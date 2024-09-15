import asyncio
import traceback

import bibtexparser
import nodriver

from crawl.error_tools import ScreenshotAuto
from crawl.wait_tools import wait_to_complete
from logger import logger


class ScrapeSub:
    def __init__(self, page: nodriver.Tab):
        self.page = page

    async def fill_detail(self, pub):
        page = self.page
        await page.wait(2)
        await page.wait_for(text=pub['title'], timeout=30)
        # 暂时测试
        # logger.debug(f"ScrapeSub.fill_detail 0 {pub['title']}")
        await wait_to_complete(page, timeout=30)
        # logger.debug(f"ScrapeSub.fill_detail 1 {pub['title']}")

        # 假设网页已加载完成（之后的timeout不用太长）

        page_screenshot = ScreenshotAuto(page)

        # 使用nodriver自带网页解析功能：
        async with page_screenshot:
            more = await page.select('#ChDivSummaryMore', timeout=2)
            # 展开摘要
            if more.attrs['style'] != 'display:none':
                # print('展开摘要', page_url)
                await more.click()
                await page.wait(0.5)

        async with page_screenshot:
            summary = await page.select('#ChDivSummary', timeout=2)
            pub['abstract'] = summary.text.strip()

        # 爬取其他信息（不太重要）

        # 爬取pdf链接（此页面中打开才行）
        # async with page_screenshot:
        #     a = await page.select('#pdfDown', timeout=2)
        #     pub['pdf_link'] = a.attrs['href']

        # 点击引用格式
        async with page_screenshot:
            quote = await page.select('div.top-second li.btn-quote > a', timeout=2)
            # 打开引用弹框
            await quote.click()
            await page.wait(2)

            a = await page.find(text='更多引用格式')
            bib_link = a.attrs['href']
            pub['bib_link'] = bib_link


class ScrapeBib:
    def __init__(self, page: nodriver.Tab):
        self.page = page

    async def _click_and_get(self):
        page = self.page
        # 点中bib格式
        a_bib = await page.select('div.export-sidebar-a > ul > li > a[displaymode="BibTex"]')
        await a_bib.click()
        await page.wait(2)
        # 等待后再尝试
        tag_bib = await page.select('#result > ul > li', timeout=30)
        bib_str = tag_bib.text_all.strip()
        return bib_str

    async def fill_bib(self, pub, max_tries):
        page = self.page
        err_sample = None

        # 等待页面加载
        await page.wait_for(text='文献导出格式', timeout=30)
        loaded = await wait_to_complete(page, timeout=30)
        if not loaded:
            logger.warning(f'bib页面未加载完成')

        for i in range(max_tries):
            try:
                # 尝试爬取
                bib_str = await self._click_and_get()
                # 检查格式
                bib_db = bibtexparser.loads(bib_str)
                assert len(bib_db.entries) > 0, f'格式异常{bib_str[:20]}...'
                pub['bib'] = bibtexparser.dumps(bib_db)
                return
            except Exception as e:
                logger.error(f'bibtexparser解析失败，尝试{i + 1} {type(e)} {e}')
                err_sample = e
                await page.reload()  # 并刷新网页

        raise Exception(f'bibtexparser解析失败，已尝试{max_tries} {err_sample}')
