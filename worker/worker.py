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

# Optional imports (handled if available)
try:
    import numpy as np
except Exception:
    np = None
try:
    import pandas as pd
except Exception:
    pd = None

def make_json_safe(obj, *, _seen=None):
    """
    Recursively convert objects to JSON-serializable types.
    - Dict keys are stringified.
    - Sets/tuples/frozensets -> lists (sorted when possible for stability).
    - defaultdict/Counter/OrderedDict -> dict
    - numpy scalars/arrays -> python scalars/lists
    - pandas Series/DataFrame/Index -> lists/dicts
    - dataclass -> dict
    - Enum -> value
    - datetime/date/time -> ISO 8601 string
    - Decimal/Fraction -> float (or string if non-finite)
    - Path/UUID -> string
    - bytes/bytearray -> UTF-8 string (fallback to base16 if needed)
    - Falls back to str(repr) for unknown types.
    """
    if _seen is None:
        _seen = set()

    oid = id(obj)
    # primitives
    if obj is None or isinstance(obj, (bool, int, float, str)):
        # Handle NaN/Inf explicitly (JSON doesn't allow them)
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return str(obj)
        return obj

    # cycle guard
    if oid in _seen:
        return "<recursion>"
    _seen.add(oid)

    # dataclass
    if is_dataclass(obj) and not isinstance(obj, type):
        return make_json_safe(asdict(obj), _seen=_seen)

    # enums
    if isinstance(obj, Enum):
        return make_json_safe(obj.value, _seen=_seen)

    # datetime
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)

    # decimals & fractions
    if isinstance(obj, (decimal.Decimal, Fraction)):
        try:
            val = float(obj)
            if math.isnan(val) or math.isinf(val):
                return str(obj)
            return val
        except Exception:
            return str(obj)

    # uuid / path
    if isinstance(obj, (uuid.UUID, Path)):
        return str(obj)

    # bytes
    if isinstance(obj, (bytes, bytearray, memoryview)):
        try:
            return obj.decode("utf-8")
        except Exception:
            # hex fallback (safe & compact enough)
            return obj.hex()

    # numpy
    if np is not None:
        if isinstance(obj, np.generic):
            return make_json_safe(obj.item(), _seen=_seen)
        if isinstance(obj, np.ndarray):
            return make_json_safe(obj.tolist(), _seen=_seen)

    # pandas
    if pd is not None:
        if isinstance(obj, pd.Series):
            return make_json_safe(obj.to_dict(), _seen=_seen)
        if isinstance(obj, pd.DataFrame):
            # records are usually handier; change to .to_dict() if you prefer
            return make_json_safe(obj.to_dict(orient="records"), _seen=_seen)
        if isinstance(obj, pd.Index):
            return make_json_safe(obj.tolist(), _seen=_seen)

    # mappings
    if isinstance(obj, (dict, defaultdict, Counter, OrderedDict)):
        out = {}
        for k, v in obj.items():
            try:
                sk = str(k)
            except Exception:
                sk = repr(k)
            out[sk] = make_json_safe(v, _seen=_seen)
        return out

    # sets & frozensets
    if isinstance(obj, (set, frozenset)):
        # sort if possible for deterministic output
        try:
            return [make_json_safe(x, _seen=_seen) for x in sorted(obj, key=lambda x: repr(x))]
        except Exception:
            return [make_json_safe(x, _seen=_seen) for x in obj]

    # sequences
    if isinstance(obj, (list, tuple, deque)):
        return [make_json_safe(x, _seen=_seen) for x in obj]

    # fallback
    try:
        json.dumps(obj)  # if it works, just return as-is
        return obj
    except Exception:
        try:
            return repr(obj)
        except Exception:
            return f"<unserializable {type(obj).__name__}>"

def json_dumps_safe(obj, **kwargs) -> str:
    """Convenience: sanitize then dump."""
    return json.dumps(make_json_safe(obj), ensure_ascii=False, **kwargs)
    
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
        decoded_file = file_to_process.decode('utf-8')
        # Get params
        params = row['params']
        # Pass file to data pipeline
        SB.table('jobs').update({
            'status': 'running',
            'started_at': _utc_now()
        }).eq('id', job_id).execute()
        
        results = run_stage1_data_generation(decoded_file)
        res = json_dumps_safe(results)
        # Put it to bucket results
        results_encoded = json.dumps(res, ensure_ascii=False, indent=2).encode("utf-8")
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