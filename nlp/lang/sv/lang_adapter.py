from nlp.lang.lang_adapter import LangAdapter, NLPToken
from nlp.lexicon.schema import LemmaSV, LemmaBase
from typing import List, Dict
import stanza
import logging

logging.basicConfig(level=logging.INFO)

class sv_lang_adapter(LangAdapter):

    def __init__(self):
        self.nlp = stanza.Pipeline("sv", processors="tokenize,pos,lemma")

    def tokenize(self, words_clean: List[str]) -> List[NLPToken]:
        # Implement Swedish-specific tokenization logic here
        words_clean = list(set(words_clean))  # get unique
        tokens = []
        for word in words_clean:
            doc = self.nlp(word)
            for sentence in doc.sentences:
                for token in sentence.words:
                    art = None
                    # Derive article
                    if token.upos == "NOUN":
                        feats = token.feats or ""  
                        art = "en" if "Gender=Com" in feats else ("ett" if "Gender=Neut" in feats else None)
                    # Append token
                    tokens.append(NLPToken(
                                    form=token.text, 
                                    lemma=token.lemma, 
                                    pos=token.upos,
                                    other = {'artikel': art}))
        logging.info(f"Tokenized {len(words_clean)} word to {len(tokens)} tokens.")
        return tokens
    

    def build_dictionary_from_tokens(self, tokens: list[NLPToken], words_counted: Dict[str,int]) -> Dict[str, LemmaSV]:
        
        # Implement Swedish-specific dictionary building logic here
        # Example: Group tokens by lemma and aggregate forms and features
        lexicon = {}
        for token in tokens:
            if token.lemma not in lexicon:
                lexicon[token.lemma] = LemmaSV(
                    pos=token.pos,
                    forms=[],
                    examples={},
                    artikel=token.other.get('artikel') if token.other else None,
                    forms_freq={},
                    lang="sv"
                )

            lexicon[token.lemma].forms.append(token.form)

            lexicon[token.lemma].forms_freq[token.form] = words_counted.get(token.form, 0)

            lexicon[token.lemma].forms_cov[token.form] = words_counted.get(token.form, 0) / sum(words_counted.values()) if sum(words_counted.values()) > 0 else 0.0

            lexicon[token.lemma].forms = list(set(lexicon[token.lemma].forms))  # Ensure unique forms
        logging.info(f"Built lexicon with {len(lexicon)} lemmas from {len(tokens)} tokens.")
        return lexicon



if __name__ == '__main__':
    adapter = sv_lang_adapter()
    tokens = adapter.tokenize(["Fanny", "är", "en", "bra", "lärare"])
    print(tokens)
    dictionary = adapter.build_dictionary_from_tokens(tokens)
    print(dictionary)
    # EXAMPLE WORKFLOW
    #  sentences: List[SentenceRec] from ContentAdapter layers
    #  1) Pre-clean
    # ent_map = adapter.clean_for_sentences(file, content_adapter)  # Dict[tuple(tokens), original_sentence]
    # ords_clean = adapter.clean_for_words(file, content_adapter)   # List[str]
    # 
    #  2) NLP
    # oken_recs = adapter.tokenize(words_clean)        # List[NLPTokenkenRec]
    # emmas_info = adapter.build_dictionary_from_tokens(token_recs)   # {"Forms_by_Lemma": {...}}
    # uilt_dic =  adapter.get_sentence_example(cleaned_senteces, lemmas_info)

