import ast
import json
from unittest.mock import MagicMock

from common.schemas import BuildDeckRequest
from core.ports import DeckIO
from domain.nlp.lexicon.schema import AnalyzedEpisode
from domain.translator.translation import _tag_first
from domain.translator.translator import Translator
from pipelines.deck_pipeline import get_preview_stats, run_deck_pipeline


def test_deck_pipeline():
    # Setup inputs
    srt_path = "tests/integ/data_preview.txt"

    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    raw_json_str = ast.literal_eval(srt_content)
    loaded_analysis = json.loads(raw_json_str)

    from tests.integ.example_request import request

    episode_data = AnalyzedEpisode(episode_name="BonusFam", **loaded_analysis)
    build_request = BuildDeckRequest(**request)

    translator = MagicMock(spec=Translator)
    deck_io = MagicMock(spec=DeckIO)

    translator.translate.return_value = _tag_first("translated", "translated")
    deck_io.get_cached.return_value = {}

    result = run_deck_pipeline(episode_data, build_request, translator, deck_io)
    print(result)
    deck_io.save_deck.assert_called_once()
    deck_io.save_cards.assert_called_once()
    assert result["achieved_coverage"] > 0
    assert result["stopped_reason"] == "exhausted"
    assert result["picked_count"] > 0


def test_preview_stats():
    srt_path = "tests/integ/data_preview.txt"

    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    from tests.integ.example_request import request

    raw_json_str = ast.literal_eval(srt_content)
    loaded_analysis = json.loads(raw_json_str)

    episode_data = AnalyzedEpisode(episode_name="BonusFam", **loaded_analysis)
    build_request = BuildDeckRequest(**request)

    result = get_preview_stats(episode_data, build_request)
    assert result["achieved_coverage"] > 0
