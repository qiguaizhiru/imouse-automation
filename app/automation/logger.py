import logging
import os
import sys
from datetime import datetime

from .paths import data_path


def setup_logger(name="automation", log_dir=None, level=logging.INFO):
    if log_dir is None:
        log_dir = data_path("logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件日志（utf-8，稳定）
    log_file = os.path.join(log_dir, f"{name}_{datetime.now():%Y%m%d}.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 控制台日志：打包成窗口程序时 sys.stdout 可能为 None；
    # 且 Windows 控制台是 gbk，遇到 emoji 等会报错。仅在有可写 stdout 时添加，
    # 并且不因编码问题打断程序。
    stream = sys.stdout
    if stream is not None:
        try:
            ch = logging.StreamHandler(stream)
            ch.setLevel(level)
            ch.setFormatter(fmt)
            logger.addHandler(ch)
        except Exception:
            pass

    return logger
