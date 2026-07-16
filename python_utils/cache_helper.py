# -*- coding: utf-8 -*-
"""缓存与重试工具。

提供三样常用能力，纯标准库实现，线程安全：

* ``CacheHelper``：带 TTL（过期时间）+ LRU（容量上限）的内存缓存对象；
* ``@cache``：把上述缓存能力作为装饰器套在函数上，自动缓存返回值；
* ``@retry``：失败自动重试，支持指数退避与指定异常类型。

    from python_utils import CacheHelper, cache, retry

    c = CacheHelper(maxsize=100, ttl=60)
    c.set("k", 123); c.get("k")

    @cache(ttl=30)
    def load_user(uid): ...

    @retry(times=3, delay=0.5, backoff=2.0, exceptions=(IOError,))
    def call_api(): ...
"""

from __future__ import annotations

import functools
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Optional, Tuple, Type

_MISSING = object()


class CacheHelper:
    """线程安全的 TTL + LRU 内存缓存。"""

    def __init__(self, maxsize: int = 128, ttl: Optional[float] = None):
        """
        :param maxsize: 最大条目数，超出按最近最少使用淘汰。
        :param ttl: 默认过期秒数；``None`` 表示不过期。
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._data: "OrderedDict[Any, Tuple[Any, Optional[float]]]" = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: Any, default: Any = None) -> Any:
        """取值；不存在或已过期返回 default。"""
        with self._lock:
            item = self._data.get(key, _MISSING)
            if item is _MISSING:
                return default
            value, expire_at = item
            if expire_at is not None and time.time() > expire_at:
                del self._data[key]
                return default
            self._data.move_to_end(key)  # 命中即刷新 LRU 顺序
            return value

    def set(self, key: Any, value: Any, ttl: Optional[float] = _MISSING) -> None:
        """写入；ttl 省略用默认 ttl。"""
        with self._lock:
            use_ttl = self.ttl if ttl is _MISSING else ttl
            expire_at = time.time() + use_ttl if use_ttl else None
            self._data[key] = (value, expire_at)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)  # 淘汰最久未用

    def delete(self, key: Any) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __contains__(self, key: Any) -> bool:
        return self.get(key, _MISSING) is not _MISSING

    def __len__(self) -> int:
        return len(self._data)


def cache(ttl: Optional[float] = None, maxsize: int = 128) -> Callable:
    """函数结果缓存装饰器（按参数缓存），支持 TTL + LRU。

    仅适用于参数可哈希的函数。附带 ``.cache_clear()`` 清空。
    """
    store = CacheHelper(maxsize=maxsize, ttl=ttl)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            hit = store.get(key, _MISSING)
            if hit is not _MISSING:
                return hit
            result = func(*args, **kwargs)
            store.set(key, result)
            return result

        wrapper.cache_clear = store.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator


def retry(
    times: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    on_retry: Optional[Callable[[int, BaseException], None]] = None,
) -> Callable:
    """失败重试装饰器，支持指数退避。

    :param times: 最多尝试次数（含首次）。
    :param delay: 首次重试前的等待秒数。
    :param backoff: 每次重试等待时间的放大倍数（指数退避）。
    :param exceptions: 只对这些异常重试，其余直接抛出。
    :param on_retry: 每次重试前的回调，入参为 (第几次, 异常)。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            last_exc: Optional[BaseException] = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: PERF203
                    last_exc = exc
                    if attempt == times:
                        break
                    if on_retry:
                        on_retry(attempt, exc)
                    time.sleep(wait)
                    wait *= backoff
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


__all__ = ["CacheHelper", "cache", "retry"]
