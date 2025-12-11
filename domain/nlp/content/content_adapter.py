from abc import ABC, abstractmethod
from typing import Any, List

from domain.nlp.lexicon.schema import SentenceRec

# Sentence unit from content adapter


class ContentAdapter(ABC):
    @abstractmethod
    def clean_for_sentence(self, file: Any) -> List[SentenceRec]:
        """
        Transform list of sentences to tokenized words adapter
        """
        raise NotImplementedError

    @abstractmethod
    def clean_for_words(self, sentences: List[SentenceRec]) -> List[str]:
        """
        Transform list of sentences to tokenized words adapter
        """
        raise NotImplementedError
