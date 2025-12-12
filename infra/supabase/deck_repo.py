import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any

from common.schemas import CacheEntry
from domain.deck.schemas.schema import Card, Deck


class SBDeckIO:
    translation_table = "cached_translations"
    cards_table = "cards"
    decks_table = "decks"

    def __init__(self, sb):
        self.sb = sb

    def get_cached(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        """
        Return list of rows filtered by cache id.
        """

        res = (
            self.sb.table(self.translation_table)
            .select("*")
            .in_("cache_id", ids)
            .execute()
        )

        rows = res.data or []

        return {row["cache_id"]: row for row in rows}

    def upsert_cache_translation(self, cache_entries: list[CacheEntry]) -> dict:
        """
        Upsert data. List of entries to cache.
        """
        to_upsert = []

        for entry in cache_entries:
            dc = {k: str(v) for k, v in asdict(entry).items()}
            to_upsert.append(dc)

        res = self.sb.table(self.translation_table).upsert(to_upsert).execute()

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

        res = self.sb.table(self.cards_table).upsert(to_upsert).execute()

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
            "analyzed_hash": deck.analyzed_hash,
            "build_version": deck.build_version,
            "card_count": deck.card_count,
            "request_params": request_params,
            "achieved_coverage": deck.achieved_coverage,
            "stopped_reason": deck.stopped_reason,
            # Add other fields if/when added to SQL (e.g. achieved_coverage)
        }
        res = self.sb.table(self.decks_table).upsert(dc).execute()

        upserted = res.data or []

        logging.info(f"Upserted {len(upserted)} decks. Time {datetime.now()}")

        return res


if __name__ == "__main__":
    pass
