import os

import deepl
from dotenv import load_dotenv

load_dotenv()
TRANS_VERSION = "DEEPL:2025-09"
DEEPL_AUTH_KEY = os.getenv("DEEPL_AUTH_KEY")


class Translator:
    def __init__(self):
        self.translator = deepl.Translator(DEEPL_AUTH_KEY)

    def translate(
        self, text: list[str], target_lang: str, source_lang: str
    ) -> list[str]:
        result = self.translator.translate_text(
            text,
            target_lang=target_lang,
            source_lang=source_lang,
            tag_handling="xml",
            # outline_detection=True,
        )

        if isinstance(result, list):
            return [r.text for r in result]
        else:
            return [result.text]


if __name__ == "__main__":
    translator = Translator()
    to_translate = [
        "Jag är på väg dit nu. Sagajag tror att hon har barn, så var <i>lite</i> försiktig"
    ]
    res = translator.translate(to_translate, "EN-GB", "sv")
    print(res)

# -Gestern, als ich das Abendessen zubereitet habe.
