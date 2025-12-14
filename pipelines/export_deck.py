from common.schemas import ExportDeckRequest
from domain.deck.deck_output.exporters import export_deck
from infra.supabase.deck_repo import SBDeckIO


def run_export_deck(request: ExportDeckRequest) -> bytes:
    deck_io = SBDeckIO()
    return export_deck(request, deck_io)
