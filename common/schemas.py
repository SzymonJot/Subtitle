from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ---------- Simple Deck ----------


class ExportOptions(BaseModel):
    filename_base: Optional[str] = None  # e.g., "bonusfamiljen-s01e01"
    include_sentence: bool = False
    add_tags_prefix: Optional[str] = None  # e.g., "SV"
    template_id: Optional[str] = None  # which card template to use


class BuiltDeck(BaseModel):
    # Provenance
    episode_id: str
    job_id: str
    idempotency_key: str
    build_version: str

    # File info
    format: Literal["anki", "quizlet", "csv"]
    result_path: str  # e.g., "results/{episode_id}/{idempotency_key}.zip"
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


DIFFICULTY_SCORING = Literal["FREQ"]
OUTPUT_FORMAT = Literal["ANKI", "QUIZLET", "CSV"]


class BuildDeckRequest(BaseModel):
    # Request to build a deck of flashcards from analyzed episode data. #
    # ---- User-tunable knobs (the ones that define the output) ----
    job_id: str  # hash from job table
    target_coverage: Optional[float] = Field(0.90, ge=0.10, le=1.00)
    deck_name: str
    max_cards: Optional[int] = Field(default=None, ge=1)
    max_share_per_pos: Dict[str, float] = Field(
        default_factory=dict
    )  # e.g., {"NOUN": 0.5, "VERB": 0.5}
    target_share_per_pos: Optional[Dict[str, float]] = Field(default_factory=dict)
    difficulty_scoring: DIFFICULTY_SCORING = "FREQ"
    exclude_known_lemmas: Optional[List[str]] = Field(default_factory=list)
    example_settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    lang_opts: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    target_lang_tag: str
    build_version: str
    params_schema_version: Literal["v1"] = "v1"
    requested_by: str
    requested_at_iso: str


class ExportDeckRequest(BaseModel):
    deck_id: int
    output_format: OUTPUT_FORMAT
    export_options: ExportOptions = Field(default_factory=ExportOptions)
