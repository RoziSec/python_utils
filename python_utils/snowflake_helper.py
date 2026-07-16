# -*- coding: utf-8 -*-
"""雪花算法（Snowflake）分布式 ID 生成类。

生成 64 位、趋势递增的**纯数字**唯一 ID，相比 UUID 更短、有序、对数据库
索引更友好，适合做分布式主键、订单号等。结构（共 63 位有效）：

    1 位符号(恒 0) | 41 位毫秒时间戳 | 5 位数据中心 | 5 位机器 | 12 位序列号

* 41 位时间戳可用约 69 年；
* 10 位机器位支持 1024 个节点；
* 12 位序列号支持单节点单毫秒内 4096 个 ID。

线程安全，并处理了时钟回拨。纯标准库实现。

    from python_utils import SnowflakeHelper

    sf = SnowflakeHelper(datacenter_id=1, worker_id=1)
    sf.next_id()      # 例如 189273456789012345
"""

from __future__ import annotations

import threading
import time


class SnowflakeHelper:
    """雪花 ID 生成器（线程安全）。"""

    # 各段位数
    _WORKER_BITS = 5
    _DATACENTER_BITS = 5
    _SEQUENCE_BITS = 12

    _MAX_WORKER = (1 << _WORKER_BITS) - 1          # 31
    _MAX_DATACENTER = (1 << _DATACENTER_BITS) - 1  # 31
    _SEQUENCE_MASK = (1 << _SEQUENCE_BITS) - 1      # 4095

    # 各段左移量
    _WORKER_SHIFT = _SEQUENCE_BITS
    _DATACENTER_SHIFT = _SEQUENCE_BITS + _WORKER_BITS
    _TIMESTAMP_SHIFT = _SEQUENCE_BITS + _WORKER_BITS + _DATACENTER_BITS

    def __init__(self, datacenter_id: int = 0, worker_id: int = 0, epoch: int = 1704067200000):
        """
        :param datacenter_id: 数据中心编号 0~31。
        :param worker_id: 机器编号 0~31。
        :param epoch: 起始纪元（毫秒），默认 2024-01-01。不应晚于当前时间。
        """
        if not 0 <= datacenter_id <= self._MAX_DATACENTER:
            raise ValueError(f"datacenter_id 需在 0~{self._MAX_DATACENTER}")
        if not 0 <= worker_id <= self._MAX_WORKER:
            raise ValueError(f"worker_id 需在 0~{self._MAX_WORKER}")
        self.datacenter_id = datacenter_id
        self.worker_id = worker_id
        self.epoch = epoch
        self._sequence = 0
        self._last_ts = -1
        self._lock = threading.Lock()

    @staticmethod
    def _now() -> int:
        return int(time.time() * 1000)

    def _wait_next_ms(self, last_ts: int) -> int:
        ts = self._now()
        while ts <= last_ts:
            ts = self._now()
        return ts

    def next_id(self) -> int:
        """生成下一个唯一 ID（线程安全）。"""
        with self._lock:
            ts = self._now()
            if ts < self._last_ts:
                # 时钟回拨：等待追回，避免生成重复 ID
                ts = self._wait_next_ms(self._last_ts)
            if ts == self._last_ts:
                # 同一毫秒内自增序列
                self._sequence = (self._sequence + 1) & self._SEQUENCE_MASK
                if self._sequence == 0:
                    # 序列耗尽，等到下一毫秒
                    ts = self._wait_next_ms(self._last_ts)
            else:
                self._sequence = 0
            self._last_ts = ts
            return (
                ((ts - self.epoch) << self._TIMESTAMP_SHIFT)
                | (self.datacenter_id << self._DATACENTER_SHIFT)
                | (self.worker_id << self._WORKER_SHIFT)
                | self._sequence
            )

    def next_id_str(self) -> str:
        """返回字符串形式的 ID。"""
        return str(self.next_id())


__all__ = ["SnowflakeHelper"]
