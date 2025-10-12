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
    

    def build_dictionary_from_tokens(self, tokens: List[NLPToken]) -> Dict[str, LemmaSV]:
        """
        Build a Swedish lexicon where:
          - forms_freq: per-lemma, per-form counts (from these tokens)
          - forms_cov: per-lemma, per-form coverage share using ONE shared denominator
                       (sum over all lemmas & forms ≈ 1.0)
        Assumes each token has: lemma (str), form (str), pos (str), and optional other: dict.
        """
        lexicon: Dict[str, LemmaSV] = {}
        total_tokens_in_pool = 0  # denominator shared across all entries

        # 1) Count per-lemma/per-form directly from tokens (no global form table)
        for tok in tokens:
            total_tokens_in_pool += 1
            lemma = tok.lemma
            form = tok.form

            if lemma not in lexicon:
                lexicon[lemma] = LemmaSV(
                    pos=tok.pos,
                    forms=[],
                    examples={},                # fill elsewhere if you have examples
                    lang="sv",
                    artikel=(tok.other.get("artikel") if getattr(tok, "other", None) else None),
                    gender=(tok.other.get("gender") if getattr(tok, "other", None) else None),
                    definite=(tok.other.get("definite") if getattr(tok, "other", None) else None),
                )

            entry = lexicon[lemma]
            entry.forms.append(form)
            entry.forms_freq[form] = entry.forms_freq.get(form, 0) + 1

        # 2) Finalize: dedupe forms; compute per-form coverage with the SAME denominator
        if total_tokens_in_pool == 0:
            return lexicon  # empty input → empty cov

        for lemma, entry in lexicon.items():
            # unique forms on output
            entry.forms = list(set(entry.forms))
            # per-form coverage share (each token contributes exactly once overall)
            entry.forms_cov = {
                f: cnt / total_tokens_in_pool
                for f, cnt in entry.forms_freq.items()
            }

        # Optional sanity: pool coverage should sum ≈ 1.0
        # total_cov = sum(sum(e.forms_cov.values()) for e in lexicon.values())
        # assert 0.99 <= total_cov <= 1.01, f"Pool coverage sum is {total_cov:.6f}, expected ~1.0"

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

