import asyncio

from fastapi import WebSocket, Path


from app.server import app, goodbye, HeartBeatTask
from logger import logger


@app.websocket("/search/{name}")
async def search(
        websocket: WebSocket,
        name: str = Path(..., title="terms to be searched"),
):
    await websocket.accept()
    # 解析api参数
    from app.param_tools import check_key, Params
    from crawl.Item import create_item
    try:
        obj = await websocket.receive_json()
        check_key(obj)
        item = create_item(name, Params(obj))
    except Exception as e:
        await goodbye(websocket, {"error": f"api参数异常 {e}"})
        return

    # 创建资源
    try:
        from crawl import nodriver_tools
        browser_auto = await nodriver_tools.create()
    except Exception as e:
        await goodbye(websocket, {'error': f'nodriver启动浏览器出错 {e}'})
        return

    from app.Record import Record
    record = Record()

    from app.Runner import Runner
    runner = Runner(browser_auto, record)

    # 创建任务
    task = asyncio.create_task(runner.run(item))
    await SearchTask(websocket, record).run_task(task)


class SearchTask(HeartBeatTask):
    def __init__(self, websocket: WebSocket, record):
        super().__init__(websocket)
        from app.Record import Record
        self.record: Record = record

    async def on_heartbeat(self, data):
        data['progress'] = self.record.get_progress()

    async def on_finish(self, data):
        # 任务执行结果
        data['data'] = self.record.deliver_pubs()
