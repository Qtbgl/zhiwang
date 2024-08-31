import asyncio
import traceback

import bibtexparser
import nodriver

from logger import logger


class ScrapeSub:
    def __init__(self, page: nodriver.Tab):
        self.page = page

    async def fill_detail(self, pub):
        page = self.page
        await page.wait_for('#ChDivSummary')
        # 用nodriver自带网页解析
        # 展开摘要
        more = await page.select('#ChDivSummaryMore')
        if more.attrs['style'] != 'display:none':
            # print('展开摘要', page_url)
            await more.click()
            await page.wait(0.5)

        summary = await page.select('#ChDivSummary')
        pub['abstract'] = summary.text.strip()

        # 其他信息爬取
        try:
            doc = await page.select('div.container > div.doc')
            p = await doc.query_selector('p.keywords')
            pub['keywords'] = p.text_all if p else None

            institution = await page.select('#authorpart + h3.author')
            ins = [span.text.strip() for span in await institution.query_selector_all('span')]
            ins = ';'.join(ins)
            pub['institution'] = ins

            # doi = await page.find('DOI：')
            # doi = await doi.parent
            # p = await doi.query_selector('span.rowtit + p')
            # pub['doi'] = p.text
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(traceback.format_exc())

        # 引用格式
        quote = await page.select('div.top-second li.btn-quote > a')

        # 打开引用弹框
        await quote.click()
        await page.wait(2)

        a = await page.find(text='更多引用格式')
        bib_link = a.attrs['href']
        pub['bib_link'] = bib_link


class ScrapeBib:
    def __init__(self, page: nodriver.Tab):
        self.page = page

    async def get_bib(self):
        page = self.page
        await page.wait_for(text='文献导出格式')
        # 点中bib格式
        a_bib = await page.select('div.export-sidebar-a > ul > li > a[displaymode="BibTex"]')
        await a_bib.click()
        await page.wait(2)
        # 等待后再尝试
        tag_bib = await page.select('#result > ul > li', timeout=10)
        bib_str = tag_bib.text_all.strip()
        return bib_str

    async def fill_bib(self, pub, max_tries):
        bib_str = await self.get_bib()
        for i in range(max_tries):
            # 检查格式
            try:
                bib_db = bibtexparser.loads(bib_str)
                assert len(bib_db.entries) > 0
                entry = bib_db.entries[0]
                entry['abstract'] = pub['abstract']
                pub['bib'] = bibtexparser.dumps(bib_db)
                return
            except Exception as e:
                logger.error(f'bibtexparser失败{i + 1} {e}')
                bib_str = await self.get_bib()

        raise Exception(f'bibtexparser无法解析 {bib_str}')
