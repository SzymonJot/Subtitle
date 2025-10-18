# tests/unit/pipeline/test_look_up_cache.py
from typing import Any, Dict, List
import types
import pytest

# --- import the function under test ---
# Adjust this import to your real module path:
# e.g. from pipeline.translation_selection import look_up_cache
from deck.deck_generation import look_up_cache

# We'll monkeypatch create_id_translation_cache inside the module where look_up_cache lives.
# In tests we’ll reference it via that module object (pytest’s monkeypatch will handle it).


class FakeDeckIO:
    """Implements DeckIO.get_cached(ids) -> dict[cache_id, row]."""
    def __init__(self, rows_by_id: Dict[str, Dict[str, Any]]):
        self.rows_by_id = rows_by_id
        self.last_ids = None

    def get_cached(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        self.last_ids = list(ids)
        return {i: self.rows_by_id[i] for i in ids if i in self.rows_by_id}


@pytest.fixture
def monkeypatched_cache_id(monkeypatch, request):
    """
    Patch create_id_translation_cache in the module under test
    with a simple deterministic function of inputs.
    """
    # Adjust this to the module where look_up_cache is defined:
    import deck.deck_generation  as mut  # module under test

    def fake_create_id_translation_cache(word, sentence, src, tgt):
        # Simple, stable ID that matches what tests expect:
        return f"{src}->{tgt}::{word}||{sentence}"

    monkeypatch.setattr(mut, "create_id_translation_cache", fake_create_id_translation_cache)
    return fake_create_id_translation_cache


def test_look_up_cache_mutates_found_and_splits(monkeypatched_cache_id):
    # Arrange
    src, tgt = "sv", "en"
    candidates = [
        {"form_original_lang": "hej", "sentence_original_lang": "hej du"},
        {"form_original_lang": "då",  "sentence_original_lang": "vi ses"},
        {"form_original_lang": "kaffe","sentence_original_lang":"vill du ha kaffe"},
    ]
    # Precompute the IDs the function will generate (must match the fake above)
    mkid = lambda w, s: f"{src}->{tgt}::{w}||{s}"
    cached = {
        mkid("hej", "hej du"): {
            "cache_id": mkid("hej", "hej du"),
            "target_lang_word": "hello",
            "target_lang_sentence": "hello there",
        },
        mkid("kaffe", "vill du ha kaffe"): {
            "cache_id": mkid("kaffe", "vill du ha kaffe"),
            "target_lang_word": "coffee",
            "target_lang_sentence": "do you want coffee",
        },
        # note: "då" is intentionally missing to test not_found
    }
    io = FakeDeckIO(cached)

    # Act
    found, not_found = look_up_cache(candidates, src, tgt, io)

    # Assert: DeckIO called with the expected IDs in order
    assert io.last_ids == [
        mkid("hej", "hej du"),
        mkid("då",  "vi ses"),
        mkid("kaffe","vill du ha kaffe"),
    ]

    # Assert: found/not_found partition and original order preserved
    assert [c["form_original_lang"] for c in found] == ["hej", "kaffe"]
    assert [c["form_original_lang"] for c in not_found] == ["då"]

    # Assert: in-place mutation for found ones
    hej = found[0]
    kaffe = found[1]
    assert hej["translated_word"] == "hello"
    assert hej["translated_example"] == "hello there"
    assert kaffe["translated_word"] == "coffee"
    assert kaffe["translated_example"] == "do you want coffee"

    # No translation fields added to not-found
    assert "translated_word" not in not_found[0]

    # Assert: candidates list objects were mutated (same identities)
    assert candidates[0] is found[0]
    assert candidates[2] is found[1]
    assert candidates[1] is not_found[0]


def test_look_up_cache_empty_input(monkeypatched_cache_id):
    io = FakeDeckIO(rows_by_id={})
    found, not_found = look_up_cache([], "sv", "en", io)
    assert found == []
    assert not_found == []
    # io.last_ids should be [] (depending on your function; if it never calls get_cached on empty, adjust)
    assert io.last_ids == []


def test_look_up_cache_unknown_ids(monkeypatched_cache_id):
    src, tgt = "sv", "en"
    candidates = [
        {"form_original_lang": "x", "sentence_original_lang": "y"},
    ]
    io = FakeDeckIO(rows_by_id={})  # nothing cached
    found, not_found = look_up_cache(candidates, src, tgt, io)
    assert found == []
    assert not_found == candidates
