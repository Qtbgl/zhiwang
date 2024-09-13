import asyncio

from fastapi import WebSocket, Path

from app.param_tools import get_int
from app.server import app, goodbye, HeartBeatTask
from crawl.SearchItem import SearchItem


@app.websocket("/search/{name}")
async def search(
        websocket: WebSocket,
        name: str = Path(..., title="terms to be searched"),
):
    await websocket.accept()
    # 解析api参数
    from app.param_tools import check_key
    try:
        obj = await websocket.receive_json()
        check_key(obj)
        item = create_item(name, Param(obj))
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

    from service.Record import Record
    record = Record()

    from service.Runner import Runner
    runner = Runner(browser_auto, record)

    # 创建任务
    task = asyncio.create_task(runner.run(item))
    await SearchTask(websocket, record).run_task(task)


class SearchTask(HeartBeatTask):
    def __init__(self, websocket: WebSocket, record):
        super().__init__(websocket)
        from service.Record import Record
        self.record: Record = record

    async def on_heartbeat(self, data):
        data['progress'] = self.record.get_progress()

    async def on_finish(self, data):
        # 任务执行结果
        data['data'] = self.record.deliver_pubs()


class Param:
    def __init__(self, obj: dict):
        self.obj = obj

    @property
    def pages(self):
        return get_int(self.obj, 'pages', a=1, default=1)

    @property
    def year(self):
        return get_int(self.obj, 'year_low', a=1900, b=2024)

    @property
    def sort_by(self):
        obj = self.obj
        val = obj.get('sort_by')
        if val is None:
            return None

        assert val in ('relevant', 'date', 'cite', 'download')
        return val

    @property
    def min_cite(self):
        return get_int(self.obj, 'min_cite', a=0)


def create_item(name: str, p: Param):
    return SearchItem(name, p.pages, p.sort_by, p.year, p.min_cite)
