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
        cov_share_source=0.05,
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
        cov_share_source=0.05,
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
        cov_share_source=0.05,
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
        cov_share_source=0.05,
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
    deck_io = MagicMock(spec=DeckIO)

    candidate_1 = Candidate(
        lemma="walk",
        pos="verb",
        forms=["walk", "walking"],
        freq=50,
        cov_share_source=0.05,
        form_original_lang="walk",
        sentence_original_lang="I walk slowly.",
        source_lang_tag="en",
        target_lang_tag="pl",
        translated_example="I <i>walk</i> slowly.",  # Note: changed to <i> for consistency with implementation
        translated_word="walk",
    )

    candidate_2 = Candidate(
        lemma="speak",
        pos="verb",
        forms=["speak", "speaking"],
        freq=50,
        cov_share_source=0.05,
        form_original_lang="speak",
        sentence_original_lang="I speak slowly.",
        source_lang_tag="en",
        target_lang_tag="pl",
    )
    # Using <i> tags as expected by the implementation now
    tagged_2 = "I <i>speak</i> slowly."
    translator.translate.return_value = [tagged_2]

    candidates = [candidate_1, candidate_2]

    # Mock finding cached translations: 1 is cached, 2 needs translation
    with patch(
        "domain.translator.translation._find_cached_translation_batch",
        return_value=([candidate_1], [candidate_2]),
    ):
        translated_candidates, failed = translate_selection(
            candidates, translator, deck_io
        )

    # Assertions
    assert len(translated_candidates) == 2
    assert len(failed) == 0
    assert translated_candidates[0].translated_example == "I <i>walk</i> slowly."
    assert translated_candidates[1].translated_example == tagged_2
    assert translated_candidates[1].translated_word == "speak"

    # Verify tracking fields
    assert translated_candidates[1].translation_input == "I <i>speak</i> slowly."
    assert translated_candidates[1].translation_output == tagged_2

    # Verify batch cache was called for candidate_2
    deck_io.upsert_cache_translation.assert_called_once()
    cache_entries = deck_io.upsert_cache_translation.call_args[0][0]
    assert len(cache_entries) == 1
    assert cache_entries[0]["form_org_lang"] == "speak"


def test_translate_selection_empty():
    translator = MagicMock(spec=Translator)
    deck_io = MagicMock(spec=DeckIO)

    translated, failed = translate_selection([], translator, deck_io)

    assert translated == []
    assert failed == []
