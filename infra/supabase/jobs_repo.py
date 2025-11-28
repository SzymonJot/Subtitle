import os
from datetime import datetime
from typing import Any, Dict, List
from dataclasses import asdict

from common.supabase_client import get_client
from common.constants import (
    TABLE_JOBS, TABLE_CACHE, BUCKET_UPLOADS, STATUS_RUNNING, STATUS_SUCCEEDED, STATUS_FAILED
)

SB = get_client(os.environ["SUPABASE_URL"], os.environ['SUPABASE_SERVICE_KEY'])

class SBJobsIO:
    jobs_table = TABLE_JOBS

    def __init__(self, sb):
        self.sb = sb

    def get_job(self, job_id: str):
        row = self.sb.table(TABLE_JOBS).select('*').eq('id', job_id).execute().data[0]
        return row

    def insert_job(self, job_id: str, in_path: str, jobs_table: str, status: str, params: dict):
        self.sb.table(jobs_table).insert({
            'id': job_id,
            'input_path': in_path,
            'status': status,
            'params': params,
            'created_at': datetime.now().isoformat()
        }).execute()    

    def update_status(self, job_id: str, status: str, progress: int, error: str = None):
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat(),
            'progress': progress,
        }
        if status == STATUS_SUCCEEDED:
            update_data['finished_at'] = datetime.now().isoformat()
        elif status == STATUS_RUNNING:
            update_data['started_at'] = datetime.now().isoformat()
        elif status == STATUS_FAILED:
            update_data['error'] = error
            
        self.sb.table(TABLE_JOBS).update(update_data).eq('id', job_id).execute()

    def update_value(self, table:str, to_update: dict):
        # This seems generic, but used for output_path
        # Ideally we should have update_job(job_id, **kwargs)
        self.sb.table(table).update(to_update).execute()

    def upload_file(self, bucket_name: str, file: Any, name: str):
        self.sb.storage.from_(bucket_name).upload(name, file)

    def download_analysis(self, job_id: str):
        # This logic seems specific to how output_path is stored "bucket/path"
        output_path = self.sb.table(TABLE_JOBS).select('output_path').eq('id', job_id).execute().data[0]
        path_str = output_path['output_path']
        bucket_name = path_str.split('/')[0]
        file_path = "/".join(path_str.split('/')[1:]) # Handle paths with multiple slashes if any
        return self.sb.storage.from_(bucket_name).download(file_path)

    def get_storage_file(self, path: str):
        # Assumes path is "bucket/file"
        bucket_name = path.split('/')[0]
        file_path = "/".join(path.split('/')[1:])
        return self.sb.storage.from_(bucket_name).download(file_path)

    def get_cached(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Return list of rows filtered by cache id.
        """
        if not ids:
            return {}
        res = (
            self.sb.table(TABLE_CACHE)
            .select('*')    
            .in_("id", ids)
            .execute())
        
        rows = res.data or []
        return {row['id']: row for row in rows}

    def upsert_cache_translation(self, entries: List[Dict]) -> Any:
        """
        Upsert data. List of entries to cache.
        """
        if not entries:
            return {}
        res = (
            self.sb.table(TABLE_CACHE)
            .upsert(entries)
            .execute()
        )
        return res

if __name__ == '__main__':
    pass