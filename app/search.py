import asyncio
import traceback

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
        async with self.browser_auto:
            main_task = asyncio.create_task(self.runner.run(self.item))
            pdf_task = asyncio.create_task(self.send_pdf())
            # 等待 main_task 完成
            try:
                await main_task
            except asyncio.CancelledError:
                # 一块取消两个任务
                pdf_task.cancel()
                await pdf_task
                # await抛出任务取消异常

            # 同时结束 pdf_task
            pdf_task.cancel()
            try:
                await pdf_task
            except asyncio.CancelledError:
                pass
                # 取消任务，不再抛出

    async def on_heartbeat(self, data):
        data['progress'] = self.record.get_progress()

    async def on_finish(self, data):
        # 任务执行结果
        data['data'] = self.record.deliver_pubs()

    async def send_pdf(self):
        browser_auto = self.browser_auto
        try:
            while True:
                if self.record.pdf_cnt == 0:
                    # pdf生产者还没有
                    await asyncio.sleep(1)  # 等待
                    continue

                path = Path(browser_auto.temp_dir.name)
                pdf_files = list(path.glob('*.pdf'))
                if len(pdf_files) == 0:
                    # logger.debug(f'下载目录中无pdf文件，待处理pdf_cnt: {self.record.pdf_cnt}')
                    await asyncio.sleep(1)  # 等待
                else:
                    # 发送pdf数据
                    pdf_file = pdf_files[0]
                    await self._send_pdf(pdf_file)
                    # 删除本地的
                    pdf_file.unlink()
                    self.record.pdf_cnt -= 1
                    logger.debug(f'剩余pdf_cnt: {self.record.pdf_cnt}')

        except asyncio.CancelledError as e:
            logger.debug(f"send_pdf遇到任务取消 {traceback.format_exc()}")
            raise e

    async def _send_pdf(self, pdf_file: Path):
        websocket = self.websocket
        try:
            pdf_path = pdf_file.resolve()
            with open(pdf_path, 'rb') as file:
                pdf_data = file.read()

            logger.info(f'准备发送pdf 大小{len(pdf_data)} {pdf_file.name}')
            # 发送pdf
            await websocket.send_json({'type': 'PdfData', 'file_name': pdf_file.name})
            await websocket.send_json({'just test': 'PdfData'})
            # await websocket.send_bytes(pdf_data)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f'发送pdf失败 {traceback.format_exc(chain=False)}')
            # 吸收异常


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
