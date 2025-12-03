import logging
import os
import sys
import time
from logging.handlers import TimedRotatingFileHandler

os.chdir(sys.path[0])

# Configuration constants
LOG_RETENTION_DAYS: int = 7


def cleanup_old_logs(log_dir: str, retention_days: int) -> None:
    """Delete log files older than retention_days.
    
    Args:
        log_dir: Directory containing log files
        retention_days: Number of days to retain logs
    
    Returns:
        None
    """
    if not os.path.exists(log_dir):
        return
    
    current_time = time.time()
    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        if os.path.isfile(file_path):
            file_age_days = (current_time - os.path.getmtime(file_path)) / (24 * 3600)
            if file_age_days > retention_days:
                try:
                    os.remove(file_path)
                    logger = logging.getLogger("BitConnected")
                    if logger.handlers:
                        logger.debug(f"Deleted old log file: {filename}")
                except OSError:
                    pass


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
    
    # Clean up old logs
    cleanup_old_logs("logs", LOG_RETENTION_DAYS)

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
