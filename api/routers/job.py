import uuid

from fastapi import APIRouter, HTTPException
from fastapi.datastructures import UploadFile

from common.constants import EXT_SRT
from common.schemas import BuildDeckRequest
from infra.supabase.jobs_repo import SBJobsIO
from pipelines.analysis_pipeline import register_job

router = APIRouter()


sb_jobs_io = SBJobsIO()


@router.post("/jobs", status_code=201)
async def create_job(file: UploadFile):
    if not file.filename.lower().endswith(EXT_SRT):
        raise HTTPException(status_code=400, detail=f"Only {EXT_SRT} files")

    job_id = str(uuid.uuid4())
    raw = await file.read()

    # Background tasks will be triggered.
    register_job(job_id, raw)
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
