import hashlib
import json
import logging
import re
import time
import unicodedata
from typing import Tuple

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


def _prepare_cache_entry(
    candidate: Candidate,
):
    """
    Returns a dict entry for translation cache table.
    Expects candidate to have translated_word and translated_example populated.
    """
    if not candidate.translated_word:
        raise ValueError(
            f"Candidate with empty translation: {candidate.form_original_lang}"
        )

    cache_id = _create_id_translation_cache(
        candidate.form_original_lang,
        candidate.sentence_original_lang,
        candidate.source_lang_tag,
        candidate.target_lang_tag,
    )

    return {
        "id": cache_id,
        "form_org_lang": candidate.form_original_lang,
        "sentence_org_lang": candidate.sentence_original_lang,
        "word_target_lang": candidate.translated_word,
        "sentence_target_lang": candidate.translated_example,
        "org_lang": candidate.source_lang_tag,
        "target_lang": candidate.target_lang_tag,
    }


def _is_valid_translation(sentence: str) -> bool:
    if "<i>" not in sentence or "<i></i>" in sentence:
        return False
    else:
        return True


def translate_selection(
    selection: list[Candidate],
    translator: Translator,
    deck_io: DeckIO,
) -> Tuple[list[Candidate], list[Candidate]]:
    """
    Translate the selected candidates using the provided translator.
    Cache key: word: str, sentence: str, source_lang:str, target_lang:str
    """

    if not selection:
        return [], []

    BULK_TRANSLATION = 40

    candidates_cached, candidates_to_translate = _find_cached_translation_batch(
        selection, deck_io
    )
    logging.info(f"Cached {len(candidates_cached)} candidates")
    logging.info(f"To translate {len(candidates_to_translate)} candidates")

    number_to_translate = len(candidates_to_translate)
    # In the future translation should bucket candidates with the same languages.
    # Now languages are inferred from the first candidate.

    target_lang_tag = selection[0].target_lang_tag
    source_lang_tag = selection[0].source_lang_tag

    not_translated_correctly = []

    for start in range(0, number_to_translate, BULK_TRANSLATION):
        end = min(start + BULK_TRANSLATION, number_to_translate)
        candidate_group = candidates_to_translate[start:end]

        sentences_to_translate = []
        for candidate in candidate_group:
            translation_input = _tag_first(
                candidate.sentence_original_lang, candidate.form_original_lang
            )
            candidate.translation_input = translation_input
            sentences_to_translate.append(translation_input)

        res = None
        for attempt in range(2):
            try:
                res = translator.translate(
                    sentences_to_translate,
                    target_lang=target_lang_tag,
                    source_lang=source_lang_tag,
                )
                print(
                    f"DEBUG: Batch {start}-{end}, inputs: {len(sentences_to_translate)}, res: {type(res)} len: {len(res) if hasattr(res, '__len__') else 'N/A'}"
                )
                break  # Success

            except deepl.TooManyRequestsException:
                if attempt == 1:
                    raise
                logging.warning("Too many requests to DeepL, waiting 3s...")
                time.sleep(3)

        if res is None:
            raise Exception("Failed to translate: result is None")

        entries_to_cache = []
        for candidate, translated_example in zip(candidate_group, res):
            candidate.translation_output = translated_example

            if not _is_valid_translation(translated_example):
                logging.warning(
                    "Translation missing tags or empty: input=%r, output=%r",
                    candidate.translation_input,
                    translated_example,
                )
                not_translated_correctly.append(candidate)

                candidate.translated_example = translated_example
                candidate.translated_word = _extract_term(translated_example)
                continue

            candidate.translated_example = translated_example
            candidate.translated_word = _extract_term(translated_example)

            try:
                entries_to_cache.append(_prepare_cache_entry(candidate))
            except ValueError as e:
                logging.error(f"Failed to prepare cache entry: {e}")

        if entries_to_cache:
            try:
                deck_io.upsert_cache_translation(entries_to_cache)
            except Exception as e:
                logging.warning(f"Failed to batch cache translations: {e}")
    logging.info("Not translated correctly: %r", len(not_translated_correctly))
    return candidates_cached + candidates_to_translate, not_translated_correctly
