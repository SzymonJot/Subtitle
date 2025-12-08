from deck.schemas.schema import Deck
from common.schemas import BuildDeckRequest

def export_deck(deck: Deck, request: BuildDeckRequest) -> bytes:
    if request.format == "anki":
        return _export_anki(deck)
    elif request.format == "quizlet":
        return _export_quizlet(deck)
    elif request.format == "csv":
        return _export_csv(deck)
    else:
        raise ValueError(f"Unknown format: {format}")


def _export_anki(deck: Deck) -> bytes:
    """Export deck to Anki format."""
    pass
def _export_quizlet(deck: Deck) -> bytes:
    """Export deck to Quizlet format."""
    pass

def _export_csv(deck: Deck) -> bytes:
    """Export deck to CSV format."""
    pass