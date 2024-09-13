import asyncio
import pathlib

from crawl.nodriver_tools import BrowserAuto
from logger import logger


class PdfRunner:
    def __init__(self, browser_tool: BrowserAuto):
        self.browser_tool = browser_tool

    async def login_zhiwang(self):
        pass

    async def download_pdf(self, pdf_url, save_dir: str):
        """
        :param pdf_url:
        :param save_dir: 应该是新创的路径
        抛出超时异常
        """
        # 初始转换
        if isinstance(save_dir, str):
            save_dir = pathlib.Path(save_dir)
        else:
            raise TypeError('save_dir must be str')

        browser_tool = self.browser_tool
        page = await browser_tool.browser.get(pdf_url, new_tab=True)
        try:
            # Check if the page has loaded successfully
            loop = asyncio.get_running_loop()
            now = loop.time()
            while True:
                # pdf已存在
                pdf_paths = list(save_dir.glob('*.pdf'))
                if len(pdf_paths):
                    if len(pdf_paths) > 1:
                        logger.warning(f'下载目录中pdf不唯一 {pdf_paths}')

                    pdf_path = pdf_paths[0]
                    save_path = pdf_path.resolve()
                    return save_path

                # 等待超时
                if loop.time() - now >= 60:
                    raise asyncio.TimeoutError

                await asyncio.sleep(2)

        finally:
            if page in browser_tool.browser.tabs:
                logger.error('页面未自动关闭，尝试关闭')
                await page.close()
