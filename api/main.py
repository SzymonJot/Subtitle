# uvicorn - server to post and run 
# uvicorn api.main:app --reload  
from fastapi import FastAPI, HTTPException
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

app = FastAPI()


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins = ["*"],
#     allow_methods = ["*"],
#     allow_headers = ["*"]
# )

SB = get_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
RQ = Queue("mvp_queue", connection=Redis.from_url(os.environ["REDIS_URL"]))

@app.post("/jobs")
async def create_job(file: int):
    job_id = str(uuid.uuid4())
    (
    SB.table("jobs")
    .insert({
        'id': job_id,
        'input_path': 'a',
        'status': 'queued'
    })
    .execute()
    )
    return {"job_id": job_id}

@app.get("/jobs")
def get_job(job_id: str):
    pass

@app.get("/")
def root():
    return {"Apple"}









# class Item(BaseModel):
#     text: str = None
#     is_done: bool = False



# @app.get('/')
# def root():
#     return {'Hello': 'World'}

# items = []

# @app.post('/items')
# def create_item(item:Item):
#     items.append(item)
#     return item

# @app.get('list',response_model=[Item])
# def get_list(number:int):
#     return items[:number]

# @app.get('/items/{item_id}', response_model=Item)
# def get_item(item_id: int) ->Item:
#     if len(items) <= item_id:
#         return items[item_id]
#     else:
#         return HTTPException(status_code=404, detail = 'Item not found')