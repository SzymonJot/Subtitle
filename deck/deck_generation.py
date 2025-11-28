import os
import deepl
import time
import genanki
import hashlib
import html
import regex as re
from collections import Counter, defaultdict
import unicodedata as ud
from math import floor
from typing import Dict, List, TypedDict, Optional, Tuple
from nlp.lexicon.schema import EpisodeDataProcessed
from deck.schema import Deck, Card, OutputFormat, ExportOptions, BuiltDeck,BuildDeckRequest
import langcodes
import unicodedata
from core.ports import DeckIO

TRANS_VERSION = 'DEEPL:2025-09'
#DEEPL_AUTH_KEY  = os.getenv('DEEPL_AUTH_KEY')

#translator = deepl.Translator(DEEPL_AUTH_KEY)

class Candidate(TypedDict):
    lemma: str
    pos: str
    forms: List[str]
    freq: int
    cov_share: float        # per-lemma coverage share (0..1)
    example: dict

class RankedCandidate(TypedDict):
    lemma: str
    pos: str
    forms: List[str]
    freq: int
    cov_share: float
    score: float
    example: dict
    form_original_lang: str
    sentence_original_lang: str
    translated_word: str
    translated_example: str

def select_candidates(analyzed_payload: EpisodeDataProcessed, req: BuildDeckRequest) -> List[Candidate]:
    lexicon = analyzed_payload.episode_data_processed
    known_lemmas = set(req.exclude_known_lemmas or [])
    allowed_pos = set(req.include_pos or [])

    out: List[Candidate] = []
    for lemma, data in lexicon.items():
        pos = data.pos
        if allowed_pos and pos not in allowed_pos:
            continue
        if lemma in known_lemmas:        # <-- key change
            continue

        # pick a single frequency and coverage scalar for ranking
        freq_total = sum(data.forms_freq.values())
        cov_total = sum(data.forms_cov.values())

        out.append(Candidate(
            lemma=lemma,
            pos=pos,
            forms=list(set(data.forms)),
            freq=freq_total,
            cov_share=cov_total,         # make sure Candidate.cov_share is float in your TypedDict
        ))
    return out

def score_and_rank(candidates: List[Candidate], req: BuildDeckRequest, rng_seed: int) -> List[RankedCandidate]:
    """
    Score and rank candidates based on request parameters.
    """
    
    ranked_candidates = []
    candidates = sorted(candidates, key=lambda x: x['cov_share'], reverse=True)
 
    for candidate in candidates:
        candidate['score'] = candidate['cov_share']
        ranked_candidates.append(RankedCandidate(**candidate))

    return ranked_candidates
 
def apply_constraints(ranked: List[RankedCandidate], req: BuildDeckRequest) -> List[RankedCandidate]:
    """
    Apply hard constraints from request to the ranked list.
    """
    """
    dedupe by lemma

    exclude known/blacklist

    remove cov_share ≤ 0 or malformed
    
    """

    # to_implement

    return ranked

def validate_caps(max_share_per_pos: Optional[Dict[str, float]]) -> None:
    """
    Hard caps semantics: sum may be <= 1.0 (leftover means other POS can fill it).
    We reject sums > 1.0 to avoid ambiguous intent.
    """
    if not max_share_per_pos:
        return
    total = sum(max(0.0, v) for v in max_share_per_pos.values())
    if total > 1.0 + 1e-9:
        raise ValueError(
            f"max_share_per_pos sums to {total:.3f} (> 1). "
            "Lower the shares or spread across more POS."
        )

def caps_to_counts(deck_limit: int, max_share_per_pos: Optional[Dict[str, float]]) -> Dict[str, int]:
    """
    Convert cap shares to integer limits against the deck budget.
    We do NOT normalize if sum < 1.0 (leftover is allowed).
    """
    if not max_share_per_pos:
        return {}
    return {pos: max(0, floor(max(0.0, share) * deck_limit))
            for pos, share in max_share_per_pos.items()}

