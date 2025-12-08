# pip install pydantic>=2
from typing import Dict, List, Optional, Literal, Union, Any
from pydantic import BaseModel, Field, ConfigDict
from dataclasses import dataclass

'''
{
  "<lemma>": {
    "Artikel": "en|ett|null",
    "POS": "NOUN|ADJ|VERB|...",
    "Forms": ["<form1>", "<form2>", "..."],               
    "examples": { "<form>": ["sent1", "sent2", "..."] },  
    "feats": { "Gender": "Com|Neut", "Definite": "Ind|Def" }
  }
}
'''

class NLPToken(BaseModel):
    form: str                     # surface, lowercased
    lemma: str                    # lemma (or same as form)
    pos: Optional[str] = None     # UPOS/XPOS
    other: Dict[str, Any] = None  # language-specific: {"artikel":"en", "gender":"utrum", ...}

class SentenceRec(BaseModel):
    text: str
    meta: Dict[str, Any]  # {"start":12.34,"end":15.67,"speaker":"A","source_id":"..."} safe primitives only

class LemmaBase(BaseModel):
    pos: str
    forms: List[str]
    examples: Dict[str, List[str]]
    model_config = ConfigDict(extra="forbid")  
    forms_freq: Dict[str, int] = Field(default_factory=dict)  # per-form token counts
    forms_cov: Dict[str, float] = Field(default_factory=dict)   # per-form coverage share (0..1)


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
    episode_data_processed: Dict[str, LemmaEntry]
    stats: Optional[Stats] = None    # ← NEW optional
    model_config = ConfigDict(extra="forbid")