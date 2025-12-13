import logging
import traceback

from common.constants import (
    BUCKET_RESULTS,
    BUCKET_UPLOADS,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    TABLE_JOBS,
)
from domain.nlp.adapter_factory import AdapterFactory
from domain.nlp.run_episode_analysis import process_episode
from infra.supabase.jobs_repo import SBJobsIO


def register_job(job_id: str, file: bytes, episode_name: str):
    logging.info(f"Registering job: {job_id}")
    in_path = f"{BUCKET_UPLOADS}/{job_id}"
    jobs_table = TABLE_JOBS
    sb_jobs_io = SBJobsIO()
    sb_jobs_io.upload_file(BUCKET_UPLOADS, file, job_id)
    sb_jobs_io.insert_job(
        job_id=job_id,
        in_path=in_path,
        jobs_table=jobs_table,
        status=STATUS_QUEUED,
        params={"file_type": "srt", "language": "sv", "episode_name": episode_name},
    )

    # job_queue.enqueue(run_analysis_pipeline, job_id)

    return job_id


def run_analysis_pipeline(job_id: str) -> dict:
    sb_jobs_io = SBJobsIO()
    try:
        # Get row from supabase for this job id
        row = sb_jobs_io.get_job(job_id)
        in_path = row["input_path"]
        # Fetch file
        file_to_process = sb_jobs_io.get_storage_file(in_path)
        # Get params
        params = row["params"]
        # Pass file to data pipeline
        logging.info(f"Processing job: {job_id}")
        sb_jobs_io.update_status(job_id, STATUS_RUNNING, 0)

        adapter = AdapterFactory.create_content_adapter(params["file_type"])
        lang_adapter = AdapterFactory.create_lang_adapter(params["language"])

        analyzed_episode = process_episode(
            file_to_process, adapter, lang_adapter, episode_name=params["episode_name"]
        )

        # Put it to bucket results
        results_encoded = analyzed_episode.model_dump_json().encode("utf-8")
        logging.info(f"Encoded results to {len(results_encoded)} bytes.")
        sb_jobs_io.upload_file(BUCKET_RESULTS, results_encoded, job_id)
        logging.info(f"Uploaded results to bucket {BUCKET_RESULTS}/{job_id}")
        # Put result path to jobs table
        output_path = f"{BUCKET_RESULTS}/{job_id}"
        logging.info(f"Output path: {output_path}")
        sb_jobs_io.update_value(TABLE_JOBS, job_id, {"output_path": output_path})
        logging.info(f"Updated jobs table with output path: {output_path}")
        # Set supabase to success
        sb_jobs_io.update_status(job_id, STATUS_SUCCEEDED, 100)
        logging.info(f"Updated status to succeeded for job: {job_id}")

    except Exception:
        sb_jobs_io.update_status(
            job_id, STATUS_FAILED, 0, error=traceback.format_exc()[:8000]
        )
        logging.error(f"Failed to process job: {job_id}")
        raise
    return analyzed_episode.stats
