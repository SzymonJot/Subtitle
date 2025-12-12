from typing import Literal, Optional

from pydantic import BaseModel


class Candidate(BaseModel):
    lemma: str
    pos: str
    forms: list[str]
    freq: int
    cov_share: float

    source_lang_tag: Optional[str] = None
    target_lang_tag: Optional[str] = None

    examples: Optional[dict] = None
    score: Optional[float] = None

    # - Populated at translation step
    form_original_lang: Optional[str] = None
    sentence_original_lang: Optional[str] = None
    translated_word: Optional[str] = None
    translated_example: Optional[str] = None


POS = Literal["NOUN", "VERB", "ADJ", "ADV"]
OutputFormat = Literal["anki", "quizlet", "csv"]

# ---------- Simple Card ----------


class Card(BaseModel):
    """
    Minimal unit for study/export.
    Keep only the fields you actually render or filter by.
    """

    lemma: str  # canonical key (e.g., 'gå')
    prompt: str  # what user sees first
    answer: str  # answer side
    sentence: Optional[str] = None  # example sentence (optional)
    sentence_translation: Optional[str] = (
        None  # example sentence translation (optional)
    )
    pos: Optional[POS] = None  # part of speech
    source_lang_tag: Optional[str] = None
    target_lang_tag: Optional[str] = None


class Deck(BaseModel):
    """
    Minimal deck with just enough metadata to cache/export and show quick stats.
    """

    id: str
    episode_name: str
    analyzed_hash: str
    build_version: str
    # quick stats
    card_count: int
    achieved_coverage: float = 0.0
    stopped_reason: str = ""
    target_lang_back: bool = True
