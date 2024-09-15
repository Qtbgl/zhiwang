import asyncio
import traceback

from service.Record import Record
from crawl.SearchItem import SearchItem
from crawl.main_page import ScrapeMain
from crawl.nodriver_tools import BrowserAuto
from crawl.sub_page import ScrapeSub, ScrapeBib
from logger import logger
from data import api_config


class Runner:
    def __init__(self, browser_tool: BrowserAuto, record: Record):
        self.batch = api_config.scrape_batch
        self.browser_tool = browser_tool
        self.record = record

    async def run(self, item: SearchItem):
        logger.info(f'任务请求 {item}')
        async with self.browser_tool:
            try:
                self.record.set_pages(item.pages)
                scrape_main = await ScrapeMain.create(self.browser_tool, item)
                logger.info(f'成功打开知网结果页 {scrape_main.page}')
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

    async def fill_pub(self, pub, item: SearchItem):
        min_cite = item.min_cite
        # 过滤引用数量
        if min_cite is not None and min_cite > 0:
            num_citations = pub.get('num_citations')
            if num_citations is None:
                pub['error'] = f'无引用数量信息'
                await self.record.fail_to_fill(pub)
                return
            elif num_citations < min_cite:
                pub['error'] = f'引用数量不足 {pub["num_citations"]} < {min_cite}'
                await self.record.fail_to_fill(pub)
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
            await self.record.fail_to_fill(pub)
            return

        # 接着获取bib
        try:
            await self.fill_bib(pub)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # 吸收异常
            logger.error(f'爬取bib失败 {pub["bib_link"]}')
            logger.debug(traceback.format_exc())
            pub['error'] = str(e)
            await self.record.fail_to_fill(pub)
            return

        await self.record.success_fill(pub)

    async def fill_detail(self, pub):
        page_url = pub['url']
        tool = self.browser_tool
        page = await tool.browser.get(page_url, new_tab=True)
        try:
            sub = ScrapeSub(page)
            await sub.fill_detail(pub)

            # pdf...
            btn = await page.find('#pdfDown', timeout=2)
            await btn.click()

        finally:
            await page.close()

    async def fill_bib(self, pub):
        bib_link = pub['bib_link']
        tool = self.browser_tool
        page = await tool.browser.get(bib_link, new_tab=True)
        try:
            sub = ScrapeBib(page)
            await sub.fill_bib(pub, max_tries=3)
        finally:
            await page.close()
