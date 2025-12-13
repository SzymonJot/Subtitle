import hashlib
import json
import unicodedata
from unittest.mock import MagicMock, patch

from core.ports import DeckIO
from domain.deck.schemas.schema import Candidate
from domain.translator.translation import (
    _create_id_translation_cache,
    _find_cached_translation_batch,
    _look_up_translation_from_cache,
    _tag_first,
    translate_selection,
)
from domain.translator.translator import Translator


def test_id_create_translation_cache():
    # Setup
    image = {
        "word": "run",
        "sentence": "I run daily.",
        "target_lang_tag": "pl",
        "source_lang_tag": "en",
        "translation_ver": "DEEPL:2025-09",
    }

    image["word"] = unicodedata.normalize("NFKC", image["word"].strip())
    image["sentence"] = " ".join(image["sentence"].split())
    image["sentence"] = unicodedata.normalize("NFKC", image["sentence"])

    expected_id = hashlib.sha256(
        json.dumps(
            image, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode(encoding="utf-8")
    ).hexdigest()

    # Execute
    id = _create_id_translation_cache(**image)

    # Assertions
    assert id == expected_id


def test_look_up_translation_from_cache():
    # Setup
    mock_deck_io = MagicMock(spec=DeckIO)

    candidate_1 = Candidate(
        lemma="walk",
        pos="verb",
        forms=["walk", "walking"],
        freq=50,
        cov_share=0.05,
        form_original_lang="walk",
        sentence_original_lang="I walk slowly.",
        source_lang_tag="en",
        target_lang_tag="pl",
    )

    candidate_2 = Candidate(
        lemma="speak",
        pos="verb",
        forms=["speak", "speaking"],
        freq=50,
        cov_share=0.05,
        form_original_lang="speak",
        sentence_original_lang="I speak slowly.",
        source_lang_tag="en",
        target_lang_tag="pl",
    )

    ids = {
        _create_id_translation_cache(
            c.form_original_lang,
            c.sentence_original_lang,
            c.source_lang_tag,
            c.target_lang_tag,
        ): c
        for c in [candidate_1, candidate_2]
    }

    mock_deck_io.get_cached.return_value = ids
    # Execute
    res = _look_up_translation_from_cache([candidate_1, candidate_2], mock_deck_io)

    # Assertions
    assert res == ids


def test_find_cached_translation_batch():
    mock_deck_io = MagicMock(spec=DeckIO)

    candidate_1 = Candidate(
        lemma="walk",
        pos="verb",
        forms=["walk", "walking"],
        freq=50,
        cov_share=0.05,
        form_original_lang="walk",
        sentence_original_lang="I walk slowly.",
        source_lang_tag="en",
        target_lang_tag="pl",
    )

    candidate_2 = Candidate(
        lemma="speak",
        pos="verb",
        forms=["speak", "speaking"],
        freq=50,
        cov_share=0.05,
        form_original_lang="speak",
        sentence_original_lang="I speak slowly.",
        source_lang_tag="en",
        target_lang_tag="pl",
    )

    candidates = [candidate_1, candidate_2]

    ids = {}

    mock_deck_io.get_cached.return_value = ids

    # Execute
    cached_translation, to_translate = _find_cached_translation_batch(
        candidates, mock_deck_io
    )

    # Assertions
    assert cached_translation == []
    assert to_translate == candidates


def test_translate_selection():
    translator = MagicMock(spec=Translator)

    candidate_1 = Candidate(
        lemma="walk",
        pos="verb",
        forms=["walk", "walking"],
        freq=50,
        cov_share=0.05,
        form_original_lang="walk",
        sentence_original_lang="I walk slowly.",
        source_lang_tag="en",
        target_lang_tag="pl",
        translated_example="I <term>walk</term> slowly.",
    )

    candidate_2 = Candidate(
        lemma="speak",
        pos="verb",
        forms=["speak", "speaking"],
        freq=50,
        cov_share=0.05,
        form_original_lang="speak",
        sentence_original_lang="I speak slowly.",
        source_lang_tag="en",
        target_lang_tag="pl",
    )
    tagged_2 = _tag_first(
        candidate_2.sentence_original_lang, candidate_2.form_original_lang
    )
    translator.translate.side_effect = [tagged_2]

    candidates = [candidate_1, candidate_2]

    with (
        patch(
            "domain.translator.translation._find_cached_translation_batch",
            return_value=([candidate_1], [candidate_2]),
        ) as mock_find_cached_translation_batch,
        patch(
            "domain.translator.translation._cache_translation",
            return_value=None,
        ) as mock_cache_translation,
    ):
        translated_candidates = translate_selection(
            candidates, translator, MagicMock(spec=DeckIO)
        )

    # Assertions
    assert translated_candidates[0].translated_example == "I <term>walk</term> slowly."
    assert translated_candidates[1].translated_example == tagged_2
