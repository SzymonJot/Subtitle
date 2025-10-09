
from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import hashlib
import json

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
    front: str                        # what user sees first
    back: str                         # answer side
    sentence: Optional[str] = None    # example sentence (optional)
    pos: Optional[POS] = None
    tags: List[str] = Field(default_factory=list)

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
        front: str,
        back: str,
        sentence: Optional[str] = None,
        pos: Optional[POS] = None,
        tags: Optional[List[str]] = None,
        build_version: str = "v1",
        template_id: str = "basic",
    ) -> "Card":
        cid = cls.make_id(lemma, front, back, sentence or "", pos or "", build_version, template_id)
        return cls(
            id=cid,
            lemma=lemma,
            front=front,
            back=back,
            sentence=sentence,
            pos=pos,
            tags=tags or [],
        )

# ---------- Simple Deck ----------

class Deck(BaseModel):
    """
    Minimal deck with just enough metadata to cache/export and show quick stats.
    """
    episode_id: str
    analyzed_hash: str
    build_version: str
    format: OutputFormat = "anki"

    cards: List[Card]

    # quick stats / cache hints
    card_count: int
    unique_lemmas: int
    achieved_coverage: float = 0.0     # 0..1 (fill if you compute it upstream)
    idempotency_key: str               # hash of (analyzed_hash + knobs/version)
    cached: bool = False

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
        cards: List[Card],
        achieved_coverage: float = 0.0,
        knobs_fingerprint: str = "",   # e.g., dump of BuildDeckRequest knobs you consider material
        cached: bool = False,
    ) -> "Deck":
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
            idempotency_key=idem,
            cached=cached,
        )
