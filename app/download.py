import asyncio
import tempfile

from fastapi import WebSocket, Path
from starlette.websockets import WebSocketDisconnect

from app.param_tools import param_check, ParamError
from app.server import app, goodbye
from logger import logger


@app.websocket("/search")
async def download(
        websocket: WebSocket,
):
    await websocket.accept()
    # 解析api参数
    from app.param_tools import check_key
    try:
        obj = await websocket.receive_json()
        check_key(obj)
        # 之后可以加入机构登入授权信息
        # ......
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

    await DownloadTask(websocket, browser_auto).finish()


class DownloadTask:
    def __init__(self, websocket: WebSocket, browser_auto):
        self.websocket = websocket

        from service.PdfRunner import PdfRunner
        self.runner = PdfRunner(browser_auto)

    async def finish(self):
        websocket = self.websocket
        runner = self.runner

        # 知网登入机构
        await runner.login_zhiwang()

        # 提示客户端开始接收
        await websocket.send_json({'type': 'Starting'})

        # 不断下载
        while True:
            obj = await websocket.receive_json()
            # 输入分类
            try:
                if is_to_end(obj):
                    break
                elif is_to_download(obj):
                    pdf_link = get_pdf_link(obj)
                    # 爬取pdf
                    await self.do_pdf_download(pdf_link)
                else:
                    raise ParamError(f'未知操作{obj}')

            except ParamError as e:
                await send_error(websocket, f'api请求参数异常 {e}')
                continue
            except asyncio.CancelledError:
                raise
            except WebSocketDisconnect as e:
                logger.error(f"Connection closed: {type(e)} {e}")
                break
            except Exception as e:
                # 其他异常处理
                logger.error(e)
                await send_error(websocket, f'发送异常 {e}')
                continue

    async def do_pdf_download(self, pdf_link):
        websocket = self.websocket
        runner = self.runner
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path = await runner.download_pdf(pdf_link, temp_dir)
                with open(pdf_path, 'rb') as file:
                    pdf_data = file.read()

                logger.info(f'pdf下载成功，准备发送{len(pdf_data)} {pdf_path}')
                # 发送pdf
                await send_pdf(websocket, pdf_data)

        except asyncio.TimeoutError as e:
            await send_error(websocket, 'pdf下载超时')


@param_check
def is_to_end(obj):
    return obj['doing'] == 'end'


@param_check
def is_to_download(obj):
    return obj['doing'] == 'download'


@param_check
def get_pdf_link(obj):
    return obj['pdf_link']


async def send_error(websocket: WebSocket, e=None):
    await websocket.send_json({'type': 'ErrorInfo', 'error': e})


async def send_pdf(websocket: WebSocket, pdf_data):
    await websocket.send_json({'type': 'PdfData'})
    await websocket.send_bytes(pdf_data)
