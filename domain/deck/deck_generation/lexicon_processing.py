from typing import Dict, List, Optional

from common.schemas import BuildDeckRequest, PreviewBuildDeckRequest
from domain.deck.deck_generation.candidates_picker import pick_until_target
from domain.deck.schemas.schema import Candidate
from domain.nlp.lexicon.schema import AnalyzedEpisode

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


def select_candidates(
    analyzed_episode: AnalyzedEpisode, req: BuildDeckRequest | PreviewBuildDeckRequest
) -> List[Candidate]:
    """
    Select candidates from the lexicon based on the request parameters.
    Build candidates list from the lexicon. Filters out known lemmas and pos not in request.
    """
    lexicon = analyzed_episode.episode_data_processed
    known_lemmas = set(req.exclude_known_lemmas or [])
    allowed_pos = set(req.target_share_per_pos.keys() or [])
    target_lang_tag = req.target_lang_tag

    out: List[Candidate] = []
    for lemma, data in lexicon.items():
        pos = data.pos
        source_lang_tag = data.lang
        if allowed_pos and pos not in allowed_pos:
            continue
        if lemma in known_lemmas:
            continue

        freq_total = sum(data.forms_freq.values())
        cov_total = sum(data.forms_cov.values())

        out.append(
            Candidate(
                lemma=lemma,
                pos=pos,
                forms=list(set(data.forms)),
                freq=freq_total,
                cov_share=cov_total,
                source_lang_tag=source_lang_tag,
                target_lang_tag=target_lang_tag,
            )
        )
    return out


def score_and_rank(
    candidates: List[Candidate], req: BuildDeckRequest | PreviewBuildDeckRequest
) -> List[Candidate]:
    """
    Score and rank candidates based on request parameters.
    Populates score field in candidates.
    """
    ### In the future - multiple ranking types based on req.difficulty_scoring
    ranked_candidates = []
    candidates = sorted(candidates, key=lambda cand: cand.cov_share, reverse=True)

    for candidate in candidates:
        candidate.score = candidate.cov_share
        ranked_candidates.append(candidate)

    return ranked_candidates


def select_example(
    selection: List[Candidate],
    req: BuildDeckRequest,
    analyzed_payload: AnalyzedEpisode,
) -> List[Candidate]:
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
        """Sentence word count"""
        return len(s.split())

    def pick_best(examples: List[str]) -> Optional[str]:
        """Pick the best example sentence"""
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
        lemma = cand.lemma
        data = analyzed_payload.episode_data_processed.get(lemma)

        if not data or not getattr(data, "examples", None):
            raise ValueError(f"No examples found for lemma: {lemma}")

        # data.examples is expected to be: Dict[str form, List[str sentences]]
        for form, example in data.examples.items():
            chosen = pick_best(example)
            if chosen:
                cand.form_original_lang = form
                cand.sentence_original_lang = chosen
            else:
                raise ValueError(f"No valid example found for form: {form}")
    return selection


def deck_report(selection: List[Candidate], req: BuildDeckRequest) -> Dict:
    """
    Return deck report based on selection and request parameters.
    """
    _, repr = pick_until_target(
        selection,
        req.max_cards,
        req.target_coverage,
        req.target_share_per_pos,
        req.max_share_per_pos,
        req.max_share_per_pos,
    )

    return repr


if __name__ == "__main__":
    pass
