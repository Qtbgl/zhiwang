import asyncio
import traceback

from nodriver_tools import BrowserAuto
from logger import logger
from parse_zhiwang import parse_result_page


class QuitError(Exception):
    pass


class ScrapeMain:
    def __init__(self, browser_auto: BrowserAuto):
        self.batch_for_detail = 5
        self.browser_auto = browser_auto

    async def get_result_page(self, name, sort_by=None, year=None):
        page = await self.browser_auto.browser.get('https://www.cnki.net/')
        entry = await page.find('中文文献、外文文献')  # 等待直到找到

        await entry.send_keys(name)
        btn = await page.select('body > div.wrapper > div.searchmain > div.search-form > div.input-box > input.search-btn')

        await btn.click()
        # 进入搜索结果页
        succeed = False
        for i in range(5):
            try:
                await page.wait(2)
                await page.wait_for(selector='#ModuleSearchResult tbody > tr')
                succeed = True
                break
            except asyncio.TimeoutError:
                logger.error(f'知网结果页打开失败，尝试次数{i+1}')
                await page.reload(ignore_cache=False)

        assert succeed, '知网结果页打开失败'

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
        else:
            li_sort = None

        if li_sort:
            await li_sort.click()
            await page.wait(2)  # debug 等待更新

        return page

    async def next_page(self, page):
        try:
            next_btn = await page.select('#PageNext', timeout=1)
        except asyncio.exceptions.TimeoutError:
            return False

        try:
            await next_btn.click()
            await page.wait(2)  # debug 等待更新
            await page.wait_for(selector='#ModuleSearchResult tbody > tr')
        except asyncio.TimeoutError:
            raise QuitError('打开下一结果页失败')

        return True

    async def search_pub(self, name, pages=None, sort_by=None, year=None):
        """
        :param pages: 爬取多少页的文献
        :param name: 搜索关键词
        :param sort_by: 排序根据 relevant, date, cite
        :return:
        """
        # 进入页面
        try:
            page = await self.get_result_page(name, sort_by, year)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise Exception(f'搜索结果页失败 {e}')

        # 对每一页的文献
        page_i = 1
        results = []
        try:
            while not (pages and page_i > pages):  # 当前页面与总爬取页面
                logger.info(f'爬取第{page_i}页')
                html_str = await page.get_content()
                pubs = parse_result_page(html_str)
                # 随即加入文献
                results += pubs

                # 分批爬取，减少浏览器压力
                s = self.batch_for_detail
                for i in range(0, len(pubs), s):
                    tasks = [fill_detail(pub, browser) for pub in pubs[i:i + s]]
                    await asyncio.gather(*tasks)  # 异常不抛出

                # 进入下一页
                if not self.next_page(page):
                    break

                page_i += 1

            return results

        except QuitError as e:
            logger.error(f'发生异常，爬取中断 {e}')
            return results  # 返回部分结果
