import asyncio

from app.Record import Record
from crawl.Item import Item
from crawl.main_page import ScrapeMain
from crawl.nodriver_tools import BrowserAuto
from crawl.sub_page import ScrapeSub
from logger import logger


class Runner:
    def __init__(self, browser_tool: BrowserAuto, record: Record):
        self.browser_tool = browser_tool
        self.record = record

    async def run(self, item: Item):
        async with self.browser_tool:
            try:
                scrape_main = await ScrapeMain.create(self.browser_tool, item)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                raise Exception(f'搜索知网结果页失败 {e}')

            batch = 5
            async for pubs in scrape_main:
                # 分批爬取，减少浏览器压力
                s = batch
                for i in range(0, len(pubs), s):
                    tasks = [self.fill_detail(pub) for pub in pubs[i:i + s]]
                    await asyncio.gather(*tasks)  # 异常不抛出

    async def fill_detail(self, pub):
        page_url = pub['url']
        tool = self.browser_tool
        page = await tool.browser.get(page_url, new_tab=True)
        try:
            sub = ScrapeSub(page)
            await sub.fill_detail(pub)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # 吸收异常
            logger.error(f'爬取子网页失败 {page_url} {e}')
            pub['error'] = str(e)
            return
        finally:
            await page.close()
