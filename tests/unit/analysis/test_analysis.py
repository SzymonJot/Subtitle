from pprint import pprint

from domain.nlp.content.srt_adapter import SRTAdapter
from domain.nlp.lang.sv.sv_lang_adapter import SVLangAdapter
from domain.nlp.run_episode_analysis import process_episode


def test_process_episode():
    file = "tests/unit/analysis/ep1.srt"
    with open(file, "rb") as f:
        episode = f.read()

    analyzed_episode = process_episode(
        episode, SRTAdapter(), SVLangAdapter(), episode_name="ep1"
    )
    result = analyzed_episode.model_dump()
    pprint(result)
    assert result["episode_name"] == "ep1"
    assert len(result["episode_data_processed"]) > 0
