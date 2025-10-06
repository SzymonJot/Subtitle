import os
import deepl
import time
import genanki
import hashlib
import html
import regex as re
from collections import Counter, defaultdict
import unicodedata as ud
from typing import list, dict

DEEPL_AUTH_KEY  = os.getenv('DEEPL_AUTH_KEY')

translator = deepl.Translator(DEEPL_AUTH_KEY)

_CACHE = {}
AMBIG = {
    "underkänd":  {"context": "School grading; means 'failed (an exam)'.", "override": "failed"},
    "underkända": {"context": "School grading; means 'failed (an exam)'.", "override": "failed"},
    "underkänt":  {"context": "School grading; means 'failed (an exam)'.", "override": "failed"},
    # add more false friends here...
}

# 2) Tiny domain detector (optional)
DOMAINS = {
    "school": {
        "keywords": {"prov","betyg","lärare","skola","elever","kurs","tentamen"},
        "context": "School / grading context."
    },
    "medical": {
        "keywords": {"sjukhus","läkare","behandling","symptom","diagnos"},
        "context": "Medical context."
    },
    "finance": {
        "keywords": {"bolag","aktier","börsen","fakturor","intäkter","kostnader"},
        "context": "Business / finance context."
    },
}

def translate_load(study_list, final_with_picked_sentences):
    for word in study_list:
        content = final_with_picked_sentences[word]          
        tgt = content['to_study']['word']
        sv = content['to_study']['sentence']                
        en_sentence, word_eng = translate_tagged(sv, tgt, translator)
        content['to_study']['sentence_translated'] = en_sentence
        content['to_study']['word_translated'] = word_eng
        time.sleep(0.7)  
    return final_with_picked_sentences


def get_coverage_info(lemma_count):
    coverage_info = {}
    for coverage in range(5, 101, 5):
        size, _ = deck_size_for_target(lemma_count,coverage)
        coverage_info[coverage] = size
    return coverage_info


def save_deck(deck: genanki.Deck, filename: str):
    genanki.Package(deck).write_to_file(filename)


# --- DECK ---
def _note_guid(word: str, sv: str) -> str:
    h = hashlib.sha1(f"{word}||{sv}".encode('utf-8')).hexdigest()
    return h

def generate_deck(name: str, db: dict) -> genanki.Deck:
    model = genanki.Model(
        1607392319,  # keep stable once chosen
        'EN→SV Minimal',
        fields=[{'name': 'Front'}, {'name': 'Back'}],
        templates=[{
            'name': 'Card 1',
            'qfmt': '{{Front}}',
            'afmt': '{{FrontSide}}<hr id="answer">{{Back}}',
        }],
        css="""
        .card { font-family: Inter, Arial; font-size: 18px; line-height: 1.4; }
        """
    )

    deck = genanki.Deck(2059200110, name)

    for _, rec in sorted(db.items()):
        front, back = build_card(rec)
        word = (rec.get('to_study', {}) or {}).get('Word', '')
        sv   = (rec.get('to_study', {}) or {}).get('Sentence', '')
        if not front or not word:
            continue
        note = genanki.Note(
            model=model,
            fields=[front, back],
            guid=_note_guid(word, sv),
        )
        deck.add_note(note)

    return deck


# --- utils ---
def _bold_term_tags(s: str) -> str:
    # raw <term>…</term>
    s = s.replace("<term>", "<b>").replace("</term>", "</b>")
    # escaped &lt;term&gt;…&lt;/term&gt;
    s = s.replace("&lt;term&gt;", "<b>").replace("&lt;/term&gt;", "</b>")
    return s

def _highlight_once(sentence: str, target: str) -> str:
    # bold FIRST whole-word target (case-insensitive), preserving original case
    pat = re.compile(rf"\b{re.escape(target)}\b", re.IGNORECASE)
    return pat.sub(lambda m: f"<b>{m.group(0)}</b>", sentence, count=1)

