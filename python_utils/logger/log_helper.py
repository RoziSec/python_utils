# -*- coding: utf-8 -*-
"""基于 loguru 的日志模块。

设计目标（对应需求）：

1. **不打印到终端**：初始化时移除 loguru 默认的控制台 handler，日志只写文件；
2. **按固定文件大小定期存储**：每个日志文件写满指定大小后自动切割（rotation），
   旧文件按时间保留一段时间后清理（retention），并压缩节省空间；
3. **可追溯到模块与行号**：日志格式中包含 ``{name}:{function}:{line}``，
   即“哪个模块 - 哪个函数 - 第几行”；
4. **按等级分文件存放**：DEBUG / INFO / WARNING / ERROR / CRITICAL 各写入
   独立的日志文件，每个文件只包含对应等级的记录，便于按等级排查。

使用方式::

    from python_utils.logger import setup_logger, get_logger

    setup_logger(log_dir="logs")     # 程序入口处配置一次
    log = get_logger()               # 任意模块中获取
    log.info("服务启动")
    log.error("出错啦")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Union

from loguru import logger

# loguru 是全局单例，用一个标志避免重复配置导致 handler 叠加
_CONFIGURED = False

# 日志格式：时间 | 等级 | 模块:函数:行号 | 进程/线程 | 消息
# {name} 为模块名，{function} 为函数名，{line} 为行号——满足“追溯到哪个模块哪一行”。
_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "P{process}:T{thread} | "
    "{message}"
)

# 需要各自独立成文件的等级
_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _level_only_filter(level_name: str):
    """生成一个“只放行指定等级”的过滤器，实现按等级分文件。"""

    def _filter(record) -> bool:
        return record["level"].name == level_name

    return _filter


def setup_logger(
    log_dir: Union[str, Path] = "logs",
    *,
    rotation: str = "10 MB",
    retention: str = "30 days",
    compression: str = "zip",
    encoding: str = "utf-8",
    enqueue: bool = True,
    backtrace: bool = True,
    diagnose: bool = False,
    console: bool = False,
    force: bool = False,
):
    """配置日志系统（建议在程序入口处调用一次）。

    :param log_dir: 日志文件目录，不存在会自动创建。
    :param rotation: 触发切割的条件，默认 ``"10 MB"``（写满 10MB 换新文件）。
        也可写成 ``"500 MB"``、``"1 day"``、``"00:00"`` 等 loguru 支持的形式。
    :param retention: 旧日志保留时长，默认 ``"30 days"``，超期自动删除。
    :param compression: 切割后旧文件的压缩格式，默认 ``"zip"``；置 ``None`` 不压缩。
    :param encoding: 文件编码，默认 ``utf-8``。
    :param enqueue: 是否异步写入（多进程/多线程安全，且不阻塞主逻辑），默认开启。
    :param backtrace: 异常时是否展开完整调用栈，默认开启。
    :param diagnose: 异常栈是否显示变量值，生产环境建议 ``False`` 以免泄露敏感信息。
    :param console: 是否同时输出到终端，默认 ``False``（满足“不打印在终端屏幕上”）。
    :param force: 为 ``True`` 时强制重新配置（先清空已有 handler）。
    :return: 配置好的全局 ``logger``。
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return logger

    # 1) 移除所有默认 handler —— 关键：去掉默认输出到 stderr 的控制台 handler
    logger.remove()

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 2) 按等级分别添加文件 handler，每个文件只记录对应等级
    common = dict(
        format=_LOG_FORMAT,
        rotation=rotation,       # 按固定大小切割
        retention=retention,     # 定期清理旧文件
        compression=compression, # 压缩旧文件
        encoding=encoding,
        enqueue=enqueue,
        backtrace=backtrace,
        diagnose=diagnose,
    )
    for level in _LEVELS:
        logger.add(
            log_path / f"{level.lower()}.log",
            level=level,
            filter=_level_only_filter(level),
            **common,
        )

    # 另外再写一个汇总文件 all.log（INFO 及以上全部汇总），方便整体浏览时序
    logger.add(
        log_path / "all.log",
        level="INFO",
        **common,
    )

    # 3) 可选：调试期开启控制台输出
    if console:
        logger.add(sys.stderr, level="DEBUG", format=_LOG_FORMAT)

    _CONFIGURED = True
    logger.debug("日志系统初始化完成，日志目录：{}", log_path.resolve())
    return logger


def get_logger():
    """获取全局 logger；若尚未配置则以默认参数自动配置一次。

    直接使用返回的 logger 记录日志，其定位信息（模块、行号）会自动指向
    真正调用日志方法的位置，无需额外处理。
    """
    if not _CONFIGURED:
        setup_logger()
    return logger


__all__ = ["get_logger", "setup_logger", "logger"]
