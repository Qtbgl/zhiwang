import asyncio

import nodriver


async def wait_to_load(page: nodriver.Tab, init_wait=None, wait_gap=0.5, timeout=10):
    if init_wait:
        await page.wait(init_wait)

    async def to_load():
        while not (await page.evaluate("document.readyState") == 'complete'):
            await page.wait(wait_gap)

    await asyncio.wait_for(to_load(), timeout)
