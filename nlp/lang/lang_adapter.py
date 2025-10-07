from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import regex as re
from nlp.lexicon.schema import SentenceRec
from nlp.lexicon.schema import LemmaBase, NLPToken

'''
{
  "<lemma>": {
    "pos": "NOUN|ADJ|VERB|...",
    "forms": ["<form1>", "<form2>", "..."],               
    "examples": { "<form>": ["sent1", "sent2", "..."] },  
    "feats": { "Gegendernder": "Com|Neut", "definite": "Ind|Def" }
  }
}
'''

class LangAdapter(ABC):
    code: str

    #--------------------- 1) NLP -------------------
    @abstractmethod    
    def tokenize(self, words_clean: List[str]) -> List[NLPToken]:
        """
        It will take words and do smth like nlp = stanza.Pipeline("sv", processors="tokenize,pos,lemma") and 
        then build NLPToken objects from it.
        Key: Cleaned wordSo 
        Value: nlp(word)
        """
        raise NotImplementedError
    
    #------------------- 2) Lexicon -------------------
    @abstractmethod    
    def build_dictionary_from_tokens(self, tokens: list[NLPToken]) -> Dict[str, LemmaBase]:
        """
        It will build dict with surface word and values depending on language.
        Returned: lexicon.
        """
        raise NotImplementedError
    
    @staticmethod
    def attach_examples(sentences: List[SentenceRec], lexicon:Dict[str, LemmaBase] ) -> Dict[str, LemmaBase]:
        """
        Associates example sentences with each inflected word found in the given sentences.
        Args:
            sentences (SentenceRec): Iterable of sentence objects containing text.
            lexicon (Dict[str, LemmaBase]): Dictionary mapping inflected words to their lemma data.
        Returns:
            Dict[str, LemmaBase]: Updated lexicon with example sentences attached to each inflected word.
        """

        for sentence in sentences:
            words = re.findall(r'\w+', sentence.text)
            for word in words:
                word_lower = word.lower()
                for lemma, lemma_data in lexicon.items():
                    lower_forms_set = {form.lower() for form in lemma_data.forms}
                    if word_lower in lower_forms_set:
                        lemma_data.examples.setdefault(word, []).append(sentence.text)
    
    @staticmethod
    def finalize_lexicon(lexicon:Dict[str, LemmaBase]) -> Dict[str, LemmaBase]:
        """
        Finalizes the lexicon by ensuring json seriability.
        Args:
            lexicon (Dict[str, LemmaBase]): Dictionary mapping inflected words to their lemma data.
        """
    
        return {k: v.model_dump() for k, v in lexicon.items()}

if __name__ == '__main__':

    class DummyLangAdapter(LangAdapter):
        def tokenize(self, words_clean: List[str]) -> List[NLPToken]:
            # Dummy implementation
            return []

        def build_dictionary_from_tokens(self, tokens: list[NLPToken]) -> Dict[str, LemmaBase]:
            # Dummy implementation
            return {}

    sentences = [
                SentenceRec('Fanny och Alexander', {}),
                SentenceRec('Så det blir jobbigt för andra och Fanny.', {}),
                SentenceRec('Andra veckan är det familjeliv.', {})
    ]

    words = [
        'Fanny', 'och', 'Alexander', 'Så', 'det', 'blir', 'jobbigt', 'för', 'andra', 
        'Andra', 'veckan', 'är', 'det', 'familjeliv'
    ]

    lexicon = {
        "fanny": LemmaBase(
            pos="NOUN",
            forms=["Fanny"],
            examples={}
        ),
        "alexander": LemmaBase(
            pos="NOUN",
            forms=["Alexander"],
            examples={}
        ),
        "andra": LemmaBase(
            pos="PRON",
            forms=["andra", "Andra"],
            examples={}
        ),
        "familjeliv": LemmaBase(
            pos="NOUN",
            forms=["familjeliv"],
            examples={}
        )
    }

    lang_adapter = DummyLangAdapter()
    lang_adapter.attach_examples(sentences,lexicon)
    print(lexicon)

                                                             
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