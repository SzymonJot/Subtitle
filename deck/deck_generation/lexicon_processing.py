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
from nlp.lexicon.schema import AnalyzedEpisode
from common.schemas import Deck, Card, OutputFormat, ExportOptions, BuiltDeck,BuildDeckRequest
import langcodes
import unicodedata
from core.ports import DeckIO
from typing import List, Dict, Optional
from collections import defaultdict
from deck.deck_generation.candidates_picker import pick_until_target

###########################################################
# Aim of this module is to generate a deck of cards
# from a given analyzed lexicon. 
# 
# The module is split into several functions:
# 1. select_candidates: Select candidates from the lexicon based on the request parameters.
# 2. score_and_rank: Score and rank candidates based on request parameters.
# 3. build_preview: Build a preview of the selected candidates in a simple text format.
# 4. _select_example: For each candidate and for each of its forms found in analyzed examples,
# choose exactly one example sentence and store under candidate['example'][form].
# 5. assemble_cards: Assemble card data from the selection and analyzed payload.
###########################################################

class Candidate(TypedDict):
    lemma: str
    pos: str
    forms: List[str]
    freq: int
    cov_share: float        
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

def select_candidates(analyzed_episode: AnalyzedEpisode, req: BuildDeckRequest) -> List[Candidate]:
    """
    Select candidates from the lexicon based on the request parameters.
    """
    lexicon = analyzed_episode.episode_data_processed
    known_lemmas = set(req.exclude_known_lemmas or [])
    allowed_pos = set(req.target_pos.keys() or [])

    out: List[Candidate] = []
    for lemma, data in lexicon.items():
        pos = data.pos
        if allowed_pos and pos not in allowed_pos:
            continue
        if lemma in known_lemmas:     
            continue

        freq_total = sum(data.forms_freq.values())
        cov_total = sum(data.forms_cov.values())

        out.append(Candidate(
            lemma=lemma,
            pos=pos,
            forms=list(set(data.forms)),
            freq=freq_total,
            cov_share=cov_total,      
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


def _select_example(
    selection: List[RankedCandidate],
    analyzed_payload: AnalyzedEpisode,
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

def assemble_cards(selection_with_examples: List[RankedCandidate], req: BuildDeckRequest) -> List[Card]:
    """
    Assemble card data from the selection and analyzed payload.
    Map RankedCandidate fields to Card fields
    Front: Lemma + Sentence (original)
    Back: Translated Word + Translated Sentence
    """
    cards = []
    for item in selection_with_examples:
     
        c = Card.from_minimal(
            lemma=item['lemma'],
            sentence=item.get('sentence_original_lang'),
            pos=item['pos'],
            tags=[item['pos']],
            build_version=req.build_version or "v1"
        )

        c.prompt = item['lemma']
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

if __name__ == "__main__":
    pass
    
   
   
