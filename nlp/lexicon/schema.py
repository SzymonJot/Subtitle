# pip install pydantic>=2
from typing import Dict, List, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict


class LemmaBase(BaseModel):
    POS: str
    Forms: List[str]
    examples: Dict[str, List[str]]
    model_config = ConfigDict(extra="forbid")

class LemmaSV(LemmaBase):
    lang: Literal["sv"]
    Artikel: Optional[Literal["en", "ett"]] = None
    Gender: Optional[Literal["Com", "Neut"]] = None
    Definite: Optional[Literal["Ind", "Def"]] = None


LemmaEntry = Union[LemmaSV] 

class EpisodeDataProcessed(BaseModel):
    episode_data_processed: Dict[str, LemmaEntry]
    model_config = ConfigDict(extra="forbid")