def normalize_targets(target_share_per_pos: Optional[Dict[str, float]]) -> Dict[str, float]:
    """
    Soft targets semantics: proportions to *aim for*.
    Normalize to sum = 1 so the 'need' math is stable even if sliders sum to ~0.98/1.02.
    """
    if not target_share_per_pos:
        return {}
    total = sum(max(0.0, v) for v in target_share_per_pos.values())
    if total <= 0:
        return {k: 0.0 for k in target_share_per_pos}
    return {k: max(0.0, v) / total for k, v in target_share_per_pos.items()}

def bucketize_by_pos(candidates: List[RankedCandidate]) -> Dict[str, List[RankedCandidate]]:
    """Group candidates by POS. Each bucket sorted by score descending; drop zero coverage."""
    buckets: Dict[str, List[RankedCandidate]] = defaultdict(list)
    for rc in candidates:
        if rc.get("cov_share", 0.0) > 0.0:
            buckets[rc["pos"]].append(rc)
    for pos, bucket in buckets.items():
        bucket.sort(key=lambda x: x["score"], reverse=True)
    return dict(buckets)

def is_eligible(pos: str,
                buckets: Dict[str, List[RankedCandidate]],
                pos_counts: Counter,
                caps: Dict[str, int]) -> bool:
    """Eligible = bucket non-empty AND under its hard cap (if any)."""
    if not buckets.get(pos):
        return False
    cap = caps.get(pos)
    return (cap is None) or (pos_counts.get(pos, 0) < cap)

def global_best_head(buckets: Dict[str, List[RankedCandidate]],
                     pos_counts: Counter,
                     caps: Dict[str, int]) -> Tuple[Optional[str], Optional[RankedCandidate]]:
    """Return (pos, item) for the best available head across eligible buckets."""
    best_pos: Optional[str] = None
    best_item: Optional[RankedCandidate] = None
    for p, bucket in buckets.items():
        if not is_eligible(p, buckets, pos_counts, caps):
            continue
        head = bucket[0]
        if best_item is None or head["score"] > best_item["score"]:
            best_item, best_pos = head, p
    return best_pos, best_item

def compute_needs(pos_counts: Counter,
                  targets: Dict[str, float],
                  buckets: Dict[str, List[RankedCandidate]],
                  caps: Dict[str, int],
                  alpha: float = 1.0) -> Dict[str, float]:
    """
    Smoothed need per POS: need = target_share - current_share,
    where current_share ≈ (count + α) / (N + α * P). Ineligible POS -> -inf.
    """
    needs: Dict[str, float] = {}
    if not targets:
        return needs

    P = len(targets)
    N = sum(pos_counts.values())
    denom = N + alpha * P

    for pos, t in targets.items():
        if not is_eligible(pos, buckets, pos_counts, caps):
            needs[pos] = float("-inf")
            continue
        s_hat = (pos_counts.get(pos, 0) + alpha) / denom if denom > 0 else (1.0 / P)
        needs[pos] = t - s_hat
    return needs


# ----------------- Main picker -----------------

