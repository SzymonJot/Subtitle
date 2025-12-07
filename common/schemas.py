from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
import hashlib
import json
from core.versions import TRANSLATION_ENGINE_VERSION

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
    prompt: str                        # what user sees first
    answer: str                         # answer side
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
        prompt: str,
        answer: str,
        sentence: Optional[str] = None,
        pos: Optional[POS] = None,
        tags: Optional[List[str]] = None,
        build_version: str = "v1",
        template_id: str = "basic",
    ) -> "Card":
        cid = cls.make_id(lemma, sentence or "", pos or "", build_version, template_id)
        return cls(
            id=cid,
            lemma=lemma,
            prompt=prompt,
            answer=answer,
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
    
class ExportOptions(BaseModel):
    filename_base: Optional[str] = None                      # e.g., "bonusfamiljen-s01e01"
    include_audio: bool = False
    add_tags_prefix: Optional[str] = None                    # e.g., "SV"
    template_id: Optional[str] = None                        # which card template to use



class BuiltDeck(BaseModel):
    # Provenance
    episode_id: str
    analyzed_hash: str
    idempotency_key: str
    build_version: str

    # File info
    format: Literal["anki", "quizlet", "csv"]
    result_path: str          # e.g., "results/{episode_id}/{idempotency_key}.zip"
    size_bytes: int
    checksum_sha256: str

    # Quick stats
    card_count: int
    unique_lemmas: int
    achieved_coverage: float  # 0.0–1.0

    # Flags
    cached: bool = False


class CacheEntry(BaseModel):
    id: str
    form_org_lang: str
    sentence_org_lang: str
    word_target_lang: str
    sentence_target_lang: str
    org_lang: str
    target_lang: str
    
class ExportOptions(BaseModel):
    include_media: bool = True


DIFFICULTY_SCORING = Literal["FREQ", "INFORMATION_GAIN", "MIXED"]
OUTPUT_FORMAT = Literal["ANKI", "QUIZLET", "CSV"]

class BuildDeckRequest(BaseModel):
    # Request to build a deck of flashcards from analyzed episode data. #
    # ---- User-tunable knobs (the ones that define the output) ----
    analyzed_hash: str
    target_coverage: Optional[float] = Field(0.90, ge=0.10, le=1.00)
    max_cards: Optional[int] = Field(default=None, ge=1)
    max_share_per_pos: Dict[str, float] = Field(default_factory=dict)  # e.g., {"NOUN": 0.5, "VERB": 0.5}
    target_share_per_pos: Optional[Dict[str, float]] = Field(default_factory=dict)
    difficulty_scoring: DIFFICULTY_SCORING = "FREQ"
    output_format: OUTPUT_FORMAT = "ANKI"
    example_settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    lang_opts: Dict[str, Dict[str,Any]] = Field(default_factory=dict)
    export_options: ExportOptions = Field(default_factory=ExportOptions)
    build_version: str
    params_schema_version: Literal["v1"] = "v1"
    requested_by: str
    requested_at_iso: str

