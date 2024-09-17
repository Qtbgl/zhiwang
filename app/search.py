import asyncio
import base64
import traceback

from starlette.websockets import WebSocketDisconnect

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
            pdf_task = asyncio.create_task(self._gather_pdf(main_task))
            # 等待 main_task 完成
            try:
                await main_task
            except asyncio.CancelledError:
                logger.debug(f'main_task被取消，一块取消pdf_task')
                pdf_task.cancel()
                raise
            finally:
                await pdf_task

    async def on_heartbeat(self, data):
        data['progress'] = self.record.get_progress()

    async def on_finish(self, data):
        # 任务执行结果
        data['result'] = self.record.deliver_pubs()

    async def _gather_pdf(self, main_task: asyncio.Task):
        while not main_task.done():
            if self.record.unmatched_pdf_cnt == 0:
                # pdf生产者还没有
                await asyncio.sleep(1)  # 等待
                continue

            # 采集pdf
            path = Path(self.browser_auto.temp_dir.name)
            pdf_files = list(path.glob('*.pdf'))
            if len(pdf_files) == 0:
                await asyncio.sleep(1)
                continue

            # 发送pdf数据
            pdf_file = pdf_files[0]
            async with self.send_lock:
                await self._send_pdf(pdf_file)
            # 删除本地的
            pdf_file.unlink()
            self.record.match_pdf(pdf_file)
            logger.debug(f'剩余 pdf_cnt: {self.record.all_pdf_cnt} unmatched: {self.record.unmatched_pdf_cnt}')

    async def _send_pdf(self, pdf_file: Path):
        websocket = self.websocket
        try:
            pdf_path = pdf_file.resolve()
            chunk_size = 1024
            logger.info(f'准备发送 PDF 文件 {pdf_path}')
            with open(pdf_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        # 如果没有更多数据，发送结束信号
                        await websocket.send_json({
                            'type': 'PdfData',
                            'file_name': pdf_file.name,
                            'pdf_data': None,
                        })
                        break

                    # 将二进制嵌入json
                    pdf_data = base64.b64encode(chunk).decode('utf-8')

                    # 发送 PDF 数据块
                    await websocket.send_json({
                        'type': 'PdfData',
                        'file_name': pdf_file.name,
                        'pdf_data': pdf_data,
                    })

                    # 等待客户端确认
                    ack = await websocket.receive_text()
                    assert ack == 'ACK', f'预期 ACK，实际收到: {ack}'

        except asyncio.CancelledError:
            raise
        except WebSocketDisconnect as e:
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