def pick_until_target(
    filtered_ranked: List[RankedCandidate],
    max_cards: Optional[int],
    target_coverage: Optional[float],
    max_share_per_pos: Optional[Dict[str, float]] = None,     # hard caps (sum ≤ 1)
    target_share_per_pos: Optional[Dict[str, float]] = None,  # soft targets (normalized)
    hysteresis_eps: float = 0.02,    # ignore tiny needs near boundary
    score_gap_delta: float = 0.15,   # allow global best if it's ≥15% higher than the needed head
) -> Tuple[List[RankedCandidate], Dict]:
    """
    POS-aware greedy picker that respects hard caps and optionally steers toward a target mix.
    Stops at target_coverage or max_cards, or when candidates are exhausted.
    Returns (picked, report).
    """
    if target_coverage is not None and not (0.0 <= target_coverage <= 1.0):
        raise ValueError("target_coverage must be within [0, 1].")

    limit = max_cards if (max_cards is not None and max_cards > 0) else len(filtered_ranked)
    validate_caps(max_share_per_pos)
    caps = caps_to_counts(limit, max_share_per_pos)
    targets = normalize_targets(target_share_per_pos)

    buckets = bucketize_by_pos(filtered_ranked)
    picked: List[RankedCandidate] = []
    pos_counts: Counter = Counter()
    coverage = 0.0
    reason = "exhausted"

    while True:
        # --- Stop checks (top-of-loop prevents “one extra pick”) ---
        if target_coverage is not None and coverage >= target_coverage - 1e-12:
            reason = "target_coverage"; break
        if len(picked) >= limit:
            reason = "max_cards"; break
        if all(len(b) == 0 for b in buckets.values()):
            reason = "exhausted"; break
        if not any(is_eligible(p, buckets, pos_counts, caps) for p in buckets):
            reason = "exhausted"; break

        # --- Seed with global best on the first iteration ---
        if not picked:
            g_pos, g_item = global_best_head(buckets, pos_counts, caps)
            if g_item is None:
                reason = "exhausted"; break
            buckets[g_pos].pop(0)
            picked.append(g_item)
            pos_counts[g_pos] += 1
            coverage = min(1.0, coverage + float(g_item["cov_share"]))
            continue

        # --- Choose POS: soft need if provided; otherwise global best ---
        needs = compute_needs(pos_counts, targets, buckets, caps) if targets else {}
        chosen_pos: Optional[str] = None

        if needs:
            pos_star = max(needs, key=needs.get)
            need_star = needs[pos_star]
            if need_star > hysteresis_eps and is_eligible(pos_star, buckets, pos_counts, caps):
                # Global-utility override: if global best is much stronger than the needed head, take it.
                g_pos, g_item = global_best_head(buckets, pos_counts, caps)
                needed_head = buckets[pos_star][0] if buckets[pos_star] else None
                if g_item and needed_head and g_item["score"] >= (1.0 + score_gap_delta) * needed_head["score"]:
                    chosen_pos = g_pos
                else:
                    chosen_pos = pos_star

        if chosen_pos is None:
            chosen_pos, _ = global_best_head(buckets, pos_counts, caps)
        if chosen_pos is None:
            reason = "exhausted"; break

        # --- Commit pick ---
        item = buckets[chosen_pos].pop(0)
        picked.append(item)
        pos_counts[chosen_pos] += 1
        coverage = min(1.0, coverage + float(item["cov_share"]))

    report = {
        "picked_count": len(picked),
        "achieved_coverage": coverage,
        "pos_counts": dict(pos_counts),
        "stopped_reason": reason,
    }
    if target_coverage is not None and coverage < target_coverage - 1e-12:
        report["note"] = "Target not reached with current caps/availability."
    return picked, report

def build_preview(selection: List[RankedCandidate], req: BuildDeckRequest) -> Tuple[bytes, str]:
    """
    Build a preview of the selected candidates in a simple text format.
    """
    max_card = [range(1,len(selection),50)]
    target = [range(0,100,5)]
    lines = []
    for cov_tgt in target:
        for tgt in max_card:
            data = pick_until_target(selection, tgt, req.target_coverage, req.max_share_per_pos)
        
    preview_text = "\n".join(lines)
    return preview_text.encode("utf-8"), "text/plain"

from typing import List, Dict, Optional
from collections import defaultdict

def choose_example(
    selection: List[RankedCandidate],
    analyzed_payload: EpisodeDataProcessed,
    req: BuildDeckRequest
) -> List[RankedCandidate]:
    """
    For each candidate and for each of its forms found in analyzed examples,
    choose exactly one example sentence and store under candidate['example'][form].
    """
    # Read constraints (adapt lang key if needed)
    lang_opts = req.lang_opts.get("sv", {})
    min_len = int(lang_opts.get("min_example_len", 1))
    max_len = int(lang_opts.get("max_example_len", 10**9))
    dedupe = bool(getattr(req, "dedupe_sentences", False))

    seen_sentences = set()

    def wc(s: str) -> int:
        return len(s.split())

    def pick_best(examples: List[str]) -> Optional[str]:
        if not examples:
            return None
        # Apply length bounds
        pool = [e for e in examples if min_len <= wc(e) <= max_len] or examples
        # Prefer multi-word
        multi = [e for e in pool if wc(e) > 1] or pool
        # Respect dedupe if requested
        if dedupe:
            for e in multi:
                if e not in seen_sentences:
                    seen_sentences.add(e)
                    return e
            # all were seen: still return something deterministic
            return multi[0]
        else:
            return multi[0]

    for cand in selection:
        lemma = cand["lemma"]
        data = analyzed_payload.episode_data_processed.get(lemma)
        cand["example"] = {}  # prepare output container

        if not data or not getattr(data, "examples", None):
            continue

        # data.examples is expected to be: Dict[str form, List[str sentences]]
        for form, example in data.examples.items():
            chosen = pick_best(example)
            if chosen:
                cand["form_original_lang"] = [form]
                cand["sentence_original_lang"] = example

    return selection

