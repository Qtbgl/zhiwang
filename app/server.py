import abc
import asyncio
import traceback

import fastapi
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from logger import logger


app = fastapi.FastAPI()


async def goodbye(websocket, msg_obj: dict):
    await websocket.send_json(msg_obj)
    await websocket.close()  # 关闭连接


class HeartBeatTask:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.heartbeat_sec = 5

    @abc.abstractmethod
    async def on_heartbeat(self, data):
        pass

    @abc.abstractmethod
    async def on_finish(self, data):
        pass

    async def run_task(self, task: asyncio.Task):
        websocket = self.websocket
        try:
            while not task.done():
                # 获取进度
                data = {'type': 'Heartbeat'}
                await self.on_heartbeat(data)
                await websocket.send_json(data)  # 发送心跳消息
                await asyncio.sleep(self.heartbeat_sec)

            # 任务完成或退出
            data = {'type': 'Result', 'error': None}
            try:
                await task
            except Exception as e:
                logger.error(f'task error retrieved: {e}')
                data['error'] = str(e)

            await self.on_finish(data)
            await goodbye(websocket, data)

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
                    await asyncio.wait_for(task, timeout=60)  # 限定时间等待
                except asyncio.CancelledError:
                    logger.info("Task was cancelled!")
