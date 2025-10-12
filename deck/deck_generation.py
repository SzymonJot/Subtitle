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

#DEEPL_AUTH_KEY  = os.getenv('DEEPL_AUTH_KEY')

#translator = deepl.Translator(DEEPL_AUTH_KEY)

class Candidate(TypedDict):
    lemma: str
    pos: str
    forms: List[str]
    freq: int
    cov_share: float        # per-lemma coverage share (0..1)

class RankedCandidate(TypedDict):
    lemma: str
    pos: str
    forms: List[str]
    freq: int
    cov_share: float
    score: float

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

def translate_selection(selection: List[RankedCandidate], translator, req: BuildDeckRequest) -> List[RankedCandidate]:
    """
    Translate the selected candidates using the provided translator.
    """
    pass

def assemble_cards(selection: List[RankedCandidate], analyzed_payload: EpisodeDataProcessed, req: BuildDeckRequest) -> List[Card]:
    """
    Assemble card data from the selection and analyzed payload.
    """
    pass

def build_deck(cards: List[Card], req: BuildDeckRequest, file_bytes: bytes, out_format: OutputFormat, result_path: str) -> Deck:
    """
    Build the final deck metadata object.
    """
    pass

def render_export(deck: Deck, req: BuildDeckRequest) -> Tuple[bytes, str]:
    """
    Render the cards into the requested format and return as bytes.
    """
    pass

def collect_stats(cards: List[Dict], analyzed_payload: EpisodeDataProcessed, req: BuildDeckRequest) -> Dict:
    """
    Collect statistics about the generated deck.
    """
    pass


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
    "target_coverage": 0.8,
    "max_cards": None,
    #"include_pos": ["NOUN", "VERB"],
    #"max_share_per_pos": None,
    #"target_share_per_cov": {"NOUN": 0.5, "VERB": 0.5},
    #"exclude_known_lemmas": ["vara", "ha", "och", "att"],
    "dedupe_sentences": True,
    "difficulty_scoring": "mixed",
    "output_format": "anki",
    "lang_opts": {
      "sv": {
        "require_article_for_nouns": True,
        "min_example_len": 15,
        "max_example_len": 140
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
    print(len(cands))

    print(sum([x['cov_share'] for x in cands]))
   
    
    print(len(cands))
    cands = score_and_rank(cands,req,1)
    contr = apply_constraints(cands,req)
    print(sum(c['cov_share'] for c in cands))
    print("Pool size:", len(contr))
    
    print("Sum cov_share:", sum(c['cov_share'] for c in contr))
    #print(cands)
    
    picked, rep = pick_until_target(
    filtered_ranked=contr,                      # List[RankedCandidate] (dicts)
    max_cards=req.max_cards,
    target_coverage=req.target_coverage,
    max_share_per_pos=req.max_share_per_pos,    # e.g., {"NOUN": 0.5, "VERB": 0.5}
    target_share_per_pos=req.target_share_per_pos,  # optional, e.g., {"NOUN": 0.5, "VERB": 0.5}
)

    print('a')
    print(rep)
    #assert all(x['pos'] == 'NOUN' or x['pos'] == 'VERB' for x in cands)


    
   
   
