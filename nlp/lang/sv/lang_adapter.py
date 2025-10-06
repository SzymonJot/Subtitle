from nlp.lang.lang_adapter import LangAdapter

class sv_lang_adapter(LangAdapter):
    pass



if __name__ == '__main__':
    # EXAMPLE WORKFLOW
     sentences: List[SentenceRec] from ContentAdapter layers
     1) Pre-clean
    ent_map = adapter.clean_for_sentences(file, content_adapter)  # Dict[tuple(tokens), original_sentence]
    ords_clean = adapter.clean_for_words(file, content_adapter)   # List[str]
    
     2) NLP
    oken_recs = adapter.tokenize(words_clean)        # List[NLPTokenkenRec]
    emmas_info = adapter.build_dictionary_from_tokens(token_recs)   # {"Forms_by_Lemma": {...}}
    uilt_dic =  adapter.get_sentence_example(cleaned_senteces, lemmas_info)

