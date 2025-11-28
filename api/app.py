# uvicorn - server to post and run 
# uvicorn api.main:app --reload  
from fastapi import FastAPI, HTTPException, UploadFile
'''
Add CORS middleware layer 
It runs before each request 
Decides whether to allow external browser from another website to access this API
CROS - Cross-Origin Resource Sharing
'''
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from common.supabase_client import get_client
from dotenv import load_dotenv
import os
import uuid
from worker.worker import run_job
from common.schemas import BuildDeckRequest
from infra.supabase.jobs_repo import SBJobsIO
'''
docker run --name redis -p -q 6379:6379 redis:7-alpine
docker ps
docker exec -it redis redis-cli
ping
'''
from redis import Redis
# rq allows for queueing jobs in redis
# Queue task; Respond; Worker pick it up
from rq import Queue
import logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

from common.constants import (
    TABLE_JOBS, BUCKET_UPLOADS, QUEUE_MVP, STATUS_QUEUED, EXT_SRT
)

SB = get_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
RQ = Queue(QUEUE_MVP, connection=Redis.from_url(os.environ["REDIS_URL"]))

sb_jobs_io = SBJobsIO(SB)

@app.post("/jobs")
async def create_job(file: UploadFile):
    if not file.filename.lower().endswith(EXT_SRT):
        raise HTTPException(status_code=400, detail=f"Only {EXT_SRT} files")
    
    job_id = str(uuid.uuid4())
    raw = await file.read()

    in_path = f"{BUCKET_UPLOADS}/{job_id}"
    jobs_table = TABLE_JOBS

    sb_jobs_io.upload_file(
        bucket_name = BUCKET_UPLOADS,
        file = raw, 
        name = job_id
    )
    sb_jobs_io.insert_job(
        job_id = job_id, 
        in_path = in_path, 
        jobs_table = jobs_table, 
        status = STATUS_QUEUED, 
        params = {
            'file_type': 'srt',
            'language': 'sv'
        }
    )

    # Background tasks will be triggered.
    run_job(job_id)
    return {"job_id": job_id}

# Get processed episode
@app.get("/jobs/{job_id}/analysis")
def get_job_analysis(job_id: str):
    return sb_jobs_io.download_analysis(job_id)

@app.get("/jobs/{job_id}/preview")
def get_preview(job_id: str):
    # GET processed episode
    return 

@app.post("/jobs/{job_id}/deck")
def get_deck(request: BuildDeckRequest, job_id: str):
    # Placeholder for deck generation logic
    return {"status": "processing", "job_id": job_id, "request": request.dict()}

@app.get("/jobs")
def get_job(job_id: str):
    return sb_jobs_io.get_job(job_id)
