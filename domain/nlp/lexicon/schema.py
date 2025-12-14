# pip install pydantic>=2
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class NLPToken(BaseModel):
    form: str  # surface, lowercased
    lemma: str  # lemma (or same as form)
    pos: Optional[str] = None  # UPOS/XPOS
    other: Dict[str, Any] = (
        None  # language-specific: {"artikel":"en", "gender":"utrum", ...}
    )


class SentenceRec(BaseModel):
    text: str
    meta: Dict[
        str, Any
    ]  # {"start":12.34,"end":15.67,"speaker":"A","source_id":"..."} safe primitives only


class LemmaBase(BaseModel):
    pos: str
    forms: List[str]
    examples: Dict[str, List[str]]
    model_config = ConfigDict(extra="forbid")
    forms_freq: Dict[str, int] = Field(default_factory=dict)  # per-form token counts
    forms_cov: Dict[str, float] = Field(
        default_factory=dict
    )  # per-form coverage share (0..1)
    to_learn: bool = Field(default=True)


class LemmaSV(LemmaBase):
    lang: Literal["sv"]
    artikel: Optional[Literal["en", "ett"]] = None
    gender: Optional[Literal["Com", "Neut"]] = None
    definite: Optional[Literal["Ind", "Def"]] = None


LemmaEntry = Union[LemmaSV]


class Stats(BaseModel):
    total_tokens: int
    total_types: int
    total_lemas: int


class AnalyzedEpisode(BaseModel):
    episode_name: str
    episode_data_processed: Dict[str, LemmaEntry]
    stats: Optional[Stats] = None
    model_config = ConfigDict(extra="forbid")
