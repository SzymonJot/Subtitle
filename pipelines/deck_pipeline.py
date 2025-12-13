import time
import uuid
from typing import Any

from common.schemas import BuildDeckRequest
from core.ports import DeckIO
from domain.deck.deck_generation.deck_generation import assemble_cards
from domain.deck.deck_generation.lexicon_processing import (
    pick_until_target,
    score_and_rank,
    select_candidates,
    select_example,
)
from domain.deck.schemas.schema import Deck
from domain.nlp.lexicon.schema import AnalyzedEpisode
from domain.translator.translation import translate_selection
from domain.translator.translator import Translator


def _t():
    return time.perf_counter()


def run_deck_pipeline(
    analyzed_episode: AnalyzedEpisode,
    req: BuildDeckRequest,
    translator: Translator,
    deck_io: DeckIO,
) -> dict[str, Any]:
    """
    Pure pipeline runner. Deterministic given (analyzed_payload, req).
    No network, no DB, no storage here.
    """

    # 1) Candidates
    candidates = select_candidates(
        analyzed_episode, req
    )  # filtered by POS, known words, etc.

    # 2) Score + rank (uses seed only for deterministic tie-breaking if needed)
    ranked = score_and_rank(candidates, req)  # computes score

    # 3) Pick until you hit coverage or cap
    candidate_selection, stats = pick_until_target(
        ranked,
        req.max_cards,
        req.target_coverage,
        req.max_share_per_pos,
        req.target_share_per_pos,
    )

    candidate_selection_with_examples = select_example(
        candidate_selection, req, analyzed_episode
    )

    translated_candidate_selection = translate_selection(
        candidate_selection_with_examples, translator, deck_io
    )

    cards = assemble_cards(translated_candidate_selection, req)

    deck_id = str(uuid.uuid4())

    stats["deck_id"] = deck_id

    deck = Deck(
        id=deck_id,
        episode_name=req.deck_name,
        job_id=req.job_id,
        build_version=req.build_version,
        card_count=len(cards),
        achieved_coverage=stats["achieved_coverage"],
        stopped_reason=stats["stopped_reason"],
    )

    deck_io.save_deck(deck, req.model_dump())
    deck_io.save_cards(cards, deck_id)

    return stats


def get_preview_stats(
    analyzed_episode: AnalyzedEpisode,
    req: BuildDeckRequest,
) -> dict[str, Any]:
    """
    Run pipeline up to card assembly for preview.
    """
    # 1) Candidates
    candidates = select_candidates(analyzed_episode, req)

    # 2) Score + rank
    ranked = score_and_rank(candidates, req)

    # 3) Pick until you hit coverage or cap
    _, stats = pick_until_target(
        ranked,
        req.max_cards,
        req.target_coverage,
        req.max_share_per_pos,
        req.target_share_per_pos,
    )

    return stats


if __name__ == "__main__":
    pass
