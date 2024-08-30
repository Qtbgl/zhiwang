import asyncio
import json
import traceback

import fastapi
from fastapi import Path, WebSocket
from starlette.websockets import WebSocketDisconnect

app = fastapi.FastAPI()


@app.websocket("/search/{name}")
async def search(
        websocket: WebSocket,
        name: str = Path(..., title="terms to be searched"),
):
    await websocket.accept()

    async def goodbye(msg_obj: dict):
        await websocket.send_text(json.dumps(msg_obj))
        await websocket.close()  # 关闭连接

    # 解析api参数
    data = await websocket.receive_text()
    from param_tools import check_key, Params
    try:
        obj = json.loads(data)
        check_key(obj)

        from Runner import create_item
        item = create_item(name, Params(obj))
    except Exception as e:
        await goodbye({"error": f"api参数异常 {e}"})
        return

    # 创建资源
    from logger import logger

    try:
        from crawl import nodriver_tools
        browser_auto = await nodriver_tools.create()
    except Exception as e:
        await goodbye({'error': f'nodriver启动浏览器出错 {e}'})
        return

    from app.Record import Record
    record = Record()

    # 使用nodriver爬取网页时，创建新的事件循环
    from app.Runner import Runner
    runner = Runner(browser_auto, record)
    # 创建任务
    task = asyncio.create_task(runner.run(item))
    result = {'type': 'Result', 'error': None}
    try:
        while not task.done():
            # 获取进度
            obj = {'type': 'Heartbeat', 'progress': record.get_progress()}
            await websocket.send_text(json.dumps(obj))  # 发送心跳消息
            await asyncio.sleep(5)

        try:
            await task
        except Exception as e:
            # 异常信息返回，不抛出
            logger.error(f'task error retrieved: {e}')
            result['error'] = str(e)
        finally:
            # 返回任务执行结果
            result['data'] = record.deliver_pubs()
            await goodbye(msg_obj=result)

    except WebSocketDisconnect as e:
        logger.error(f"Connection closed: {type(e)} {e}")
    except Exception as e:
        logger.error(f"Unexpected Error: {type(e)} {e} \n{traceback.format_exc()}")
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Unexpected Error: {type(e)} {e}")
    finally:
        if not task.done():
            logger.info('Task not done, canceling...')
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info("Task was cancelled!")
