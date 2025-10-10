import regex as re
import unicodedata
from collections import defaultdict
from  pprint import pprint
from collections import Counter
import os
from typing import Dict, List, Tuple
import time, unicodedata as ud
from dotenv import load_dotenv
from nlp.lexicon.schema import EpisodeDataProcessed
import json, unicodedata, time
from typing import Dict, List
import logging
from nlp.lexicon.schema import Stats
from typing import Literal
from pydantic import BaseModel

load_dotenv()

import hashlib
import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

def _t():
    return time.perf_counter()

def run_deck_pipeline(
    analyzed_payload: Dict[str, Any],
    req: BuildDeckRequest,
    *,
    results_prefix: str = "results",
) -> Tuple[BuiltDeck, bytes]:
    """
    Pure pipeline runner. Deterministic given (analyzed_payload, req).
    No network, no DB, no storage here.
    """
    #rng_seed = req.deterministic_seed() # =H(analyzed_hash ⊕ normalized_params ⊕ build_version) rng_seed = f(idempotency_key) (e.g., take first 8 hex bytes → int)
    #Figure out the impodency key: https://chatgpt.com/g/g-p-68e7fd660adc8191be389c9408063e39-persdeck/c/68e7fd9e-acc0-832c-826e-e45c2550499d
    # 1) Candidates
    candidates = select_candidates(analyzed_payload, req) # filtered by POS, known words, etc.

    # 2) Score + rank (uses seed only for deterministic tie-breaking if needed)
    ranked = score_and_rank(candidates, req, rng_seed) # computes score

    # 3) Enforce hard knobs (POS, known words, max per POS, etc.)
    filtered = apply_constraints(ranked, req) 

    # 4) Pick until you hit coverage or cap
    selection = pick_until_target(filtered, req) 

    selection_with_tx = translate_selection(selection, translator, req)  # side-effect + cache
    
    cards = assemble_cards(selection_with_tx, analyzed_payload, req)

    # 6) Render to bytes (anki/quizlet/csv) — still pure
    file_bytes, out_format = render_export(cards, req)

    # 7) Stats for UI/audit
    stats = collect_stats(cards, analyzed_payload, req)

    # 8) Canonical storage path comes from idempotency key
    result_path = f"{results_prefix}/{req.episode_id}/{req.idempotency_key()}." + (
        "csv" if out_format == "csv" else "zip"
    )

    # 9) Final metadata object (no upload here)
    built = build_metadata(
        req=req,
        stats=stats,
        file_bytes=file_bytes,
        format_=out_format,
        result_path=result_path,
    )

    return built, file_bytes


if __name__ == '__main__':
    from pprint import pformat  
    import pickle
    from nlp.content.srt_adapter import SRTAdapter
    from nlp.lang.sv.lang_adapter import sv_lang_adapter

    results = process_episode(
        open("test/ep1.srt", "rb").read(),
        adapter = SRTAdapter(),
        lang_adapter = sv_lang_adapter()
    )
    # binary snapshot (full fidelity)
    with open('data.pkl', 'wb') as f:
        pickle.dump(results, f)

    # human-readable peek (no JSON needed)
    with open('data_preview.txt', 'w', encoding='utf-8') as f:
        f.write(pformat(results, width=120, compact=True))

    print("Saved data.pkl and data_preview.txt")
    
    #quotas = {"VERB": 0.35, "NOUN": 0.40, "ADJ": 0.15, "ADV": 0.10}
    #study_list, picked_by_pos = select_top_quota(lemma_count, target_total=260, quotas=quotas)
    #cov = coverage(lemma_count)
    #get_coverage_info(lemma_count)
    #print(f"Estimated token coverage: {cov:.1%}")