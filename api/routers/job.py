import logging
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.datastructures import UploadFile

from common.constants import EXT_SRT
from common.schemas import BuildDeckRequest, ExportDeckRequest, PreviewBuildDeckRequest
from domain.nlp.lexicon.schema import AnalyzedEpisode
from domain.translator.translator import Translator
from infra.supabase.deck_repo import SBDeckIO
from infra.supabase.jobs_repo import SBJobsIO
from pipelines.analysis_pipeline import register_job, run_analysis_pipeline
from pipelines.deck_pipeline import get_preview_stats, run_deck_pipeline
from pipelines.export_deck import run_export_deck

router = APIRouter()
sb_jobs_io = SBJobsIO()


@router.post("/jobs", status_code=201)
async def create_job(file: UploadFile, episode_name: str):
    if not file.filename.lower().endswith(EXT_SRT):
        raise HTTPException(status_code=400, detail=f"Only {EXT_SRT} files")

    job_id = str(uuid.uuid4())
    raw = await file.read()
    logging.info(f"Received file: {file.filename}")
    # Background tasks will be triggered.
    job_id_res = register_job(job_id, raw, episode_name)
    logging.info(f"Registered job: {job_id_res}")
    return {"job_id": job_id_res}


# Get processed episode
@router.get("/jobs/{job_id}/analysis")
def get_job_analysis(job_id: str):
    return sb_jobs_io.download_analysis(job_id)


@router.post("/jobs/{job_id}/preview")
def get_preview(request: PreviewBuildDeckRequest):
    jobs_io = SBJobsIO()
    analyzed_episode = jobs_io.download_analysis(request.job_id)
    analyzed_episode = AnalyzedEpisode.model_validate_json(analyzed_episode)
    return get_preview_stats(analyzed_episode, request)


@router.post("/jobs/{job_id}/deck")
def export_deck(request: ExportDeckRequest):
    deck_io = SBDeckIO()
    return run_export_deck(request, deck_io)


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    return sb_jobs_io.get_job(job_id)


@router.post("/jobs/{job_id}/manual")
def manualy_process_job(job_id: str):
    stats = run_analysis_pipeline(job_id)
    return {"job_id": job_id, "stats": stats}


@router.post("/deck")
def create_deck(request: BuildDeckRequest):
    deck_io = SBDeckIO()
    translator = Translator()
    jobs_io = SBJobsIO()
    analyzed_episode = jobs_io.download_analysis(request.job_id)
    analyzed_episode = AnalyzedEpisode.model_validate_json(analyzed_episode)
    return run_deck_pipeline(analyzed_episode, request, translator, deck_io)
