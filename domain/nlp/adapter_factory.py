from domain.nlp.content.content_adapter import ContentAdapter
from domain.nlp.content.srt_adapter import SRTAdapter
from domain.nlp.lang.lang_adapter import LangAdapter
from domain.nlp.lang.sv.sv_lang_adapter import SVLangAdapter


class AdapterFactory:
    @staticmethod
    def create_content_adapter(file_type: str) -> ContentAdapter:
        if file_type == "srt":
            return SRTAdapter()
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def create_lang_adapter(language: str) -> LangAdapter:
        if language == "sv":
            return SVLangAdapter()
        else:
            raise ValueError(f"Unsupported language: {language}")
