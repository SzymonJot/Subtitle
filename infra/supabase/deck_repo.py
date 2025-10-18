import os
from common.supabase_client import get_client
from typing import  Any

SB = get_client(os.environ["SUPABASE_URL"], os.environ['SUPABASE_SERVICE_KEY'])


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


if __name__ == '__main__':
    pass
    