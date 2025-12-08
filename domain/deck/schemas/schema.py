from pydantic import BaseModel, Field
from typing import Optional, Literal
import hashlib
import json

class Candidate(BaseModel):
    lemma: str
    pos: str
    forms: list[str]
    freq: int
    cov_share: float  

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
    id: str                           # stable hash from contents
    lemma: str                        # canonical key (e.g., 'gå')
    prompt: str                       # what user sees first
    answer: str                       # answer side
    sentence: Optional[str] = None    # example sentence (optional)
    pos: Optional[POS] = None         # part of speech

    @staticmethod
    def make_id(*parts: str) -> str:
        """Stable id from relevant content."""
        payload = "||".join(parts).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]  # short & readable

    @classmethod
    def from_minimal(
        cls,
        *,
        lemma: str,
        prompt: str,
        answer: str,
        sentence: Optional[str] = None,
        pos: Optional[POS] = None,
        build_version: str = "v1",
        template_id: str = "basic",
    ) -> Card:
        cid = cls.make_id(lemma, sentence or "", pos or "", build_version, template_id)
        return cls(
            id=cid,
            lemma=lemma,
            prompt=prompt,
            answer=answer,
            sentence=sentence,
            pos=pos
        )

class Deck(BaseModel):
    """
    Minimal deck with just enough metadata to cache/export and show quick stats.
    """
    episode_id: str
    analyzed_hash: str
    build_version: str
    format: OutputFormat = "anki"

    cards: list[Card]

    # quick stats / cache hints
    card_count: int
    unique_lemmas: int
    achieved_coverage: float = 0.0     # 0..1 (fill if you compute it upstream)
    idempotency_key: str               # hash of (analyzed_hash + knobs/version)
    target_lang_back: bool = True

    @staticmethod
    def make_idempotency_key(*parts: str) -> str:
        payload = json.dumps(parts, ensure_ascii=False, sort_keys=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def build(
        cls,
        *,
        episode_id: str,
        analyzed_hash: str,
        build_version: str,
        out_format: OutputFormat,
        cards: list[Card],
        achieved_coverage: float = 0.0,
        knobs_fingerprint: str = ""   # e.g., dump of BuildDeckRequest knobs you consider material
    ) -> Deck:
        # quick stats
        card_count = len(cards)
        unique_lemmas = len({c.lemma for c in cards})

        # idem key ties cache to analyzed payload + knobs + version
        idem = cls.make_idempotency_key(analyzed_hash, knobs_fingerprint, build_version)

        return cls(
            episode_id=episode_id,
            analyzed_hash=analyzed_hash,
            build_version=build_version,
            format=out_format,
            cards=cards,
            card_count=card_count,
            unique_lemmas=unique_lemmas,
            achieved_coverage=achieved_coverage,
            idempotency_key=idem
        )

