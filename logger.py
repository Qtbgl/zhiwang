from loguru import logger
from datetime import datetime
import os
import sys


if not os.path.exists('data/log'):
    os.makedirs('data/log')

LOG_FILE = f"data/log/app_{datetime.now().strftime('%Y-%m-%d %H%M%S')}.log"
format_ = "{time:MM-DD HH:mm:ss} {level} {message}"

logger.remove()  # 移除默认设置
logger.add(sys.stdout, level="DEBUG", format=format_)
logger.add(LOG_FILE, encoding="utf-8", format=format_)
