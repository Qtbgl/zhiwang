import asyncio

from logger import logger


class ScreenshotAuto:
    def __init__(self, page, dont_raise_timeout=True):
        self.page = page
        self.dont_raise_timeout = dont_raise_timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 检查是否有异常
        if exc_type is not None:
            if exc_type is asyncio.TimeoutError:
                # 如果是 asyncio.TimeoutError，不抛出异常
                path = await self.page.save_screenshot()
                logger.error(f'网页等待元素异常 {exc_val} 截图已保存 {path}')
                if self.dont_raise_timeout:
                    return True  # 返回 True 表示抑制异常

            elif exc_type is asyncio.CancelledError:
                pass
            else:
                # 打印其他异常信息
                logger.error(f"ScreenshotAuto遇到其他异常 {exc_type} {exc_val}")

        return False  # 返回 False 表示不抑制异常
