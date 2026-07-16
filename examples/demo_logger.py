# -*- coding: utf-8 -*-
"""日志模块使用示例。

运行后请查看 examples/logs 目录：
    debug.log / info.log / warning.log / error.log / critical.log —— 按等级分文件
    all.log —— INFO 及以上汇总
每条日志都带有“模块:函数:行号”，方便定位。

运行：
    cd E:/Code/python_utils
    python -m examples.demo_logger
"""

from python_utils.logger import setup_logger, get_logger


def do_work():
    log = get_logger()
    log.debug("这是一条 DEBUG，会写入 debug.log")
    log.info("这是一条 INFO，会写入 info.log 和 all.log")
    log.warning("这是一条 WARNING，会写入 warning.log")
    try:
        1 / 0
    except ZeroDivisionError:
        # 用 logger.exception 记录异常，会自动附带堆栈
        log.exception("捕获到异常，会写入 error.log")


def main():
    # 入口处配置一次：不输出终端、单文件 5MB 切割、保留 15 天
    setup_logger(
        log_dir="examples/logs",
        rotation="5 MB",
        retention="15 days",
        console=False,   # True 可临时在终端也看到日志，便于调试
    )
    do_work()
    print("日志已写入 examples/logs 目录，请前往查看。")


if __name__ == "__main__":
    main()
