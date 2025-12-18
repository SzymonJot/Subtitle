import logging
import os

import deepl
from dotenv import load_dotenv

load_dotenv()
TRANS_VERSION = "DEEPL:2025-09"
DEEPL_AUTH_KEY = os.getenv("DEEPL_AUTH_KEY")


class Translator:
    def __init__(self):
        self.translator = deepl.Translator(DEEPL_AUTH_KEY)

    def translate(self, text: str, target_lang: str, source_lang: str) -> str:
        logging.info(text, target_lang, source_lang)
        result = self.translator.translate_text(
            text,
            target_lang=target_lang,
            source_lang=source_lang,
            tag_handling="xml",
            # outline_detection=True,
            splitting_tags=["i"],
        )

        return result.text


if __name__ == "__main__":
    translator = Translator()
    print(translator.translate("Daniel? <> <i>Är</i> bomben stor?", "EN-GB", "sv"))
