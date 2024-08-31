import asyncio

from app.Record import Record
from crawl.Item import Item
from crawl.main_page import ScrapeMain
from crawl.nodriver_tools import BrowserAuto
from crawl.sub_page import ScrapeSub, ScrapeBib
from crawl.wait_tools import wait_to_load
from logger import logger
from data import api_config


class Runner:
    def __init__(self, browser_tool: BrowserAuto, record: Record):
        self.batch = api_config.scrape_batch
        self.browser_tool = browser_tool
        self.record = record

    async def run(self, item: Item):
        logger.info(f'任务请求 {item}')
        async with self.browser_tool:
            try:
                self.record.set_pages(item.pages)
                scrape_main = await ScrapeMain.create(self.browser_tool, item)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                raise Exception(f'搜索知网结果页失败 {e}')

            async for pubs in scrape_main.search_pub(item):
                # 分批爬取，减少浏览器压力
                s = self.batch
                for i in range(0, len(pubs), s):
                    tasks = [self.fill_pub(pub, item) for pub in pubs[i:i + s]]
                    logger.info(f'准备异步爬取 {len(tasks)}')
                    await asyncio.gather(*tasks)  # 异常不抛出

    async def fill_pub(self, pub, item: Item):
        min_cite = item.min_cite
        # 过滤引用数量
        if min_cite is not None and min_cite > 0:
            num_citations = pub.get('num_citations')
            if num_citations is None:
                pub['error'] = f'无引用数量信息'
                self.record.fail_to_fill(pub)
                return
            elif num_citations < min_cite:
                pub['error'] = f'引用数量不足 {pub["num_citations"]} < {min_cite}'
                self.record.fail_to_fill(pub)
                return

        # 先获取bib_link
        try:
            await self.fill_detail(pub)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # 吸收异常
            logger.error(f'爬取子网页失败 {pub["url"]} {e}')
            pub['error'] = str(e)
            self.record.fail_to_fill(pub)
            return

        # 接着获取bib
        try:
            await self.fill_bib(pub)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # 吸收异常
            logger.error(f'爬取bib失败 {pub["bib_link"]} {e}')
            pub['error'] = str(e)
            self.record.fail_to_fill(pub)
            return

        self.record.success_fill(pub)

    async def fill_detail(self, pub):
        page_url = pub['url']
        tool = self.browser_tool
        page = await tool.browser.get(page_url, new_tab=True)
        await wait_to_load(page, 2)
        try:
            sub = ScrapeSub(page)
            await sub.fill_detail(pub)
        finally:
            await page.close()

    async def fill_bib(self, pub):
        bib_link = pub['bib_link']
        tool = self.browser_tool
        page = await tool.browser.get(bib_link, new_tab=True)
        await wait_to_load(page, 2)
        try:
            sub = ScrapeBib(page)
            await sub.fill_bib(pub, max_tries=3)
        finally:
            await page.close()
