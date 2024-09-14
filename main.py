from app import *


@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == '__main__':
    # uvicorn 内嵌式启动
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5161)
