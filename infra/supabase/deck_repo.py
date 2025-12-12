import logging
from datetime import datetime
from typing import Any

from common.constants import CACHED_TRANSLATIONS_TABLE, CARDS_TABLE, DECKS_TABLE
from common.schemas import CacheEntry
from common.supabase_client import get_client
from domain.deck.schemas.schema import Card, Deck


class SBDeckIO:
    def __init__(self):
        self.sb = get_client()

    def get_cached(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        """
        Return list of rows filtered by cache id.
        """

        res = (
            self.sb.table(CACHED_TRANSLATIONS_TABLE)
            .select("*")
            .in_("id", ids)
            .execute()
        )

        rows = res.data or []

        return {row["id"]: row for row in rows}

    def upsert_cache_translation(self, cache_entries: list[CacheEntry]) -> dict:
        """
        Upsert data. List of entries to cache.
        """
        to_upsert = []

        for entry in cache_entries:
            dc = {k: str(v) for k, v in entry.items()}
            to_upsert.append(dc)

        res = self.sb.table(CACHED_TRANSLATIONS_TABLE).upsert(to_upsert).execute()

        upserted = res.data or []

        logging.info(f"Upserted {len(upserted)} entries. Time {datetime.now()}")

        return res

    def save_cards(self, cards: list[Card], deck_id: str):
        """
        Save cards to database.
        """
        to_upsert = []

        for card in cards:
            dc = card.model_dump()
            dc["deck_id"] = deck_id
            to_upsert.append(dc)

        res = self.sb.table(CARDS_TABLE).upsert(to_upsert).execute()

        upserted = res.data or []

        logging.info(f"Upserted {len(upserted)} cards. Time {datetime.now()}")

        return res

    def save_deck(self, deck: Deck, request_params: dict):
        """
        Save deck metadata to database.
        Request params are stored for reproducibility.
        """
        # Map Pydantic fields to DB columns
        dc = {
            "id": deck.id,
            "job_id": deck.job_id,
            "build_version": deck.build_version,
            "card_count": deck.card_count,
            "request_params": request_params,
            "achieved_coverage": deck.achieved_coverage,
            "stopped_reason": deck.stopped_reason,
            # Add other fields if/when added to SQL (e.g. achieved_coverage)
        }
        res = self.sb.table(DECKS_TABLE).upsert(dc).execute()

        upserted = res.data or []

        logging.info(f"Upserted {len(upserted)} decks. Time {datetime.now()}")

        return res


if __name__ == "__main__":
    pass
