# uvicorn - server to post and run
# uvicorn api.main:app --reload
from fastapi import FastAPI

"""
Add CORS middleware layer 
It runs before each request 
Decides whether to allow external browser from another website to access this API
CROS - Cross-Origin Resource Sharing
"""
import os

from common.supabase_client import get_client
from infra.supabase.jobs_repo import SBJobsIO

"""
docker run --name redis -p -q 6379:6379 redis:7-alpine
docker ps
docker exec -it redis redis-cli
ping
"""
from redis import Redis

# rq allows for queueing jobs in redis
# Queue task; Respond; Worker pick it up
from rq import Queue

from common.logging import setup_logging

app = FastAPI()
setup_logging()

from api.job import router as job_router
from common.constants import (
    QUEUE_MVP,
)

SB = get_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
RQ = Queue(QUEUE_MVP, connection=Redis.from_url(os.environ["REDIS_URL"]))

sb_jobs_io = SBJobsIO(SB)


app.include_router(job_router)
