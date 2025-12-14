import logging

from fastapi import APIRouter, Form, HTTPException, Response
from fastapi.datastructures import UploadFile

from common.constants import EXT_SRT
from common.schemas import BuildDeckRequest, ExportDeckRequest, PreviewBuildDeckRequest
from infra.supabase.jobs_repo import SBJobsIO
from pipelines.analysis_pipeline import register_job, run_analysis_pipeline
from pipelines.deck_pipeline import run_deck_pipeline, run_preview
from pipelines.export_deck import run_export_deck

router = APIRouter()
sb_jobs_io = SBJobsIO()


@router.post("/jobs", status_code=201)
async def create_job(file: UploadFile, episode_name: str = Form(...)):
    if not file.filename.lower().endswith(EXT_SRT):
        raise HTTPException(status_code=400, detail=f"Only {EXT_SRT} files")

    raw = await file.read()
    logging.info(f"Received file: {file.filename}")
    job_id_res = register_job(raw, episode_name)
    logging.info(f"Registered job: {job_id_res}")
    return {"job_id": job_id_res}


# Get processed episode
@router.get("/jobs/{job_id}/analysis")
def get_job_analysis(job_id: str):
    return sb_jobs_io.download_analysis(job_id)


@router.post("/jobs/{job_id}/preview")
def get_preview(request: PreviewBuildDeckRequest):
    return run_preview(request)


@router.post("/jobs/{job_id}/deck")
def export_deck(request: ExportDeckRequest):
    return Response(
        content=run_export_deck(request),
        media_type="text/tab-separated-values; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="quizlet.tsv"'},
    )


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    return sb_jobs_io.get_job(job_id)


@router.post("/jobs/{job_id}/manual")
def manualy_process_job(job_id: str):
    stats = run_analysis_pipeline(job_id)
    return {"job_id": job_id, "stats": stats}


@router.post("/deck")
def create_deck(request: BuildDeckRequest):
    return run_deck_pipeline(request)
