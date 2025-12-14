import logging
from typing import Dict, List

import stanza

from domain.nlp.lang.lang_adapter import LangAdapter, NLPToken
from domain.nlp.lang.sv.sv_not_translatable import SV_NOT_TRANSLATABLE
from domain.nlp.lexicon.schema import LemmaSV


class SVLangAdapter(LangAdapter):
    def __init__(self):
        self.nlp = stanza.Pipeline(
            "sv", processors="tokenize,pos,lemma", tokenize_pretokenized=True
        )

    def tokenize(self, words_clean: List[str]) -> List[NLPToken]:
        # Implement Swedish-specific tokenization logic here
        words_clean = list(set(words_clean))  # get unique
        doc = self.nlp([[w] for w in words_clean])
        tokens = []
        for sentence in doc.sentences:
            for token in sentence.words:
                art = None
                # Derive article
                if token.upos == "NOUN":
                    feats = token.feats or ""
                    art = (
                        "en"
                        if "Gender=Com" in feats
                        else ("ett" if "Gender=Neut" in feats else None)
                    )
                # Append token
                tokens.append(
                    NLPToken(
                        form=token.text,
                        lemma=token.lemma,
                        pos=token.upos,
                        other={"artikel": art},
                    )
                )
        logging.info(f"Tokenized {len(words_clean)} word to {len(tokens)} tokens.")
        return tokens

    def build_dictionary_from_tokens(
        self,
        tokens: list[NLPToken],
        words_counted: Dict[str, int],
        not_translatable: list[str] = SV_NOT_TRANSLATABLE,
    ) -> Dict[str, LemmaSV]:
        # Implement Swedish-specific dictionary building logic here
        # Example: Group tokens by lemma and aggregate forms and features
        test = 0
        lexicon = {}
        for token in tokens:
            if token.lemma not in lexicon:
                lexicon[token.lemma] = LemmaSV(
                    pos=token.pos,
                    forms=[],
                    examples={},
                    artikel=token.other.get("artikel") if token.other else None,
                    forms_freq={},
                    lang="sv",
                    to_learn=token.lemma not in not_translatable,
                )

            lexicon[token.lemma].forms.append(token.form)

            lexicon[token.lemma].forms_freq[token.form] = words_counted.get(
                token.form, 0
            )

            # REVIEW THIS,
            lexicon[token.lemma].forms_cov[token.form] = (
                words_counted.get(token.form, 0) / sum(words_counted.values())
                if sum(words_counted.values()) > 0
                else 0.0
            )
            test += words_counted.get(token.form, 0)
            lexicon[token.lemma].forms = list(
                set(lexicon[token.lemma].forms)
            )  # Ensure unique forms

        return lexicon


if __name__ == "__main__":
    pass
