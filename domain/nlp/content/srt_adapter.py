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
    (?<!\b(?:dr|prof|mr|mrs|ms|st|jr|sr|e\.g|i\.e|no|np|tj|kap|art|al)\.) # Abbreviations
    (?<=\.|!|\?)                                                          # Split after . ! ?
    \s+                                                                   # Followed by whitespace
    (?=[A-Z0-9"'-]|\p{Lu})                                                # Lookahead: Next char is usually Upper or Value or Dash
    """,
        re.IGNORECASE | re.VERBOSE,
    )

    def _clean_line(self, text):
        text = re.sub(r"<[^>]+>", "", text)

        # 2. Remove leading dashes used for dialogue (e.g. "- Hello")
        # This preserves hyphens in words like "semi-detached"
        text = re.sub(r"^\s*-\s+", "", text)  # Dash followed by space
        text = re.sub(r"^\s*-\s*", "", text)  # strict start dash
        return text

    def _split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in self._SENT_END_RE.split(text) if s.strip()]

    def _read_file(self, srt_file: Any) -> str:
        """
        Reads an SRT file and extracts the text content from it.
        Args:
            srt_file (Any): The SRT file to read.
        """
        return srt_file.decode("utf-8")

    def _parse_srt_blocks(self, content: str) -> list[str]:
        """
        Identify content blocks inbetween time lines.
        """
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        blocks = re.split(r"\n\s*\n", content)

        text_lines = []
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]

            arrow_line = -1
            for i, line in enumerate(lines):
                if "-->" in line:
                    arrow_line = i

            if arrow_line != -1 and arrow_line + 1 < len(lines):
                data_content = lines[arrow_line + 1 :]

            text_lines.extend(data_content)

        return text_lines

    def clean_for_sentence(self, srt_file: Any) -> List[SentenceRec]:
        """
        Transform list of sentences to tokenized words adapter
        """
        file_content = self._read_file(srt_file)

        lines = self._parse_srt_blocks(file_content)
        lines = [self._clean_line(line) for line in lines]

        text = " ".join(lines)

        # 2) Split by sentences (not lines)
        sentences = self._split_sentences(text)

        # 3) Clean and filter
        cleaned_sentences = []
        for s in sentences:
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
    from pprint import pprint

    adapter = SRTAdapter()
    # Provide the path to a sample SRT file
    srt_path = "A.Good.Man.in.Africa.1994.1080p.AMZN.WEBRip.DDP2.0.x264-monkee.sv.srt"
    with open(srt_path, "rb") as f:
        file = f.read()

    res = adapter.clean_for_sentence(srt_file=file)
    pprint(res)
    text = "Allt tycks leda till honom. Även stackars Innocens."
    print(repr(text))
    tt = adapter._split_sentences(text)
    pprint(tt)