# --- FRONT ---
def _front_text(rec: dict) -> str:
    """
    Front shows:
      1) English sentence (italic, with bolded term)
      2) 'gloss (pos)'
    """
    ts = rec.get('to_study', {}) or {}
    en_sent = ts.get('Sentence_translated') or ''
    gloss   = ts.get('Word_translated') or ''   # <-- fixed source
    pos     = (rec.get('POS') or '').lower()

    # clean "None"
    if gloss == 'None': gloss = ''
    if en_sent == 'None': en_sent = ''

    en_sent = _bold_term_tags(en_sent)

    gloss_line = f"{gloss}  ({pos})" if gloss and pos else (gloss or (f"({pos})" if pos else ""))

    parts = []
    if en_sent:
        parts.append(f"<div style='font-style:italic'>{en_sent}</div>")
    if gloss_line:
        parts.append(f"<div style='margin-top:6px'>{html.escape(gloss_line)}</div>")
    return "".join(parts)

# --- BACK & CARD BUILDER ---
def build_card(rec: dict) -> tuple[str, str]:
    pos   = rec.get('POS', '') or ''
    art   = rec.get('Artikel') or ''   # 'en' / 'ett' / ''
    ts    = rec.get('to_study', {}) or {}
    word  = ts.get('Word', '') or ''
    sv    = ts.get('Sentence', '') or ''
    en    = ts.get('Sentence_translated', '') or ''
    en    = _bold_term_tags(en)

    front = _front_text(rec)

    badge = (
        f"<span style='background:#eee;border-radius:6px;padding:2px 6px;margin-left:6px'>{art}</span>"
        if (pos == 'NOUN' and art) else ""
    )

    back = (
        f"<div style='font-size:1.35em;line-height:1.2'><b>{html.escape(word)}</b>{badge}</div>"
        f"<div style='margin-top:8px'>{_highlight_once(html.escape(sv), word)}</div>"
        f"<div style='margin-top:6px;font-style:italic'>{en}</div>"
        f"<div style='margin-top:6px;color:#777'>{pos.lower()}</div>"
    )
    return front, back


def select_top_quota(lemma_count, target_total=250, quotas=None):
    """
    lemma_count: dict like {'NOUN': {'barn':12, 'dag':4, ...}, 'VERB': {...}, ...}
    target_total: total number of lemmas you want
    quotas: POS -> fraction, e.g. {'VERB':0.35,'NOUN':0.40,'ADJ':0.15,'ADV':0.10}
            If None, distribute evenly across POS present.
    Returns: (study_list, picked_by_pos)
      study_list = [(lemma, POS, count)] ordered by selection stage
      picked_by_pos = {'NOUN': {'barn':12, ...}, 'VERB': {...}, ...}
    """
    # Convert inner dicts to Counters
    pos_counters = {pos: Counter(d) for pos, d in lemma_count.items()}
    all_pos = list(pos_counters.keys())

    if not quotas:
        quotas = {pos: 1/len(all_pos) for pos in all_pos}

    # translate fractions to integer quotas, then backfill any shortfall
    raw = {pos: int(target_total * quotas.get(pos, 0)) for pos in all_pos}
    short = target_total - sum(raw.values())
    # give leftover slots to the biggest buckets by available items
    fill_order = sorted(all_pos, key=lambda p: sum(pos_counters[p].values()), reverse=True)
    i = 0
    while short > 0 and fill_order:
        pos = fill_order[i % len(fill_order)]
        raw[pos] += 1
        short -= 1
        i += 1

    picked = set()
    picked_by_pos = defaultdict(dict)
    study_list = []

    # 1) take top-k per POS by its quota
    for pos, k in raw.items():
        for lemma, cnt in pos_counters[pos].most_common():
            if len(picked_by_pos[pos]) >= k:
                break
            if lemma in picked:
                continue
            picked.add(lemma)
            picked_by_pos[pos][lemma] = cnt
            study_list.append((lemma))

    # 2) backfill if some POS had too few items or overlaps reduced selection
    if len(study_list) < target_total:
        # overall ranking across all POS
        overall = Counter()
        per_pos_for_lemma = defaultdict(dict)
        for pos, C in pos_counters.items():
            for lemma, cnt in C.items():
                overall[lemma] += cnt
                per_pos_for_lemma[lemma][pos] = cnt

        for lemma, _ in overall.most_common():
            if len(study_list) >= target_total:
                break
            if lemma in picked:
                continue
            # choose the POS where this lemma is most frequent
            pos = max(per_pos_for_lemma[lemma].items(), key=lambda x: x[1])[0]
            cnt = per_pos_for_lemma[lemma][pos]
            picked.add(lemma)
            picked_by_pos[pos][lemma] = cnt
            study_list.append((lemma))

    return study_list, picked_by_pos

