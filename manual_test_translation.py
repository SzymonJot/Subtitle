import sys
import traceback
from unittest.mock import MagicMock

from core.ports import DeckIO
from domain.deck.deck_generation.translator.translation import (
    _create_id_translation_cache,
    _look_up_cache,
)
from domain.deck.schemas.schema import Candidate


def run_test():
    print("Starting manual test...")
    try:
        mock_deck_io = MagicMock(spec=DeckIO)
        source_lang = "EN"
        target_lang = "PL"

        print("Creating candidates...")
        candidate_found = Candidate(
            lemma="run",
            pos="verb",
            forms=["run", "running"],
            freq=100,
            cov_share=0.1,
            form_original_lang="run",
            sentence_original_lang="I run daily.",
        )

        candidate_not_found = Candidate(
            lemma="walk",
            pos="verb",
            forms=["walk", "walking"],
            freq=50,
            cov_share=0.05,
            form_original_lang="walk",
            sentence_original_lang="I walk slowly.",
        )

        candidates = [candidate_found, candidate_not_found]

        print("Calculating IDs...")
        found_id = _create_id_translation_cache(
            candidate_found.form_original_lang,
            candidate_found.sentence_original_lang,
            source_lang,
            target_lang,
        )
        print(f"Found ID: {found_id}")

        not_found_id = _create_id_translation_cache(
            candidate_not_found.form_original_lang,
            candidate_not_found.sentence_original_lang,
            source_lang,
            target_lang,
        )

        mock_deck_io.get_cached.return_value = {
            found_id: {
                "target_lang_word": "biegać",
                "target_lang_sentence": "Biegam codziennie.",
            }
        }

        print("Calling _look_up_cache...")
        found, not_found = _look_up_cache(
            candidates, source_lang, target_lang, mock_deck_io
        )

        print(f"Found: {len(found)}, Not Found: {len(not_found)}")

        if len(found) != 1:
            print("FAIL: Expected 1 found")
            sys.exit(1)
        if len(not_found) != 1:
            print("FAIL: Expected 1 not found")
            sys.exit(1)

        if found[0] != candidate_found:
            print("FAIL: Found candidate mismatch")
            sys.exit(1)

        if candidate_found.translated_word != "biegać":
            print(
                f"FAIL: Translation not applied. Got {candidate_found.translated_word}"
            )
            sys.exit(1)

        print("SUCCESS: usage of attribute access worked!")

    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_test()
