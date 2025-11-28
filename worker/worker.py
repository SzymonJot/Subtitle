import os
from common.supabase_client import get_client
import traceback
import datetime as dt
import logging
from pipeline.analysis_pipeline import process_episode
from infra.supabase.jobs_repo import SBJobsIO
from common.constants import (
    TABLE_JOBS, BUCKET_UPLOADS, QUEUE_MVP, STATUS_QUEUED, EXT_SRT, STATUS_FAILED, STATUS_RUNNING, STATUS_SUCCEEDED
)

SB = get_client(os.environ["SUPABASE_URL"], os.environ['SUPABASE_SERVICE_KEY'])
sb_jobs_io = SBJobsIO(SB)

def run_job(job_id: str):
    try:
        # Get row from supabase for this job id
        row = sb_jobs_io.get_job(job_id)
        in_path = row['input_path']
        # Fetch file
        file_to_process = sb_jobs_io.get_storage_file(in_path)
        # Get params
        params = row['params']
        # Pass file to data pipeline
        logging.info(f"Processing job: {job_id}")
        sb_jobs_io.update_status(job_id, STATUS_RUNNING, 0)
        
        if params['file_type'] == 'srt':
            from nlp.content.srt_adapter import SRTAdapter
            adapter = SRTAdapter()
        
        if params['language'] == 'sv':
            from nlp.lang.sv.lang_adapter import sv_lang_adapter
            lang_adapter = sv_lang_adapter()
        
        json_str = process_episode(
            file_to_process,
            adapter,
            lang_adapter
        )
      
        # Put it to bucket results
        results_encoded = json_str.encode("utf-8")
        logging.info(f"Encoded results to {len(results_encoded)} bytes.")
        sb_jobs_io.upload_file(BUCKET_RESULTS, results_encoded, job_id)
        logging.info(f"Uploaded results to bucket {BUCKET_RESULTS}/{job_id}")
        # Put result path to jobs table
        output_path = f'{BUCKET_RESULTS}/{job_id}'
        logging.info(f"Output path: {output_path}")
        sb_jobs_io.update_value(TABLE_JOBS, {'output_path': output_path})
        logging.info(f"Updated jobs table with output path: {output_path}")
        # Set supabase to success
        sb_jobs_io.update_status(job_id, STATUS_SUCCEEDED, 100)
        logging.info(f"Updated status to succeeded for job: {job_id}")

    except Exception as e:
        sb_jobs_io.update_status(job_id, STATUS_FAILED, 0, error=traceback.format_exc()[:8000])
        logging.error(f"Failed to process job: {job_id}")
        raise

if __name__ == '__main__':
    run_job('10bec8d0-bc58-4cbb-b4be-a56e52c17b4a')