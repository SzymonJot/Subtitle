import hashlib

from common.constants import BUILD_VERSION
from common.schemas import BuildDeckRequest
from domain.deck.schemas.schema import Candidate, Card, Deck, OutputFormat


def assemble_cards(
    selection_with_examples: list[Candidate], req: BuildDeckRequest
) -> list[Card]:
    """
    Assemble card data from the selection and analyzed payload.
    Map Candidate fields to Card fields
    Front: Lemma + Sentence (original)
    Back: Translated Word + Translated Sentence
    """
    cards = []
    for candidate in selection_with_examples:
        c = Card(
            lemma=candidate.lemma,
            prompt=candidate.lemma,
            answer=candidate.translated_word,
            sentence=candidate.sentence_original_lang,
            sentence_translation=candidate.translated_example,
            pos=candidate.pos,
            source_lang_tag=candidate.source_lang_tag,
            target_lang_tag=candidate.target_lang_tag,
            build_version=BUILD_VERSION,
        )

        cards.append(c)

    return cards


def build_deck(
    req: BuildDeckRequest,
    stats: dict,
    file_bytes: bytes,
    format: OutputFormat,
    result_path: str,
) -> Deck:
    """
    Build the final deck metadata object.
    """
    return Deck(
        episode_id=req.episode_id,
        analyzed_hash=req.analyzed_hash,
        idempotency_key=req.idempotency_key(),
        build_version=req.build_version or "v1",
        format=format,
        result_path=result_path,
        size_bytes=len(file_bytes),
        checksum_sha256=hashlib.sha256(file_bytes).hexdigest(),
        card_count=stats.get("card_count", 0),
        unique_lemmas=stats.get("unique_lemmas", 0),
        achieved_coverage=stats.get("achieved_coverage", 0.0),
        cached=False,
    )