def _tokenize_sv(s: str) -> set[str]:
    s = ud.normalize("NFC", s.lower())
    return set(re.findall(r"[a-zåäöéüøß\-]+", s))

def guess_context_sv(sv_sentence: str) -> str | None:
    tokens = _tokenize_sv(sv_sentence)
    for dom in DOMAINS.values():  # first match wins
        if tokens & dom["keywords"]:
            return dom["context"]
    return None

def tag_first(s, target):
    # case-insensitive, whole-word; preserves original casing in the sentence
    pattern = re.compile(rf"\b{re.escape(target)}\b", flags=re.IGNORECASE)
    return pattern.sub(lambda m: "<term>"+m.group(0)+"</term>", s, count=1)

def extract_term(en_text: str) -> str:
    a, b = en_text.find("<term>"), en_text.find("</term>")
    if a != -1 and b != -1 and b > a:
        return en_text[a+6:b]
    a, b = en_text.find("&lt;term&gt;"), en_text.find("&lt;/term&gt;")
    if a != -1 and b != -1 and b > a:
        return en_text[a+12:b]
    return ""

def translate_tagged(sv_sentence: str, target: str, translator) -> tuple[str, str]:
    key = (sv_sentence, target)
    if key in _CACHE:
        return _CACHE[key]

    # 1) Build an optional context
    ctx = None
    amb = AMBIG.get(target.lower())
    if amb:
        ctx = amb["context"]
    if ctx is None:
        ctx = guess_context_sv(sv_sentence)

    # 2) Tag first occurrence and call DeepL (one quick retry on 429)
    tagged = tag_first(sv_sentence, target)
    kwargs = dict(
        source_lang="SV", target_lang="EN-GB",
        tag_handling="xml", non_splitting_tags=["term"],
        preserve_formatting=True, outline_detection=False
    )
    if ctx:  # only pass when we have one
        kwargs["context"] = ctx

    try:
        res = translator.translate_text(tagged, **kwargs)
    except deepl.TooManyRequestsException:
        time.sleep(3)
        res = translator.translate_text(tagged, **kwargs)

    en_sentence = res.text
    word_eng = extract_term(en_sentence)

    # 3) Optional last-resort override for known false friends
    if amb and amb.get("override"):
        en_sentence = re.sub(r"(<term>)(.*?)(</term>)",
                             r"\1"+amb["override"]+r"\3",
                             en_sentence, count=1, flags=re.DOTALL)
        word_eng = amb["override"]

    _CACHE[key] = (en_sentence, word_eng)
    return _CACHE[key]

def coverage(lemma_count, picked_by_pos):
    total_tokens = sum(cnt for d in lemma_count.values() for cnt in d.values())
    covered = set()
    for pos, d in picked_by_pos.items():
        covered |= {(pos, lemma) for lemma in d}
    # sum using best matching POS counts
    covered_tokens = 0
    for pos, d in picked_by_pos.items():
        for lemma, cnt in d.items():
            covered_tokens += lemma_count.get(pos, {}).get(lemma, 0)
    return covered_tokens / total_tokens if total_tokens else 0.0

def deck_size_for_target(lemma_count: dict, target_pct: float, allowed_pos: set | None = None):
    """
    Return (k, achieved_pct) where k is the smallest number of (pos, lemma) items
    needed to reach target_pct coverage. Uses your per-(pos, lemma) counts.
    target_pct can be 0–1 (e.g., 0.8) or 0–100 (e.g., 80).
    """
    # normalize target to 0..1
    tp = target_pct / 100.0 if target_pct > 1 else float(target_pct)

    # total tokens across all POS/lemmas (same definition you use in coverage())
    total_tokens = sum(cnt for d in lemma_count.values() for cnt in d.values())
    if total_tokens == 0 or tp <= 0:
        return 0, 0.0
    if tp >= 1:
        # full deck size = all unique (pos, lemma)
        full_k = sum(len(d) for pos, d in lemma_count.items() if not allowed_pos or pos in allowed_pos)
        return full_k, 1.0

    # flatten and rank by frequency desc (respect optional POS filter)
    items = [
        (pos, lemma, cnt)
        for pos, d in lemma_count.items() if (not allowed_pos or pos in allowed_pos)
        for lemma, cnt in d.items()
    ]
    items.sort(key=lambda x: x[2], reverse=True)

    covered_tokens = 0
    k = 0
    # (pos, lemma) uniqueness is inherent; no need for an extra set unless inputs repeat
    for pos, lemma, cnt in items:
        covered_tokens += cnt
        k += 1
        achieved = covered_tokens / total_tokens
        if achieved >= tp:
            return k, achieved

    # If target not met (e.g., tp > achievable due to filters), return max
    return k, covered_tokens / total_tokens

