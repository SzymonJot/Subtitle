"""
RQ Worker for processing background jobs.

On Windows, use SimpleWorker which doesn't rely on Unix forking.
Run with: python -m worker.worker
"""

import logging

from rq.worker import SimpleWorker

from pipelines.jobs_queue import job_queue, redis_conn

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    # Use SimpleWorker for Windows compatibility (no forking)
    worker = SimpleWorker([job_queue], connection=redis_conn)
    logging.info(f"Starting RQ worker for queue: {job_queue.name}")
    worker.work()
