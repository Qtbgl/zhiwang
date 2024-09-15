import asyncio
import traceback

import nodriver

from crawl.SearchItem import SearchItem
from crawl.error_tools import ScreenshotAuto
from crawl.nodriver_tools import BrowserAuto
from crawl.wait_tools import wait_to_complete
from logger import logger
from crawl.parse_zhiwang import parse_result_page


class ScrapeMain:
    def __init__(self, page: nodriver.Tab):
        self.batch_for_detail = 5
        self.page = page

    @classmethod
    async def create(cls, tool: BrowserAuto, item: SearchItem):
        name = item.name

        page = await tool.browser.get('https://www.cnki.net/', new_tab=True)
        page_screenshot = ScreenshotAuto(page, dont_raise_timeout=False)

        async with page_screenshot:
            entry = await page.find('中文文献、外文文献', timeout=30)  # 等待直到找到
            await wait_to_complete(page, timeout=30)  # 等待网页加载

            await entry.send_keys(name)
            btn = await page.select(
                'body > div.wrapper > div.searchmain > div.search-form > div.input-box > input.search-btn',
                timeout=2)

            await btn.click()

        # 进入搜索结果页
        succeed = False
        max_tries = 5
        for i in range(max_tries):
            try:
                await page.wait(2)
                await page.wait_for(selector='#ModuleSearchResult tbody > tr')
                succeed = True
                break
            except asyncio.TimeoutError:
                logger.error(f'知网结果页打开失败，尝试次数{i+1}')
                await page.reload(ignore_cache=False)

        if not succeed:
            path = await page.save_screenshot()
            logger.error(f'知网结果页打开失败，已尝试{max_tries}，截图已保存 {path}')
            raise Exception('知网结果页打开失败')

        return cls(page)

    async def filter_result(self, item: SearchItem):
        year = item.year
        sort_by = item.sort_by
        page = self.page
        # 指定年份
        if year is not None:
            bar = await page.select('#ModuleGroupFilter')
            ye = await bar.query_selector('dl[groupid="YE"]')
            t = await ye.query_selector('i.icon.icon-arrow')
            await t.click()
            await page.wait(0.5)
            # 已展开列表
            t = await ye.query_selector(f'input[type="checkbox"][value="{year}"]')
            await t.click()
            await page.wait(2)  # debug 等待更新

        # 指定排序
        if sort_by == 'relevant':
            li_sort = await page.select('#CF')
        elif sort_by == 'date':
            li_sort = await page.select('#PT')
        elif sort_by == 'cite':
            li_sort = await page.select('#CF')
        elif sort_by == 'download':
            li_sort = await page.select('#DFR')
        else:
            li_sort = None

        if li_sort:
            await li_sort.click()
            await page.wait(2)  # debug 等待更新

    async def next_page(self):
        page = self.page
        try:
            next_btn = await page.select('#PageNext', timeout=1)
        except asyncio.exceptions.TimeoutError:
            return False

        try:
            await next_btn.click()
            await page.wait(2)  # debug 等待更新
            await page.wait_for(selector='#ModuleSearchResult tbody > tr')
        except asyncio.TimeoutError:
            raise Exception('打开下一结果页失败')

        return True

    async def search_pub(self, item: SearchItem):
        page = self.page

        try:
           await self.filter_result(item)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception(f'筛选结果出错 {e}')

        # 对每一页的文献
        page_i = 1
        pages = item.pages
        try:
            while True:
                logger.info(f'爬取第{page_i}页')
                html_str = await page.get_content()
                pubs = parse_result_page(html_str)
                yield pubs

                # 进入下一页
                page_i += 1
                if pages and page_i > pages:  # 当前页面 vs 总爬取页面
                    break
                if not await self.next_page():
                    break
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception(f'发生异常，爬取中断 {e}')
