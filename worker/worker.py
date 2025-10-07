import os
from common.supabase_client import get_client
from pipeline.pipeline import run_stage1_data_generation
import json
import traceback
import datetime as dt
from collections import defaultdict, Counter
import numpy as np

import json, math, datetime, decimal, uuid
from fractions import Fraction
from pathlib import Path
from enum import Enum
from collections import defaultdict, Counter, OrderedDict, deque
from dataclasses import is_dataclass, asdict
import logging


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
        
        # Run clean pipeline
        adapter_output = adapter.clean_for_sentence(file_to_process)
        logging.info(f"Cleaned to {len(adapter_output)} sentences.")
        words = adapter.clean_for_words(adapter_output)
        logging.info(f"Cleaned to {len(words)} words.")

        # Run data analysis pipeline
        logging.info(f"Tokenizing words...")
        lang_adapter_output = lang_adapter.tokenize(words)
        logging.info(f"Tokenized to {len(lang_adapter_output)} tokens.")

        logging.info(f"Building lexicon from tokens...")
        lexicon = lang_adapter.build_dictionary_from_tokens(lang_adapter_output)
        logging.info(f"Built lexicon with {len(lexicon)} lemmas.")
        logging.info(f"Attaching examples to lexicon...")
        lang_adapter.attach_examples(adapter_output, lexicon)
        logging.info(f"Attached examples to lexicon.")
        ser_lexicon = lang_adapter.finalize_lexicon(lexicon)
        logging.info(f"Finalized lexicon.")
       
        # Put it to bucket results
        results_encoded = json.dumps(ser_lexicon, ensure_ascii=False, indent=2).encode("utf-8")
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
    run_job('04ee7a5e-63e4-4a8b-ab36-af23a5bb34e7')