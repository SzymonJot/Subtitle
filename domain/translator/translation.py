import hashlib
import json
import logging
import re
import time
import unicodedata
from typing import List, Tuple

import deepl

from core.ports import DeckIO
from domain.deck.schemas.schema import Candidate
from domain.translator.translator import TRANS_VERSION, Translator

SEP_FIND = re.compile(r"[\r\n\x85\u2028\u2029]")


def _create_id_translation_cache(
    word: str,
    sentence: str,
    source_lang_tag: str,
    target_lang_tag: str,
    translation_ver: str = TRANS_VERSION,
) -> str:
    """
    Creates ID for translation cache table based on passed parameters.
    Key are case sensitive.
    All white spaces are collapsed as it won't change learning experience.
    """

    if SEP_FIND.search(sentence):
        raise ValueError("CR/LF characters/lines break found in sentence!")

    if SEP_FIND.search(word):
        raise ValueError("CR/LF characters/lines break found in word!")

    # Canocnical Unicode representation
    word_cleaned = unicodedata.normalize("NFKC", word.strip())
    sentence = " ".join(sentence.split())
    sentence_cleaned = unicodedata.normalize("NFKC", sentence)

    if not word_cleaned:
        raise ValueError("Incorrect word")
    if not sentence_cleaned:
        raise ValueError("Incorrect sentence")
    if not translation_ver:
        raise ValueError("Incorrect version")

    image = {
        "word": word_cleaned,
        "sentence": sentence_cleaned,
        "target_lang_tag": target_lang_tag,
        "source_lang_tag": source_lang_tag,
        "translation_ver": translation_ver,
    }

    return hashlib.sha256(
        json.dumps(
            image, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode(encoding="utf-8")
    ).hexdigest()


def _look_up_translation_from_cache(
    candidates_to_check: list[Candidate],
    deck_io: DeckIO,
) -> dict[str, dict]:
    """
    Function returns the candidates that matched cache
    """
    ids = []
    for candidate in candidates_to_check:
        cache_id = _create_id_translation_cache(
            candidate.form_original_lang,
            candidate.sentence_original_lang,
            candidate.source_lang_tag,
            candidate.target_lang_tag,
        )
        ids.append(cache_id)

    res = deck_io.get_cached(ids)

    return res


def _find_cached_translation_batch(
    selection: list[Candidate],
    deck_io: DeckIO,
) -> Tuple[list[Candidate], list[Candidate]]:
    """
    Function mutates the candidates that matched cache
    """
    n = len(selection)
    batch = 100
    to_translate = []
    cached_translation = []

    for start in range(0, n, batch):
        end = min(start + batch, n)
        candidates_to_check = selection[start:end]
        res = _look_up_translation_from_cache(candidates_to_check, deck_io)

        for candidate in candidates_to_check:
            cache_id = _create_id_translation_cache(
                candidate.form_original_lang,
                candidate.sentence_original_lang,
                candidate.source_lang_tag,
                candidate.target_lang_tag,
            )
            cached_candidate = res.get(cache_id, None)
            if cached_candidate:
                candidate.translated_word = cached_candidate["word_target_lang"]
                candidate.translated_example = cached_candidate["sentence_target_lang"]
                cached_translation.append(candidate)
            else:
                to_translate.append(candidate)

    return cached_translation, to_translate


def _tag_first(s, target):
    # case-insensitive, whole-word; preserves original casing in the sentence
    pattern = re.compile(rf"\b{re.escape(target)}\b", flags=re.IGNORECASE)
    s = pattern.sub(lambda m: "<i>" + m.group(0) + "</i>", s, count=1)
    return s


def _extract_term(target_text: str) -> str:
    a, b = target_text.find("<i>"), target_text.find("</i>")
    if a != -1 and b != -1 and b > a:
        return target_text[a + 3 : b]
    return ""


def _cache_translation(
    candidate: Candidate,
    deck_io: DeckIO,
):
    if not candidate.translated_word == "":
        # Calculate ID
        cache_id = _create_id_translation_cache(
            candidate.form_original_lang,
            candidate.sentence_original_lang,
            candidate.source_lang_tag,
            candidate.target_lang_tag,
        )

        entry = {
            "id": cache_id,
            "form_org_lang": candidate.form_original_lang,
            "sentence_org_lang": candidate.sentence_original_lang,
            "word_target_lang": candidate.translated_word,
            "sentence_target_lang": candidate.translated_example,
            "org_lang": candidate.source_lang_tag,
            "target_lang": candidate.target_lang_tag,
        }

        try:
            deck_io.upsert_cache_translation([entry])
        except Exception as e:
            raise Exception(f"Failed to cache translation: {e}")
    else:
        raise Exception(
            f"Candidate with empty translation: {candidate.form_original_lang} in {candidate.sentence_original_lang}"
        )


def translate_selection(
    selection: List[Candidate],
    translator: Translator,
    deck_io: DeckIO,
) -> List[Candidate]:
    """
    Translate the selected candidates using the provided translator.
    Cache key: word: str, sentence: str, source_lang:str, target_lang:str
    """

    candidates_cached, candidates_to_translate = _find_cached_translation_batch(
        selection, deck_io
    )
    logging.info(f"Cached {len(candidates_cached)} candidates")
    logging.info(f"To translate {len(candidates_to_translate)} candidates")
    for candidate in candidates_to_translate:
        form = candidate.form_original_lang
        sentence = candidate.sentence_original_lang
        sentence_tagged = _tag_first(sentence, form)
        logging.info(f"Translating {sentence_tagged}")

        try:
            res = translator.translate(
                sentence_tagged,
                target_lang=candidate.target_lang_tag,
                source_lang=candidate.source_lang_tag,
            )
            logging.info(
                f"Translated {candidate.form_original_lang} in {candidate.sentence_original_lang}"
            )

        except deepl.TooManyRequestsException:
            time.sleep(3)
            res = translator.translate(
                sentence_tagged,
                target_lang=candidate.target_lang_tag,
                source_lang=candidate.source_lang_tag,
            )

        if res == "":
            raise Exception(
                f"Failed to translate {candidate.form_original_lang} in {candidate.sentence_original_lang}"
            )
        target_lang_sentence = res
        logging.info("Translated sentence: " + target_lang_sentence)
        target_lang_word = _extract_term(target_lang_sentence)
        logging.info("Extracted term: " + target_lang_word)

        candidate.translated_example = target_lang_sentence
        candidate.translated_word = target_lang_word
        try:
            _cache_translation(candidate, deck_io)
        except Exception as e:
            raise Exception(f"Failed to cache translation: {e}, Candidate: {candidate}")
    return candidates_cached + candidates_to_translate
