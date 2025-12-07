from pydantic import BaseModel

class Candidate(BaseModel):
    lemma: str
    pos: str
    forms: list[str]
    freq: int
    cov_share: float        
    example: dict

class RankedCandidate(BaseModel):
    lemma: str
    pos: str
    forms: list[str]
    freq: int
    cov_share: float
    score: float
    example: dict
    form_original_lang: str
    sentence_original_lang: str
    translated_word: str
    translated_example: str