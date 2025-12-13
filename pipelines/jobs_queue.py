import os

from redis import Redis
from rq import Queue

redis_conn = Redis.from_url(os.environ["REDIS_URL"])
job_queue = Queue(name="JOB_QUEUE", connection=redis_conn)
