def get_art(word):
    doc = nlp(word)
    for sent in doc.sentences:
       for w in sent.words:
           if w.upos == "NOUN":
               feats = w.feats or ""          # e.g. "Definite=Ind|Gender=Neut|Number=Sing"
               art = "en" if "Gender=Com" in feats else ("ett" if "Gender=Neut" in feats else None)
               return art
           
    return None