SEP_FIND = re.compile(r'[\r\n\x85\u2028\u2029]')

def create_id_translation_cache(word: str, sentence: str, source_lang:str, target_lang: str, translation_ver:str = TRANS_VERSION) -> str:
    """
    Creates ID for translation cache table based on passed parameters.
    Key are case sensitive.
    All white spaces are collapsed as it won't change learning experience.
    """

    if SEP_FIND.search(sentence):
        raise ValueError("CR/LF characters/lines break found in sentence!")
    
    if SEP_FIND.search(word):
        raise ValueError("CR/LF characters/lines break found in word!")
    
    source_tag = langcodes.Language.get(source_lang).to_tag()
    target_tag = langcodes.Language.get(target_lang).to_tag()

    
    word_cleaned = unicodedata.normalize("NFKC",word.strip())
    sentence = " ".join(sentence.split())
    sentence_cleaned =  unicodedata.normalize("NFKC", sentence )

    if not word_cleaned:
        raise ValueError("Incorrect word")
    if not sentence_cleaned:
        raise ValueError("Incorrect sentence")
    if not translation_ver:
        raise ValueError("Incorrect version")
    
    image = {}
    image['word'] = word_cleaned
    image['sentence'] = sentence_cleaned
    image['target_lang'] = target_tag
    image['source_lang'] = source_tag
    image['translation_ver'] = translation_ver

    return hashlib.sha256(json.dumps(image, sort_keys=True, ensure_ascii=False, separators=(',',':')).encode(encoding='utf-8')).hexdigest()


def look_up_cache(candidates_to_check:List, source_lang, target_lang, deck_io: DeckIO) -> Tuple[List[RankedCandidate], List[RankedCandidate]]:
    """
    Function mutates the candidates that matched cache
    """
    ids = []
    found = []
    not_found = []
    for candidate in candidates_to_check:
        cache_id = create_id_translation_cache(candidate['form_original_lang'], candidate['sentence_original_lang'], source_lang, target_lang)
        ids.append(cache_id)

    res = deck_io.get_cached(ids)

    if len(ids) != len(candidates_to_check):
        raise ValueError("Different len between cache ids and candidates to check")
        
    for candidate, cache_id in zip(candidates_to_check, ids):
        res_content = res.get(cache_id, None)
        if res_content:
            candidate['translated_word'] = res_content['target_lang_word']
            candidate['translated_example'] = res_content['target_lang_sentence']
            found.append(candidate)
        else:
            not_found.append(candidate)

    return found, not_found