def pick_shortest_by_lemma(
    final: Dict[str, Dict[str, List[str]]],
    prefer_inflected: bool = True,      # prefer forms where word_form != lemma
    measure: str = "tokens"             # "tokens" or "chars"
    ) -> List[Tuple[str, str, str]]:
    """
    Returns a list of (lemma, chosen_word_form, shortest_example_sentence).
    Chooses per lemma the word form whose shortest example is the shortest.
    """

    def key_for(s: str):
        # primary: token count, secondary: char length
        return (len(s.split()), len(s)) if measure == "tokens" else (len(s),)

    results = {}

    for lemma, forms in final.items():
        forms['to_study'] = {}
        if not forms:
            continue

        candidates = []
        for form, sents in forms['examples'].items():
            if not sents:
                continue
            shortest_sent_for_form = min(sents, key=key_for)

            # Rank: 0 = inflected preferred, 1 = base (if prefer_inflected)
            rank = 0 if (prefer_inflected and form != lemma) else 1
            candidates.append((rank, key_for(shortest_sent_for_form), form, shortest_sent_for_form))

        if not candidates:
            continue
        
        # Choose minimal by (rank, length-key)
        _, _, best_form, best_sentence = min(candidates, key=lambda x: (x[0], x[1]))

        forms['to_study']['word'] = best_form
        forms['to_study']['sentence'] = best_sentence

    return final

if __name__ == "__main__":
    lemma_count = {
        'ADJ': {
            '140säng': 2,
            '18årsgräns': 5,
            'aggressiv': 2
            },
        'ADV': {'aggressivitet': 1
                }
        }
    
    final = {'140säng': {'Artikel': 'ett',
                        'Forms': {'140säng'},
                        'POS': 'NOUN',
                        'examples': {'140säng': ['Om man är under 25 och kollar en 140säng '
                                                 'då flyttar man hemifrån.']},
                        'to_study': {'sentence': 'Om man är under 25 och kollar en 140säng '
                                                 'då flyttar man hemifrån.',
                                     'word': '140säng'}},
    '18årsgräns': {'Artikel': 'en',
                   'Forms': {'18årsgräns'},
                   'POS': 'NOUN',
                   'examples': {'18årsgräns': ['Är det inte 18årsgräns på det '
                                               'här?']},
                   'to_study': {'sentence': 'Är det inte 18årsgräns på det här?',
                                'word': '18årsgräns'}},

    'aggressiv': {'Artikel': None,
                  'Forms': {'aggressivt', 'aggressiv'},
                  'POS': 'ADJ',
                  'examples': {'aggressiv': ['Du är jävligt aggressiv i vanliga '
                                             'fall.'],
                               'aggressivt': ['Kör lite aggressivt!']},
                  'to_study': {'sentence': 'Kör lite aggressivt!',
                               'word': 'aggressivt'}},
    'aggressivitet': {'Artikel': 'en',
                      'Forms': {'aggressivitet'},
                      'POS': 'NOUN',
                      'examples': {'aggressivitet': ['Aggressivitet?']},
                      'to_study': {'sentence': 'Aggressivitet?',
                                   'word': 'aggressivitet'}},
                                 
    }
        



    # Fetch X top study
    study_list = select_top_quota(lemma_count, 200)
    # Translate
    load = translate_load(study_list, final)
    # Generate deck based on options:
    # Only words
    # Words and sentences
    # Filter out basics
    # Language for front
    
    # Return

