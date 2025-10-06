from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import regex as re
from nlp.content.content_adapter import SentenceRec

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

@dataclass
class NLPToken:
    form: str                     # surface, lowercased
    lemma: str                    # lemma (or same as form)
    pos: Optional[str] = None     # UPOS/XPOS
    feats: Dict[str, Any] = None  # language-specific: {"artikel":"en", "gender":"utrum", ...}


class LangAdapter(ABC):
    code: str

    #--------------------- 1) NLP -------------------
    @abstractmethod    
    def tokenize(self, words_clean) -> List[NLPToken]:
        """
        It will take words and do smth like nlp = stanza.Pipeline("sv", processors="tokenize,pos,lemma") and 
        then build NLPToken objects from it.
        Key: Cleaned word
        Value: nlp(word)
        """
        raise NotImplementedError
    
    #------------------- 2) Lexicon -------------------
    @abstractmethod    
    def build_dictionary_from_tokens(self, tokens: list[NLPToken]) -> Dict[str, Dict[str, Any]]:
        """
        It will build dict with surface word and values depending on language.
        Returned: lexicon.
        """
        raise NotImplementedError

    @staticmethod
    def attach_examples(sentences: SentenceRec, lexicon:Dict[str, Dict[str, Any]] ) -> Dict[str, Dict[str, Any]]:
        ''' 
        Per inflected word get all sentences where it was used.
        {Lemma {
        Inflected1: [],
        Inflected2: []
        }}
        '''
        # We know what sentence is and what required in lexicon
        # I can code it actually
        return
    
if __name__ == '__main__':

    sentences = [
                'Och andas ut.',
                'Jag andas in lite också, om det är okej.',
                'Ge mig en enda anledning att leka.',
                'Fanny och Alexander!'
                'Så det blir jobbigt för andra.',
                'Andra veckan är det familjeliv.'
    ]
                                                             
    # IDEA
    '''
    1. Files adapter are language independent
    1.3 If file_adapter needs to process data differently than defualt it tries to get hook from langadapter
    1.5 Adapter passes processed data to Lang
    2. Lang adapter handles data analyzing
    3. After the data is processed based on parameters chosen by user a desk is generated
    4. Deck generation both language specific and agnostic depending on function
    '''


    #https://chatgpt.com/c/68e29c16-1928-832b-a5ab-4ba1e515d010