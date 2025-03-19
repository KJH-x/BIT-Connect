import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

os.chdir(sys.path[0])


def setup_logger() -> logging.Logger:
    """初始化日志系统

    Returns:
        logging.Logger: 配置好的日志器实例
    """
    logger = logging.getLogger("BitConnected")

    if logger.handlers:
        logger.debug("[Warning] Logger 再次实例化")
        return logger

    logger.setLevel(logging.DEBUG)

    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)

    # 控制台输出 INFO 及以上级别
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt='%H:%M:%S'
    ))

    # 文件输出 DEBUG 及以上级别
    file_handler = TimedRotatingFileHandler(
        "logs/BitConnected.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)8s | %(filename)20s | %(message)s"
    ))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
