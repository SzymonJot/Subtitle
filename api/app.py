# uvicorn - server to post and run
# uvicorn api.main:app --reload
from fastapi import FastAPI

"""
Add CORS middleware layer 
It runs before each request 
Decides whether to allow external browser from another website to access this API
CROS - Cross-Origin Resource Sharing
"""

from infra.supabase.jobs_repo import SBJobsIO

"""
docker run --name redis -p -q 6379:6379 redis:7-alpine
docker ps
docker exec -it redis redis-cli
ping
"""

# rq allows for queueing jobs in redis
# Queue task; Respond; Worker pick it up

from common.logging import setup_logging

app = FastAPI()
setup_logging()

from api.routers.job import router as job_router

sb_jobs_io = SBJobsIO()


app.include_router(job_router)
