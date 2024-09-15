import asyncio
import os
import traceback
import re

import nodriver

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
        # async with self.browser_tool:  # debug 放到更外面
        try:
            self.record.set_pages(item.pages)
            scrape_main = await ScrapeMain.create(self.browser_tool, item)
            logger.info(f'成功打开知网结果页 {scrape_main.page}')
        except asyncio.CancelledError:
            logger.debug(f'Runner遇到任务取消 {traceback.format_exc()}')
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

        page_url = pub['url']
        tool = self.browser_tool
        pub_page = await tool.browser.get(page_url, new_tab=True)
        try:
            await self._fill_pub(pub_page, pub)
        finally:
            if pub_page in tool.browser.tabs:
                await pub_page.close()
            else:
                logger.debug(f'非人为关闭 {pub_page}')

    async def _fill_pub(self, pub_page: nodriver.Tab, pub):
        # 先进入文献页面
        try:
            await ScrapeSub(pub_page).fill_detail(pub)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # 吸收异常
            logger.error(f'爬取子网页失败 {pub["url"]} {e}')
            pub['error'] = str(e)
            await self.record.fail_to_fill(pub)
            return

        pdf_task = asyncio.create_task(self.download_pdf(pub_page, pub))
        bib_task = asyncio.create_task(self.fill_bib(pub))

        # 等待bib任务（依靠bib_link，获取bib）
        try:
            await bib_task
        except asyncio.CancelledError:
            pdf_task.cancel()
            await pdf_task
            raise
        except Exception as e:
            logger.error(f'爬取bib失败 {pub["bib_link"]} {traceback.format_exc()}')
            pub['error'] = str(e)
            await self.record.fail_to_fill(pub)
            return   # 吸收异常

        try:
            await asyncio.wait_for(pdf_task, timeout=30)
        except asyncio.TimeoutError as e:
            logger.error(f'等待pdf失败 {pub["title"]} {pub["url"]}')
            # 吸收异常

        await self.record.success_fill(pub)

    async def download_pdf(self, pub_page: nodriver.Tab, pub):
        try:
            # pdf后台下载
            btn = await pub_page.find('PDF下载', timeout=2)
            await btn.click()
            self.record.pdf_cnt += 1
            logger.debug(f'加入pdf_cnt: {self.record.pdf_cnt}')
        except asyncio.TimeoutError as e:
            logger.error(f'下载PDF异常 {e}')
            return  # 吸收异常

        full_info = pub['title'] + ' ' + pub['author']

        def belong_to_pub(file_name):
            part_info = re.findall(r'[\u4e00-\u9fa5]+', file_name)
            for part in part_info:
                if part not in full_info:
                    return False
            return True

        # 等待pdf下载完成
        while True:
            await asyncio.sleep(2)
            for file in os.listdir(self.browser_tool.temp_dir.name):
                if file.endswith(".pdf") and belong_to_pub(file):
                    break

    async def fill_bib(self, pub):
        bib_link = pub['bib_link']
        tool = self.browser_tool
        page = await tool.browser.get(bib_link, new_tab=True)
        try:
            sub = ScrapeBib(page)
            await sub.fill_bib(pub, max_tries=3)
        finally:
            await page.close()