def translate_selection(selection: List[RankedCandidate], translator, source_lang:str, target_lang:str, deck_io: DeckIO) -> List[RankedCandidate]:
    """
    Translate the selected candidates using the provided translator.
    Cache key: word: str, sentence: str, source_lang:str, target_lang:str
    """

    def tag_first(s, target):
    # case-insensitive, whole-word; preserves original casing in the sentence
        pattern = re.compile(rf"\b{re.escape(target)}\b", flags=re.IGNORECASE)
        return pattern.sub(lambda m: "<term>"+m.group(0)+"</term>", s, count=1)
    
    source_lang_tag = langcodes.Language.get(source_lang).to_tag()
    target_lang_tag = langcodes.Language.get(target_lang).to_tag()

    def extract_term(target_text: str) -> str:
        a, b = target_text.find("<term>"), target_text.find("</term>")
        if a != -1 and b != -1 and b > a:
            return target_text[a+6:b]
        a, b = target_text.find("&lt;term&gt;"), target_text.find("&lt;/term&gt;")
        if a != -1 and b != -1 and b > a:
            return target_text[a+12:b]
        return ""
    
    to_translate = []
    cached_translation = []
 
    n = len(selection)
    batch = 100

    for start in range(0, n, batch):
        end = min(start + batch, n )
        candidates_to_check = selection[start:end]
        
        cand_found, cand_not_found = look_up_cache(candidates_to_check, source_lang, target_lang, deck_io)

        to_translate += cand_not_found 
        cached_translation += cand_found
        
    
    for candidate in to_translate:
        form = candidate["form_original_lang"]
        sentence = candidate["sentence_original_lang"]
        
        sentence_tagged = tag_first(sentence, form)
    
        kwargs = dict(
            source_lang=source_lang_tag, target_lang=target_lang_tag,
            tag_handling="xml", non_splitting_tags=["term"],
            preserve_formatting=True, outline_detection=False
        )

        try:
            res = translator.translate_text(sentence_tagged, **kwargs)
        except deepl.TooManyRequestsException:
            time.sleep(3)
            res = translator.translate_text(sentence_tagged, **kwargs)
        
        target_lang_sentence = res.text
        target_lang_word = extract_term(target_lang_sentence)

        candidate["translated_example"] = target_lang_sentence
        candidate["translated_word"] = target_lang_word

        if not target_lang_word == "":
            # Create CacheEntry
            # We need to construct CacheEntry object or dict
            # CacheEntry(id, form_org_lang, sentence_org_lang, word_target_lang, sentence_target_lang, org_lang, target_lang)
            
            # Calculate ID
            cache_id = create_id_translation_cache(form, sentence, source_lang, target_lang)
            
            entry = {
                "id": cache_id,
                "form_org_lang": form,
                "sentence_org_lang": sentence,
                "word_target_lang": target_lang_word,
                "sentence_target_lang": target_lang_sentence,
                "org_lang": source_lang,
                "target_lang": target_lang
            }
            
            # Upsert immediately (or batch?)
            # For now immediately
            try:
                deck_io.upsert_cache_translation([entry])
            except Exception as e:
                print(f"Failed to cache translation: {e}")

    
    return cached_translation + to_translate
    

    #tag_first()
    #kwargs = {}
    #translator.translate_text(tagged, **kwargs)
    # Context translation, cache has to have word+sentence id and langauge
    # it should process in batches

def assemble_cards(selection: List[RankedCandidate], analyzed_payload: EpisodeDataProcessed, req: BuildDeckRequest) -> List[Card]:
    """
    Assemble card data from the selection and analyzed payload.
    """
    # 1. Choose examples
    selection_with_examples = choose_example(selection, analyzed_payload, req)
    
    cards = []
    for item in selection_with_examples:
        # Create Card object
        # We need to map RankedCandidate fields to Card fields
        # Card(id, lemma, prompt, answer, sentence, pos, tags)
        
        # For now, simple mapping:
        # prompt = lemma (or form?)
        # answer = translated_word
        # sentence = sentence_original_lang (with hole?) -> translated_example
        
        # Let's assume:
        # Front: Lemma + Sentence (original)
        # Back: Translated Word + Translated Sentence
        
        # Or based on Card schema:
        # lemma: str
        # prompt: str
        # answer: str
        # sentence: Optional[str]
        
        c = Card.from_minimal(
            lemma=item['lemma'],
            sentence=item.get('sentence_original_lang'),
            pos=item['pos'],
            tags=[item['pos']],
            build_version=req.build_version or "v1"
        )
        # Override prompt/answer if needed based on template
        # For now, let's keep defaults from from_minimal or set them explicitly
        c.prompt = item['lemma']
        c.answer = item.get('translated_word', '')
        # If we have translation, maybe we want to store it?
        # Card schema is simple. Let's stick to basic.
        
        cards.append(c)
        
    return cards

