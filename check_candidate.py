from domain.deck.schemas.schema import Candidate

try:
    c = Candidate(lemma="foo", pos="VERB", forms=[], freq=1, cov_share=0.1)
    print("Created candidate")
    try:
        val = c["lemma"]
        print("Item access worked")
    except TypeError as e:
        print(f"Item access failed: {e}")
    except Exception as e:
        print(f"Item access failed with {type(e)}: {e}")

    try:
        c.lemma
        print("Attribute access worked")
    except Exception as e:
        print(f"Attribute access failed: {e}")

except Exception as e:
    print(f"Failed to create candidate: {e}")
