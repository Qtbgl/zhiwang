import os
import tempfile
import traceback

import asyncio
from pathlib import Path

from nodriver.core.browser import Browser, Config

from logger import logger


class BrowserAuto:
    def __init__(self, browser: Browser):
        self.browser = browser
        assert browser and not browser.stopped, 'Crawl的浏览器不可用'
        self.temp_dir = tempfile.TemporaryDirectory()

    async def __aenter__(self):  # 不在此处开启浏览器
        path = Path(self.temp_dir.name)
        logger.info(f'成功打开浏览器，设置临时下载目录 {path}')
        await self.browser.main_tab.set_download_path(path)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 关闭浏览器
        logger.info('准备关闭浏览器')
        try:
            self.browser.stop()  # 标准关闭
        except Exception as e:
            raise e  # 再次抛出，不影响原异常

        try:
            self.temp_dir.cleanup()  # 调用退出函数
        except Exception as e:
            logger.error(f'清除临时目录失败 {e}')


class StartBrowserError(Exception):
    pass


async def create():
    """
    :return: 可能抛出浏览器打开异常
    """
    config = Config(headless=True)
    # 创建实例，一般不会报错
    # 保留实例，以关闭浏览器进程
    browser = Browser(config)
    try:
        await browser.start()
    except Exception as e1:
        logger.error(traceback.format_exc())
        throw = StartBrowserError('浏览器启动失败')
        try:
            stop(browser)
        except Exception as e2:
            logger.error(traceback.format_exc())
            throw = StartBrowserError('浏览器启动失败，且关闭进程时出错')

        raise throw

    return BrowserAuto(browser)


def stop(browser):
    """
    :param browser: 关闭浏览器进程，代码复制于nodriver
    :return:
    """
    self = browser
    assert isinstance(self._process, asyncio.subprocess.Process), '浏览器进程不存在'
    logger.info('进入自定义函数，开始关闭进程')
    for _ in range(3):
        try:
            self._process.terminate()
            logger.info(
                "terminated browser with pid %d successfully" % self._process.pid
            )
            break
        except (Exception,):
            try:
                self._process.kill()
                logger.info(
                    "killed browser with pid %d successfully" % self._process.pid
                )
                break
            except (Exception,):
                try:
                    if hasattr(self, "browser_process_pid"):
                        os.kill(self._process_pid, 15)
                        logger.info(
                            "killed browser with pid %d using signal 15 successfully"
                            % self._process.pid
                        )
                        break
                except (TypeError,):
                    logger.info("typerror", exc_info=True)
                    pass
                except (PermissionError,):
                    logger.info(
                        "browser already stopped, or no permission to kill. skip"
                    )
                    pass
                except (ProcessLookupError,):
                    logger.info("process lookup failure")
                    pass
                except (Exception,):
                    raise
        self._process = None
        self._process_pid = None
