import os
from common.supabase_client import get_client
import json
import traceback
import datetime as dt
import json
import logging
from pipeline.pipeline import process_episode


SB = get_client(os.environ["SUPABASE_URL"], os.environ['SUPABASE_SERVICE_KEY'])

def _utc_now():
    return dt.datetime.utcnow().isoformat() + 'Z'

def run_job(job_id: str):
    try:
        # Get row from supabase for this job id
        row = SB.table('jobs').select('*').eq('id', job_id).execute().data[0]
        # Get path for file 
        in_path = row['input_path']
        # Fetch file
        file_to_process = SB.storage.from_('uploads').download(in_path)
        # Get params
        params = row['params']
        # Pass file to data pipeline
        SB.table('jobs').update({
            'status': 'running',
            'started_at': _utc_now()
        }).eq('id', job_id).execute()
        
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

        SB.storage.from_('results').upload(job_id,results_encoded, {'content-type':'application/json'})
        # Put result path to jobs table
        output_path = f'results/{job_id}'
        SB.table('jobs').update({'output_path': output_path}).eq('id', job_id).execute()
        # Set supabase to success
        SB.table('jobs').update({
            'status': 'succeeded',
            'progress': 100,
            'finished_at': _utc_now()
        }).eq('id', job_id).execute()

    except Exception as e:
        SB.table('jobs').update({
            'status': 'failed',
            'progress': 0,
            'finished_at': _utc_now(),
            'error': traceback.format_exc()[:8000]
        }).eq('id', job_id).execute()
        raise

if __name__ == '__main__':
    run_job('10bec8d0-bc58-4cbb-b4be-a56e52c17b4a')