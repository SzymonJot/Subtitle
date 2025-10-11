import os
import deepl
import time
import genanki
import hashlib
import html
import regex as re
from collections import Counter, defaultdict
import unicodedata as ud

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
    """
    Select candidates from analyzed payload based on request filters.
    """
    candidates = []
    lexicon = analyzed_payload.episode_data_processed
    known_words = set(req.exclude_known_lemmas or [])
    allowed_pos = set(req.include_pos or [])
    for lemma, data in lexicon.items():
        pos = data.pos
        if allowed_pos and pos not in allowed_pos:
            continue
        if any(form in known_words for form in data.forms):
            continue
        candidates.append(Candidate(lemma=lemma, pos=pos, data=data, freq = data.forms_freq, cov_share=data.forms_cov))
    return candidates

def score_and_rank(candidates: List[Candidate], req: BuildDeckRequest, rng_seed: int) -> List[RankedCandidate]:
    """
    Score and rank candidates based on request parameters.
    """
    
    ranked_candidates = []
    candidates = sorted(candidates, key=lambda x: sum(x['cov_share'].values()), reverse=True)
 
    for candidate in candidates:
        candidate['score'] = sum(candidate['cov_share'].values())
        ranked_candidates.append(RankedCandidate(**candidate))

    return ranked_candidates
 
def apply_constraints(ranked: List[RankedCandidate], req: BuildDeckRequest) -> List[RankedCandidate]:
    """
    Apply hard constraints from request to the ranked list.
    """
    filtered = []
    pos_counts = {}
    max_per_pos = req.max_per_pos or {}
    for item in ranked:
        pos = item.candidate.pos
        if pos in max_per_pos:
            if pos_counts.get(pos, 0) >= max_per_pos[pos]:
                continue
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
        filtered.append(item)
    return filtered

def pick_until_target(filtered: List[RankedCandidate], req: BuildDeckRequest) -> List[RankedCandidate]:
    """
    
    Pick candidates until target coverage or max count is reached.
    """
    picked = []
    total_coverage = 0.0
    target_coverage = req.target_coverage or 1.0
    max_count = req.max_count or len(filtered)
    for item in filtered:
        if len(picked) >= max_count:
            break
        picked.append(item)
        total_coverage += item.candidate.cov_share
        if total_coverage >= target_coverage:
            break
    return picked

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

    request = {
    "episode_id": "bonusfamiljen-s01e01",
    "analyzed_hash": "c0ffee12-3456-789a-bcde-0123456789ab", #hash from analysis    
    "target_coverage": 0.92,
    "max_cards": 120,
    "include_pos": ["NOUN", "VERB"],
    "exclude_known_lemmas": ["vara", "ha", "och", "att"],
    "dedupe_sentences": True,
    "difficulty_scoring": "mixed",
    "output_format": "anki",
    "lang_opts": {
      "sv": {
        "prefer_modern_lemmas": True,
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
    cands = select_candidates(eps,req)
    #print(cands)
    score_and_rank(cands,req,1)
    print('a')
    assert all(x['pos'] == 'NOUN' or x['pos'] == 'VERB' for x in cands)


    
   
   
