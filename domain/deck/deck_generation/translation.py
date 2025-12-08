import langcodes
import unicodedata
import deepl
import os
import re
import json
import hashlib
from typing import List, Tuple
from core.ports import DeckIO
from deck.schemas.schema import Candidate

TRANS_VERSION = 'DEEPL:2025-09'
DEEPL_AUTH_KEY  = os.getenv('DEEPL_AUTH_KEY')

translator = deepl.Translator(DEEPL_AUTH_KEY)



SEP_FIND = re.compile(r'[\r\n\x85\u2028\u2029]')

def create_id_translation_cache(word: str, sentence: str, source_lang:str, target_lang: str, translation_ver:str = TRANS_VERSION) -> str:
    """
    Creates ID for translation cache table based on passed parameters.
    Key are case sensitive.
    All white spaces are collapsed as it won't change learning experience.
    """

    if SEP_FIND.search(sentence):
        raise ValueError("CR/LF characters/lines break found in sentence!")
    
    if SEP_FIND.search(word):
        raise ValueError("CR/LF characters/lines break found in word!")
    
    source_tag = langcodes.Language.get(source_lang).to_tag()
    target_tag = langcodes.Language.get(target_lang).to_tag()

    
    word_cleaned = unicodedata.normalize("NFKC",word.strip())
    sentence = " ".join(sentence.split())
    sentence_cleaned =  unicodedata.normalize("NFKC", sentence )

    if not word_cleaned:
        raise ValueError("Incorrect word")
    if not sentence_cleaned:
        raise ValueError("Incorrect sentence")
    if not translation_ver:
        raise ValueError("Incorrect version")
    
    image = {}
    image['word'] = word_cleaned
    image['sentence'] = sentence_cleaned
    image['target_lang'] = target_tag
    image['source_lang'] = source_tag
    image['translation_ver'] = translation_ver

    return hashlib.sha256(json.dumps(image, sort_keys=True, ensure_ascii=False, separators=(',',':')).encode(encoding='utf-8')).hexdigest()


def look_up_cache(candidates_to_check:List, source_lang, target_lang, deck_io: DeckIO) -> Tuple[List[Candidate], List[Candidate]]:
    """
    Function mutates the candidates that matched cache
    """
    ids = []
    found = []
    not_found = []
    for candidate in candidates_to_check:
        cache_id = create_id_translation_cache(candidate['form_original_lang'], candidate['sentence_original_lang'], source_lang, target_lang)
        ids.append(cache_id)

    res = deck_io.get_cached(ids)

    if len(ids) != len(candidates_to_check):
        raise ValueError("Different len between cache ids and candidates to check")
        
    for candidate, cache_id in zip(candidates_to_check, ids):
        res_content = res.get(cache_id, None)
        if res_content:
            candidate['translated_word'] = res_content['target_lang_word']
            candidate['translated_example'] = res_content['target_lang_sentence']
            found.append(candidate)
        else:
            not_found.append(candidate)

    return found, not_found

def translate_selection(selection: List[Candidate], translator, source_lang:str, target_lang:str, deck_io: DeckIO) -> List[Candidate]:
    """
    Translate the selected candidates using the provided translator.
    Cache key: word: str, sentence: str, source_lang:str, target_lang:str
    """

    def tag_first(s, target):
    # case-insensitive, whole-word; preserves original casing in the sentence
        pattern = re.compile(rf"\b{re.escape(target)}\b", flags=re.IGNORECASE)
        return pattern.sub(lambda m: "<term>"+m.group(0)+"</term>", s, count=1)
    
    source_lang_tag = langcodes.Language.get(source_lang).to_tag()
    target_lang_tag = langcodes.Language.get(target_lang).to_tag()

    def extract_term(target_text: str) -> str:
        a, b = target_text.find("<term>"), target_text.find("</term>")
        if a != -1 and b != -1 and b > a:
            return target_text[a+6:b]
        a, b = target_text.find("&lt;term&gt;"), target_text.find("&lt;/term&gt;")
        if a != -1 and b != -1 and b > a:
            return target_text[a+12:b]
        return ""
    
    to_translate = []
    cached_translation = []
 
    n = len(selection)
    batch = 100

    for start in range(0, n, batch):
        end = min(start + batch, n )
        candidates_to_check = selection[start:end]
        
        cand_found, cand_not_found = look_up_cache(candidates_to_check, source_lang, target_lang, deck_io)

        to_translate += cand_not_found 
        cached_translation += cand_found
        
    
    for candidate in to_translate:
        form = candidate["form_original_lang"]
        sentence = candidate["sentence_original_lang"]
        
        sentence_tagged = tag_first(sentence, form)
    
        kwargs = dict(
            source_lang=source_lang_tag, target_lang=target_lang_tag,
            tag_handling="xml", non_splitting_tags=["term"],
            preserve_formatting=True, outline_detection=False
        )

        try:
            res = translator.translate_text(sentence_tagged, **kwargs)
        except deepl.TooManyRequestsException:
            time.sleep(3)
            res = translator.translate_text(sentence_tagged, **kwargs)
        
        target_lang_sentence = res.text
        target_lang_word = extract_term(target_lang_sentence)

        candidate["translated_example"] = target_lang_sentence
        candidate["translated_word"] = target_lang_word

        if not target_lang_word == "":
            # Create CacheEntry
            # We need to construct CacheEntry object or dict
            # CacheEntry(id, form_org_lang, sentence_org_lang, word_target_lang, sentence_target_lang, org_lang, target_lang)
            
            # Calculate ID
            cache_id = create_id_translation_cache(form, sentence, source_lang, target_lang)
            
            entry = {
                "id": cache_id,
                "form_org_lang": form,
                "sentence_org_lang": sentence,
                "word_target_lang": target_lang_word,
                "sentence_target_lang": target_lang_sentence,
                "org_lang": source_lang,
                "target_lang": target_lang
            }
            
            # Upsert immediately (or batch?)
            # For now immediately
            try:
                deck_io.upsert_cache_translation([entry])
            except Exception as e:
                print(f"Failed to cache translation: {e}")

    
    return cached_translation + to_translate