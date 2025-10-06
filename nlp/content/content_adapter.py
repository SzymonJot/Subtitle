from dataclasses import dataclass
from typing import Dict, Any, List
# Sentence unit from content adapter
@dataclass
class SentenceRec:
    text: str
    meta: Dict[str, Any]  # {"start":12.34,"end":15.67,"speaker":"A","source_id":"..."} safe primitives only


class ContentAdapter:

    @staticmethod
    def clean_for_words(self, sentences: List[str]) -> List[str]:
        """
        Transform list of sentences to tokenized words adapter
        """
        words = []
        for sentence in sentences:
            sentence.split('')

        #Extract words from sentences which is passed here from s
        
        return words
    