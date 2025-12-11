import os
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.datastructures import UploadFile

from common.constants import BUCKET_UPLOADS, EXT_SRT, STATUS_QUEUED, TABLE_JOBS
from common.schemas import BuildDeckRequest
from common.supabase_client import get_client
from infra.supabase.jobs_repo import SBJobsIO
from worker.worker import run_job

router = APIRouter()

sb = get_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
sb_jobs_io = SBJobsIO(sb)


@router.post("/jobs", status_code=201)
async def create_job(file: UploadFile):
    if not file.filename.lower().endswith(EXT_SRT):
        raise HTTPException(status_code=400, detail=f"Only {EXT_SRT} files")

    job_id = str(uuid.uuid4())
    raw = await file.read()

    in_path = f"{BUCKET_UPLOADS}/{job_id}"
    jobs_table = TABLE_JOBS

    sb_jobs_io.upload_file(bucket_name=BUCKET_UPLOADS, file=raw, name=job_id)
    sb_jobs_io.insert_job(
        job_id=job_id,
        in_path=in_path,
        jobs_table=jobs_table,
        status=STATUS_QUEUED,
        params={"file_type": "srt", "language": "sv"},
    )

    # Background tasks will be triggered.
    run_job(job_id)
    return {"job_id": job_id}


# Get processed episode
@router.get("/jobs/{job_id}/analysis")
def get_job_analysis(job_id: str):
    return sb_jobs_io.download_analysis(job_id)


@router.get("/jobs/{job_id}/preview")
def get_preview(job_id: str, request: BuildDeckRequest):
    # GET processed episode
    return


@router.post("/jobs/{job_id}/deck")
def get_deck(request: BuildDeckRequest, job_id: str):
    # Placeholder for deck generation logic
    return {"status": "processing", "job_id": job_id, "request": request.dict()}


@router.get("/jobs")
def get_job(job_id: str):
    return sb_jobs_io.get_job(job_id)
