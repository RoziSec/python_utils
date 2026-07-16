# -*- coding: utf-8 -*-
"""时间日期操作类。

统一处理时间戳、字符串、``datetime`` 三者互转，以及时区、相对时间、
时间区间、耗时计时等高频需求。全部为静态方法，另附一个 ``Timer`` 计时器。

    from python_utils import DateTimeHelper as DT

    DT.now_str()                       # '2026-07-06 16:44:04'
    DT.to_timestamp('2026-07-06 12:00:00')
    DT.from_timestamp(1751788800)
    DT.day_range()                     # 今天 00:00:00 ~ 23:59:59 的 (start, end)
    with DateTimeHelper.Timer() as t:  # 计时
        do_something()
    print(t.elapsed)
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union

DEFAULT_FMT = "%Y-%m-%d %H:%M:%S"
DATE_FMT = "%Y-%m-%d"
DateLike = Union[str, int, float, datetime]


class DateTimeHelper:
    """时间日期工具类（静态方法）。"""

    DEFAULT_FMT = DEFAULT_FMT
    DATE_FMT = DATE_FMT

    # ------------------------------------------------------------------ #
    # 当前时间
    # ------------------------------------------------------------------ #
    @staticmethod
    def now() -> datetime:
        """当前本地时间 ``datetime``。"""
        return datetime.now()

    @staticmethod
    def now_str(fmt: str = DEFAULT_FMT) -> str:
        """当前时间格式化字符串。"""
        return datetime.now().strftime(fmt)

    @staticmethod
    def timestamp(ms: bool = False) -> int:
        """当前 Unix 时间戳，``ms=True`` 返回毫秒。"""
        t = time.time()
        return int(t * 1000) if ms else int(t)

    # ------------------------------------------------------------------ #
    # 互转
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_datetime(value: DateLike, fmt: str = DEFAULT_FMT) -> datetime:
        """任意常见类型 -> ``datetime``。支持字符串、时间戳（秒/毫秒）、datetime。"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            # 大于 1e12 视为毫秒
            ts = value / 1000 if value > 1e12 else value
            return datetime.fromtimestamp(ts)
        if isinstance(value, str):
            return datetime.strptime(value, fmt)
        raise TypeError(f"无法转换为 datetime: {value!r}")

    @staticmethod
    def to_str(value: DateLike, fmt: str = DEFAULT_FMT) -> str:
        """任意常见类型 -> 格式化字符串。"""
        return DateTimeHelper.to_datetime(value, fmt).strftime(fmt)

    @staticmethod
    def to_timestamp(value: DateLike, fmt: str = DEFAULT_FMT, ms: bool = False) -> int:
        """任意常见类型 -> Unix 时间戳。"""
        dt = DateTimeHelper.to_datetime(value, fmt)
        t = dt.timestamp()
        return int(t * 1000) if ms else int(t)

    @staticmethod
    def from_timestamp(ts: Union[int, float], fmt: Optional[str] = DEFAULT_FMT) -> Union[str, datetime]:
        """时间戳（秒/毫秒） -> 字符串（给 fmt）或 datetime（fmt=None）。"""
        ts = ts / 1000 if ts > 1e12 else ts
        dt = datetime.fromtimestamp(ts)
        return dt.strftime(fmt) if fmt else dt

    # ------------------------------------------------------------------ #
    # 时区
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_utc(value: DateLike, fmt: str = DEFAULT_FMT) -> datetime:
        """本地时间 -> 带时区的 UTC ``datetime``。"""
        dt = DateTimeHelper.to_datetime(value, fmt)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def utc_now_str(fmt: str = DEFAULT_FMT) -> str:
        """当前 UTC 时间字符串。"""
        return datetime.now(timezone.utc).strftime(fmt)

    # ------------------------------------------------------------------ #
    # 加减 / 相对时间
    # ------------------------------------------------------------------ #
    @staticmethod
    def shift(value: DateLike = None, *, days=0, hours=0, minutes=0, seconds=0,
              fmt: str = DEFAULT_FMT) -> datetime:
        """在给定时间上加减偏移；``value`` 省略则以当前时间为基准。"""
        base = DateTimeHelper.to_datetime(value, fmt) if value is not None else datetime.now()
        return base + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    @staticmethod
    def diff_seconds(a: DateLike, b: DateLike, fmt: str = DEFAULT_FMT) -> float:
        """两个时间相差的秒数（a - b）。"""
        return (DateTimeHelper.to_datetime(a, fmt) - DateTimeHelper.to_datetime(b, fmt)).total_seconds()

    @staticmethod
    def humanize(value: DateLike, fmt: str = DEFAULT_FMT) -> str:
        """相对当前时间的人性化描述，如 “3分钟前”“2小时后”。"""
        delta = DateTimeHelper.to_datetime(value, fmt) - datetime.now()
        sec = delta.total_seconds()
        future = sec > 0
        sec = abs(sec)
        for limit, unit, div in ((60, "秒", 1), (3600, "分钟", 60),
                                 (86400, "小时", 3600), (2592000, "天", 86400)):
            if sec < limit:
                n = int(sec / div)
                return f"{n}{unit}{'后' if future else '前'}"
        return f"{int(sec / 2592000)}个月{'后' if future else '前'}"

    # ------------------------------------------------------------------ #
    # 区间：当天 / 本周 / 本月
    # ------------------------------------------------------------------ #
    @staticmethod
    def day_range(value: DateLike = None, fmt: Optional[str] = DEFAULT_FMT) -> Tuple:
        """某天的 (00:00:00, 23:59:59)；value 省略为今天。"""
        d = (DateTimeHelper.to_datetime(value, fmt) if value is not None else datetime.now())
        start = d.replace(hour=0, minute=0, second=0, microsecond=0)
        end = d.replace(hour=23, minute=59, second=59, microsecond=0)
        return (start.strftime(fmt), end.strftime(fmt)) if fmt else (start, end)

    @staticmethod
    def week_range(value: DateLike = None, fmt: Optional[str] = DEFAULT_FMT) -> Tuple:
        """本周一 00:00:00 ~ 本周日 23:59:59。"""
        d = (DateTimeHelper.to_datetime(value, fmt) if value is not None else datetime.now())
        monday = d - timedelta(days=d.weekday())
        start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59)
        return (start.strftime(fmt), end.strftime(fmt)) if fmt else (start, end)

    @staticmethod
    def month_range(value: DateLike = None, fmt: Optional[str] = DEFAULT_FMT) -> Tuple:
        """本月 1 号 00:00:00 ~ 月末 23:59:59。"""
        d = (DateTimeHelper.to_datetime(value, fmt) if value is not None else datetime.now())
        start = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if d.month == 12:
            nxt = start.replace(year=d.year + 1, month=1)
        else:
            nxt = start.replace(month=d.month + 1)
        end = (nxt - timedelta(seconds=1))
        return (start.strftime(fmt), end.strftime(fmt)) if fmt else (start, end)

    # ------------------------------------------------------------------ #
    # 计时器
    # ------------------------------------------------------------------ #
    class Timer:
        """上下文计时器，统计代码块耗时（秒）。

            with DateTimeHelper.Timer() as t:
                ...
            print(t.elapsed)   # 0.123
        """

        def __init__(self):
            self.elapsed = 0.0
            self._start = 0.0

        def __enter__(self) -> "DateTimeHelper.Timer":
            self._start = time.perf_counter()
            return self

        def __exit__(self, *exc) -> None:
            self.elapsed = time.perf_counter() - self._start


__all__ = ["DateTimeHelper"]
