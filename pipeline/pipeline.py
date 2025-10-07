import regex as re
import unicodedata
from collections import defaultdict
from nltk.util import ngrams
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk
from  pprint import pprint
from collections import Counter
import matplotlib.pyplot as plt
import genanki
from deep_translator import GoogleTranslator
import stanza
import os
import deepl
import hashlib, html
from typing import Dict, List, Tuple
import time, unicodedata as ud
from dotenv import load_dotenv
from nlp.lexicon.schema import EpisodeDataProcessed
import json, unicodedata, time
from typing import Dict, List
import logging

load_dotenv()

def _t():
    return time.perf_counter()

def process_episode(file_bytes: bytes,
                    adapter,          # srt_adapter
                    lang_adapter,     # sv_adapter
                    max_examples_per_lemma: int = 5) -> bytes:
    t0 = _t()

    # 1) sentences
    sentences: List[str] = adapter.clean_for_sentence(file_bytes)
    logging.info("Cleaned to %d sentences (%.3fs)", len(sentences), _t()-t0)

    # 2) words
    t1 = _t()
    words: List[str] = adapter.clean_for_words(sentences)
    # optional: words = [w.lower() for w in words]
    logging.info("Cleaned to %d words (%.3fs)", len(words), _t()-t1)

    # 3) tokenize
    t2 = _t()
    tokens = lang_adapter.tokenize(words)  # dict[str, NLPToken]
    logging.info("Tokenized to %d tokens (%.3fs)", len(tokens), _t()-t2)

    # 4) lemmas
    t3 = _t()
    lexicon: Dict[str, LemmaSV] = lang_adapter.build_dictionary_from_tokens(tokens)
    logging.info("Built lexicon with %d lemmas (%.3fs)", len(lexicon), _t()-t3)

    # 5) examples (cap per lemma inside the method)
    t4 = _t()
    lang_adapter.attach_examples(sentences, lexicon)
    logging.info("Attached examples (%.3fs)", _t()-t4)

    # 6) finalize → JSON bytes (stable order)
    t5 = _t()
    # Option A: wrap and let Pydantic do the JSON
    payload = EpisodeDataProcessed(episode_data_processed=lexicon)
    json_str = payload.model_dump_json(indent=2)  # already JSON-safe

    logging.info("Finalized lexicon (%.3fs). Total: %.3fs", _t()-t5, _t()-t0)
    return json_str



if __name__ == '__main__':
    from pprint import pformat  
    import pickle
    results = run_stage1_data_generation(read_file('ep1.srt'))
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