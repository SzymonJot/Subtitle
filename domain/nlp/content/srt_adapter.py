from typing import Any, List

import regex as re

from domain.nlp.content.content_adapter import ContentAdapter
from domain.nlp.lexicon.schema import SentenceRec


class SRTAdapter(ContentAdapter):
    _SRT_TIME_RE = re.compile(
        r"^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}$"
    )
    _SENT_END_RE = re.compile(
        r"""
        (?<!\b(?:dr|prof|mr|mrs|ms|nr|itp|np|tj|kap|art|al)\.)   # variable-width lookbehind OK here
        (?<=\.|!|\?|…)
        ["')\]]*
        \s+
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def _clean_line(self, line):
        line = line.replace("<", " ")
        line = line.replace(">", " ")
        line = line.replace("-", "")
        line = line.replace("...", "")
        line = line.strip()

        if line.endswith(","):
            line = line[:-1]

        line = line.replace("  ", " ")
        line = line.strip()
        return line

    def _split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in self._SENT_END_RE.split(text) if s.strip()]

    def _read_file(self, srt_file: Any) -> str:
        """
        Reads an SRT file and extracts the text content from it.
        Args:
            srt_file (Any): The SRT file to read.
        """

        return srt_file.decode("utf-8")

    def clean_for_sentence(self, srt_file: Any) -> List[SentenceRec]:
        """
        Transform list of sentences to tokenized words adapter
        """
        file_content = self._read_file(srt_file)
        lines = []
        for raw in file_content.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.isdigit():
                continue
            if self._SRT_TIME_RE.match(line):
                continue

            lines.append(line)

        text = " ".join(lines)

        # 2) Split by sentences (not lines)
        sentences = self._split_sentences(text)

        # 3) Clean and filter
        cleaned_sentences = []
        for s in sentences:
            s = self._clean_line(s)  # your cleaner
            s = " ".join(s.split())
            if len(s) > 1:
                cleaned_sentences.append(SentenceRec(text=s, meta={}))

        return cleaned_sentences

    def clean_for_words(self, sentences: List[SentenceRec]) -> List[str]:
        """
        Transform list of sentences to tokenized words adapter
        """
        cleaned_sentences = []
        for line in sentences:
            sentence = line.text
            # Remove punctuation and special characters using regex
            sentence = re.sub(r"\p{P}+", " ", sentence)
            sentence = sentence.lower()
            sentence = sentence.strip()
            for word in sentence.split():
                if (
                    word and word.isalpha()
                ):  # Ensure the word is not empty and contains only alphabetic characters
                    cleaned_sentences.append(word)

        return cleaned_sentences


if __name__ == "__main__":
    adapter = SRTAdapter()
    # Provide the path to a sample SRT file
    srt_path = "test\ep1.srt"
    sentences = adapter.clean_for_sentence(srt_path)
    words = adapter.clean_for_words(sentences)
    for s in sentences:
        print(s)

    print(words)
