import asyncio
import os

from app.heartbeat import HeartBeatTask, goodbye
from app.param_tools import get_int
from app.param_tools import check_key
from crawl import nodriver_tools
from pathlib import Path

from crawl.SearchItem import SearchItem
from crawl.nodriver_tools import BrowserAuto
from logger import logger
from service.Record import Record
from service.Runner import Runner


class SearchTask(HeartBeatTask):

    @classmethod
    async def create(cls, websocket, name):
        await websocket.accept()
        # 解析api参数
        try:
            obj = await websocket.receive_json()
            check_key(obj)
            item = create_item(name, Param(obj))
        except Exception as e:
            await goodbye(websocket, {"error": f"api参数异常 {e}"})
            raise

        # 创建资源
        try:
            browser_auto = await nodriver_tools.create()
        except Exception as e:
            await goodbye(websocket, {'error': f'nodriver启动浏览器出错 {e}'})
            raise

        record = Record()
        runner = Runner(browser_auto, record)

        return cls(websocket, item, browser_auto, record, runner)

    def __init__(self, websocket, item: SearchItem, browser_auto: BrowserAuto, record: Record, runner: Runner):
        super().__init__(websocket)
        self.item = item
        self.browser_auto = browser_auto
        self.record = record
        self.runner = runner

    async def func(self):
        pdf_task = asyncio.create_task(self.send_pdf())
        main_task = asyncio.create_task(self.runner.run(self.item))
        # 等待 main_task 完成
        await main_task

        loop = asyncio.get_running_loop()
        now = loop.time()
        while self.record.pdf_cnt > 0:
            logger.info(f"等待PDF task中 剩余数量为{self.record.pdf_cnt}")
            if loop.time() - now > 30:
                # 如果超时
                logger.error("PDF task timed out. Cancelling...")
                pdf_task.cancel()
                break

            await asyncio.sleep(1)

    async def on_heartbeat(self, data):
        data['progress'] = self.record.get_progress()

    async def on_finish(self, data):
        # 任务执行结果
        data['data'] = self.record.deliver_pubs()

    async def send_pdf(self):
        websocket = self.websocket
        browser_auto = self.browser_auto
        while True:
            path = Path(browser_auto.temp_dir.name)
            pdf_files = list(path.glob('*.pdf'))
            if len(pdf_files) == 0:
                await asyncio.sleep(1)  # 等待
            else:
                # 发送pdf数据
                pdf_file = pdf_files[0]
                pdf_path = pdf_file.resolve()
                with open(pdf_path, 'rb') as file:
                    pdf_data = file.read()

                logger.info(f'准备发送pdf {len(pdf_data)} {pdf_path}')
                # 发送pdf
                await websocket.send_json({'type': 'PdfData', 'file_name': {pdf_file.name}})
                await websocket.send_bytes(pdf_data)
                # 删除本地的
                pdf_path.unlink()
                self.record.pdf_cnt -= 1
                logger.debug(f'剩余pdf_cnt: {self.record.pdf_cnt}')


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
