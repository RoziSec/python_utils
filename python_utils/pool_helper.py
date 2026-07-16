# -*- coding: utf-8 -*-
"""线程 / 进程池操作类。

对标准库 ``concurrent.futures`` 做一层薄封装，把最常见的“并发 map”
用法简化为一个方法，同时兼顾顺序、超时与异常收集。

    from python_utils import PoolHelper

    # 并发对列表每个元素执行 func，返回与输入同序的结果列表
    results = PoolHelper.map(download, urls, max_workers=8)

    # 进程池处理 CPU 密集任务
    results = PoolHelper.map(heavy_calc, items, max_workers=4, use_process=True)

    # 需要更细控制时用上下文
    with PoolHelper(max_workers=8) as pool:
        futures = [pool.submit(func, x) for x in items]
"""

from __future__ import annotations

from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from typing import Any, Callable, Iterable, List, Optional


class PoolHelper:
    """并发执行工具类，可作为上下文管理器，也提供静态 ``map``。"""

    def __init__(self, max_workers: Optional[int] = None, *, use_process: bool = False):
        """
        :param max_workers: 并发数；None 由标准库按 CPU 决定。
        :param use_process: True 用进程池（CPU 密集），False 用线程池（IO 密集）。
        """
        executor_cls = ProcessPoolExecutor if use_process else ThreadPoolExecutor
        self._executor = executor_cls(max_workers=max_workers)

    def submit(self, fn: Callable, *args, **kwargs):
        """提交单个任务，返回 Future。"""
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)

    def __enter__(self) -> "PoolHelper":
        return self

    def __exit__(self, *exc) -> None:
        self.shutdown()

    # ------------------------------------------------------------------ #
    # 静态并发 map
    # ------------------------------------------------------------------ #
    @staticmethod
    def map(
        func: Callable,
        items: Iterable[Any],
        *,
        max_workers: Optional[int] = None,
        use_process: bool = False,
        timeout: Optional[float] = None,
        ordered: bool = True,
    ) -> List[Any]:
        """并发对 items 每个元素执行 func，返回结果列表。

        :param ordered: True 保持与输入相同顺序；False 谁先完成先返回（更快）。
        :param timeout: 单个任务的超时秒数。
        """
        items = list(items)
        executor_cls = ProcessPoolExecutor if use_process else ThreadPoolExecutor
        with executor_cls(max_workers=max_workers) as ex:
            if ordered:
                futures = [ex.submit(func, it) for it in items]
                return [f.result(timeout=timeout) for f in futures]
            else:
                futures = {ex.submit(func, it): it for it in items}
                results = []
                for f in as_completed(futures, timeout=timeout):
                    results.append(f.result())
                return results


__all__ = ["PoolHelper"]
