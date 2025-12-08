import os
from common.supabase_client import get_client
from typing import  Any
from dataclasses import dataclass, asdict
from common.schemas import CacheEntry
import logging
from datetime import datetime

class SBDeckIO:
    translation_table = 'cached_translations'

    def __init__(self, sb):
        self.sb = sb

    def get_cached(self, ids:list[str]) -> dict[str, dict[str, Any]]:
        """
        Return list of rows filtered by cache id.
        """

        res = (
            self.sb.table(self.translation_table)
            .select('*')    
            .in_("cache_id", ids)
            .execute())
        
        rows = res.data or []

        return {row['cache_id']: row for row in rows}

    def upsert_cache_translation(self, cache_entries: list[CacheEntry]) -> dict:
        """
        Upsert data. List of entries to cache.
        """
        to_upsert = []

        for entry in cache_entries:
            dc = {k: str(v) for k,v in asdict(entry).items()}
            to_upsert.append(dc)

        res = (
            self.sb.table(self.translation_table)
            .upsert(to_upsert)
            .execute()
        )

        upserted = res.data or []

        logging.info(f"Upserted {len(upserted)} entries. Time {datetime.now()}")

        return res

if __name__ == '__main__':
    pass
    