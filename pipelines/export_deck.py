from common.schemas import ExportDeckRequest
from core.ports import DeckIO
from domain.deck.deck_output.exporters import export_deck


def run_export_deck(request: ExportDeckRequest, deck_io: DeckIO) -> bytes:
    return export_deck(request, deck_io)
