from domain.nlp.content.srt_adapter import SRTAdapter
from domain.nlp.lang.sv.lang_adapter import SVLangAdapter
from pipelines.analysis_pipeline import process_episode


def test_process_episode():
    file = "tests/unit/analysis/ep1.srt"
    with open(file, "rb") as f:
        episode = f.read()

    import json

    result_json = process_episode(
        episode, SRTAdapter(), SVLangAdapter(), episode_name="ep1"
    )
    result = json.loads(result_json)
    print(result)
    assert result["episode_name"] == "ep1"
    assert len(result["episode_data_processed"]) > 0
