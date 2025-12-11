from unittest.mock import MagicMock

from core.ports import DeckIO
from domain.deck.deck_generation.translator.translation import (
    _create_id_translation_cache,
    _find_cached_translation_batch,
)
from domain.deck.schemas.schema import Candidate

mock_deck_io = MagicMock(spec=DeckIO)
mock_deck_io.get_cached.return_value = {}

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
ids = {
    _create_id_translation_cache(
        c.form_original_lang,
        c.sentence_original_lang,
        c.source_lang_tag,
        c.target_lang_tag,
    ): c
    for c in candidates
}
mock_deck_io.get_cached.return_value = ids
# Execute
cached_translation, to_translate = _find_cached_translation_batch(
    candidates, mock_deck_io
)

print(cached_translation)
print(to_translate)
