import asyncio
import traceback

import nodriver

from nodriver_tools import BrowserAuto
from logger import logger


async def scrape_detail(pub, browser_auto: BrowserAuto):
    page_url = pub['url']
    page = await browser_auto.browser.get(page_url, new_tab=True)  # 新页面
    try:
        await fill_detail(pub, page)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        # 吸收异常
        logger.error(f'scrape_detail失败 {page_url} {e}')
        pub['error'] = str(e)
        return
    finally:
        if page in browser_auto.browser.tabs:
            await page.close()
        else:
            logger.debug(f'为什么页面自动关闭了 {page}')


async def fill_detail(pub, page: nodriver.Tab):
    await page.wait(2)
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
