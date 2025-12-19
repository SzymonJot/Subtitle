import ast
import json

from common.schemas import BuildDeckRequest
from domain.nlp.lexicon.schema import AnalyzedEpisode
from domain.translator.translator import Translator
from infra.supabase.deck_repo import SBDeckIO
from pipelines.deck_pipeline import deck_pipeline


def test_deck_pipeline():
    # Setup inputs
    srt_path = "tests/integ/data_preview.txt"

    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    raw_json_str = ast.literal_eval(srt_content)
    loaded_analysis = json.loads(raw_json_str)
    loaded_analysis["episode_name"] = "BonusFam"

    from tests.integ.example_request import request

    episode_data = AnalyzedEpisode(**loaded_analysis)
    episode_data.episode_data_processed = dict(
        list(episode_data.episode_data_processed.items())[:10]
    )
    build_request = BuildDeckRequest(**request)

    translator = Translator()
    deck_io = SBDeckIO()
    deck_io.sb.table("jobs").upsert(
        {
            "status": "succeeded",
            "input_path": "dummy",
            "id": "c0ffee12-3456-789a-bcde-0123456789ab",
        },
        on_conflict="id",
        ignore_duplicates=True,
    ).execute()

    result = deck_pipeline(episode_data, build_request, translator, deck_io)
    print(result)
    deck_id = result["deck_id"]

    saved_decks = deck_io.sb.table("decks").select("*").eq("id", deck_id).execute()
    saved_cards = deck_io.sb.table("cards").select("*").eq("deck_id", deck_id).execute()

    print(result)
    print(saved_cards)

    assert len(saved_cards.data) > 0
    assert len(saved_decks.data) > 0
    assert result["achieved_coverage"] > 0
    assert result["stopped_reason"] == "exhausted"
    assert result["picked_count"] > 0
