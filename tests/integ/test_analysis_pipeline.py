import uuid

from common.constants import BUCKET_UPLOADS
from infra.supabase.jobs_repo import SBJobsIO
from pipelines.analysis_pipeline import run_analysis_pipeline


def test_analysis_pipeline():
    id = uuid.uuid4()
    sb_jobs_io = SBJobsIO()
    sb_jobs_io.sb.table("jobs").upsert(
        {
            "status": "running",
            "input_path": f"{BUCKET_UPLOADS}/{id}",
            "id": str(id),
            "params": {"file_type": "srt", "language": "sv", "episode_name": "ep1"},
        },
        on_conflict="id",
        ignore_duplicates=True,
    ).execute()
    with open("tests/integ/ep1.srt", "rb") as f:
        file_to_process = f.read()

    sb_jobs_io.sb.storage.from_(BUCKET_UPLOADS).upload(
        str(id),
        file_to_process,
    )
    stats = run_analysis_pipeline(str(id))
    assert stats.total_tokens > 0
