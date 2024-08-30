import json

import fastapi
from fastapi import Path, WebSocket

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
        p = Params(obj)
        page = p.pages
        year = p.year
        sort_by = p.sort_by
    except Exception as e:
        await goodbye({"error": f"api参数异常 {e}"})
        return

    from crawl import nodriver_tools
    try:
        browser_auto = await nodriver_tools.create()
    except Exception as e:
        await goodbye({'error': f'nodriver启动浏览器出错 {e}'})
        return



