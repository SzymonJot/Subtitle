from typing import Any, List, Protocol

from common.schemas import CacheEntry
from domain.deck.schemas.schema import Candidate, Card, Deck


class DeckIO(Protocol):
    def get_cached(self, ids: List[str]) -> dict[str, Candidate]: ...

    def upsert_cache_translation(self, cache_entries: list[CacheEntry]) -> dict: ...

    def save_deck(self, deck: Deck, request_params: dict) -> Any: ...

    def save_cards(self, cards: list[Card], deck_id: str) -> Any: ...
