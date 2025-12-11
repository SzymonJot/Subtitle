from typing import List, Protocol

from common.schemas import CacheEntry
from domain.deck.schemas.schema import Candidate


class DeckIO(Protocol):
    def get_cached(self, ids: List[str]) -> dict[str, Candidate]: ...

    def upsert_cache_translation(self, cache_entries: list[CacheEntry]) -> dict: ...