def build_deck(req: BuildDeckRequest, stats: Dict, file_bytes: bytes, format_: OutputFormat, result_path: str) -> BuiltDeck:
    """
    Build the final deck metadata object.
    """
    return BuiltDeck(
        episode_id=req.episode_id,
        analyzed_hash=req.analyzed_hash,
        idempotency_key=req.idempotency_key(),
        build_version=req.build_version or "v1",
        format=format_,
        result_path=result_path,
        size_bytes=len(file_bytes),
        checksum_sha256=hashlib.sha256(file_bytes).hexdigest(),
        card_count=stats.get('card_count', 0),
        unique_lemmas=stats.get('unique_lemmas', 0),
        achieved_coverage=stats.get('achieved_coverage', 0.0),
        cached=False
    )

def render_export(cards: List[Card], req: BuildDeckRequest) -> Tuple[bytes, str]:
    """
    Render the cards into the requested format and return as bytes.
    """
    # Placeholder for actual rendering (Anki/CSV)
    # For now, return JSON as bytes
    import json
    data = [c.dict() for c in cards]
    return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'), "json"

def collect_stats(cards: List[Card], analyzed_payload: EpisodeDataProcessed, req: BuildDeckRequest) -> Dict:
    """
    Collect statistics about the generated deck.
    """
    return {
        "card_count": len(cards),
        "unique_lemmas": len({c.lemma for c in cards}),
        "achieved_coverage": 0.0 # TODO: Calculate real coverage
    }


if __name__ == "__main__":
    import json,ast
    srt_path = "data_preview.txt"

    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    raw_json_str = ast.literal_eval(srt_content)   

    loaded = json.loads(raw_json_str)
    #adjust the request load
    request = {
    "episode_id": "bonusfamiljen-s01e01",
    "analyzed_hash": "c0ffee12-3456-789a-bcde-0123456789ab", #hash from analysis    
    "target_coverage": None,
    "max_cards": 100,
    "include_pos": None,
    "max_share_per_pos": {"NOUN": 0.6, "VERB": 0.2, 'ADJ':0.1},
    "target_share_per_pos": {"NOUN": 0.5, "VERB": 0.5},
    "exclude_known_lemmas": ["vara", "ha", "och", "att"],
    "dedupe_sentences": True,
    "difficulty_scoring": "mixed",
    "output_format": "anki",
    "example_settings":{
        "example_len":{
            "min_example_len": 15,
            "max_example_len": 140
        }
    },
    "lang_opts": {
      "sv": {
      
      }
    },
    "build_version": "2025-10-09.b3",
    "params_schema_version": "v1",
    "requested_by": "szymon@example.com",
    "requested_at_iso": "2025-10-09T21:12:00+02:00",
    "notes": "Smoke test of BuildDeckRequest end-to-end"
    }   
    eps = EpisodeDataProcessed(**loaded)
    req = BuildDeckRequest(**request)

    print(len(set(eps.episode_data_processed)))

    cands = select_candidates(eps,req)
    s = choose_example(cands, eps, req)
    print(s)
    translate_selection(s,'t','t')
    #print(len(cands))
#
    #print(sum([x['cov_share'] for x in cands]))
   #
    #
    #print(len(cands))
    #cands = score_and_rank(cands,req,1)
    #contr = apply_constraints(cands,req)
    #print(sum(c['cov_share'] for c in cands))
    #print("Pool size:", len(contr))
    #
    #print("Sum cov_share:", sum(c['cov_share'] for c in contr))
    ##print(cands)
    #
    #picked, rep = pick_until_target(
    #filtered_ranked=contr,                      # List[RankedCandidate] (dicts)
    #max_cards=req.max_cards,
    #target_coverage=req.target_coverage,
    #max_share_per_pos=req.max_share_per_pos,    # e.g., {"NOUN": 0.5, "VERB": 0.5}
    #target_share_per_pos=req.target_share_per_pos,  # optional, e.g., {"NOUN": 0.5, "VERB": 0.5}
    #)


    #assert all(x['pos'] == 'NOUN' or x['pos'] == 'VERB' for x in cands)


    
   
   
