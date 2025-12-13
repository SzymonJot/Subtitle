import csv
import io
import logging

from common.schemas import ExportDeckRequest
from core.ports import DeckIO
from domain.deck.schemas.schema import Card


def export_deck(request: ExportDeckRequest, deck_io: DeckIO) -> bytes:
    cards = deck_io.get_cards(request.deck_id)
    if request.output_format == "anki":
        return _export_anki(cards, request)
    elif request.output_format == "quizlet":
        return _export_quizlet(cards, request)
    elif request.output_format == "csv":
        return _export_csv(cards, request)
    else:
        raise ValueError(f"Unknown format: {request.output_format}")


def _export_anki(cards: list[Card], request: ExportDeckRequest) -> bytes:
    """Export deck to Anki format."""
    pass


def _export_quizlet(cards: list[Card], request: ExportDeckRequest) -> bytes:
    """Export deck to Quizlet format."""
    buffer = io.StringIO()
    if request.export_options.include_sentence:
        writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
        for card in cards:
            writer.writerow([card.prompt, card.answer, card.sentence])
            logging.info(f"Exported card: {card.prompt} -> {card.answer}")
    else:
        writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
        for card in cards:
            writer.writerow([card.prompt, card.answer])
            logging.info(f"Exported card: {card.prompt} -> {card.answer}")

    return buffer.getvalue().encode("utf-8")


def _export_csv(cards: list[Card], request: ExportDeckRequest) -> bytes:
    """Export deck to CSV format."""
    pass
