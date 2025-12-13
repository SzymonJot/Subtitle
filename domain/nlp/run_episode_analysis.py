import logging
import time

from domain.nlp.content.content_adapter import ContentAdapter
from domain.nlp.lang.lang_adapter import LangAdapter
from domain.nlp.lexicon.schema import AnalyzedEpisode, Stats

logger = logging.getLogger(__name__)


def _t():
    return time.perf_counter()


def process_episode(
    file_bytes, adapter: ContentAdapter, lang_adapter: LangAdapter, episode_name: str
) -> AnalyzedEpisode:
    t0 = _t()

    # 1) sentences
    sentences = adapter.clean_for_sentence(file_bytes)
    logging.info("Cleaned to %d sentences (%.3fs)", len(sentences), _t() - t0)

    # 2) words
    t1 = _t()
    words = adapter.clean_for_words(sentences)
    logging.info("Cleaned to %d words (%.3fs)", len(words), _t() - t1)

    # 2.5) get words count
    words_counted = lang_adapter.count_words(words)
    logging.info("Counted to %d unique words (%.3fs)", len(words_counted), _t() - t1)

    # 3) tokenize
    t2 = _t()
    tokens = lang_adapter.tokenize(words)
    logging.info("Tokenized to %d tokens (%.3fs)", len(tokens), _t() - t2)

    # 4) lemmas
    t3 = _t()
    lexicon = lang_adapter.build_dictionary_from_tokens(tokens, words_counted)
    logging.info("Built lexicon with %d lemmas (%.3fs)", len(lexicon), _t() - t3)

    # 5) examples (cap per lemma inside the method)
    t4 = _t()
    lang_adapter.attach_examples(sentences, lexicon)
    logging.info("Attached examples (%.3fs)", _t() - t4)

    # 6) finalize
    t5 = _t()

    analyzed_episode = AnalyzedEpisode(
        episode_name=episode_name,
        episode_data_processed=lexicon,
        stats=Stats(
            total_tokens=sum(words_counted.values()),
            total_types=len(words_counted),
            total_lemas=len(lexicon),
        ),
    )

    logging.info("Finalized lexicon (%.3fs). Total: %.3fs", _t() - t5, _t() - t0)

    return analyzed_episode


if __name__ == "__main__":
    pass
