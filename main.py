# uvicorn - server to post and run 
# uvicorn api.main:app --reload  


if __name__ == "__main__":
    import uvicorn
    from api.app import create_job
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload = True)
    

from api.app import create_job
with open("tests/ep1.srt", "rb") as f:
    data = f.read()
print('finished')







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