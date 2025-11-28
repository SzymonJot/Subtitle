from typing import Protocol, List
from common.schemas import CacheEntry

class DeckIO(Protocol):
    def get_cached(self, ids: List[str]) -> dict[str, dict]: ...

    def upsert_cache_translation(self, cache_entries: list[CacheEntry]) -> dict: ...

      

