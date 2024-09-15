import fastapi
from fastapi import WebSocket, Path

app = fastapi.FastAPI()


@app.websocket("/search/{name}")
async def search(
        websocket: WebSocket,
        name: str = Path(..., title="terms to be searched")):
    # 动态加载代码
    from app.search import SearchTask, logger
    try:
        search_task = await SearchTask.create(websocket, name)
    except Exception as e:
        logger.error(f'创建任务失败 {e}')
        return

    await search_task.finish()

