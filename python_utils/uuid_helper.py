# -*- coding: utf-8 -*-
"""UUID 生成操作类。

对 Python 内置 ``uuid`` 做一层易用封装，覆盖常见场景：

* ``uuid4`` 随机（最常用，默认）；
* ``uuid1`` 基于时间 + MAC；
* ``uuid3`` / ``uuid5`` 基于命名空间（同样输入永远得到同样 UUID，可幂等）；
* ``hex`` 去横杠形式，适合做数据库主键 / 文件名；
* ``short`` 短 UUID（base62 压缩，22 位左右），适合短链、订单号；
* ``ordered`` 时间有序 UUID，趋势递增，对数据库聚簇索引更友好；
* ``is_valid`` 校验字符串是否为合法 UUID。

全部为静态方法，直接类名调用，无需实例化::

    from python_utils import UUIDHelper

    UUIDHelper.uuid4()            # '3f2504e0-4f89-41d3-9a0c-0305e82c3301'
    UUIDHelper.hex()              # '3f2504e04f8941d39a0c0305e82c3301'
    UUIDHelper.short()            # '7Ncbtl2gU4iZ4y5ay2b9pS'
    UUIDHelper.uuid5('user:123') # 同一输入恒定输出，可用于幂等键
"""

from __future__ import annotations

import uuid
from typing import Union

# base62 字符表，用于短 UUID 编码
_BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


class UUIDHelper:
    """UUID 生成与处理工具类（全部为静态方法）。"""

    # ------------------------------------------------------------------ #
    # 标准 UUID
    # ------------------------------------------------------------------ #
    @staticmethod
    def uuid4() -> str:
        """随机 UUID（v4）。最常用，无隐私泄露风险，推荐默认使用。"""
        return str(uuid.uuid4())

    @staticmethod
    def uuid1() -> str:
        """基于时间戳 + MAC 地址的 UUID（v1）。

        趋势有序，但包含机器 MAC，可能泄露信息，对外场景慎用。
        """
        return str(uuid.uuid1())

    @staticmethod
    def uuid3(name: str, namespace: uuid.UUID = uuid.NAMESPACE_DNS) -> str:
        """基于命名空间 + 名称的 UUID（v3，MD5）。相同输入恒定输出。"""
        return str(uuid.uuid3(namespace, name))

    @staticmethod
    def uuid5(name: str, namespace: uuid.UUID = uuid.NAMESPACE_DNS) -> str:
        """基于命名空间 + 名称的 UUID（v5，SHA1）。相同输入恒定输出。

        比 v3 更推荐，常用于把业务键（如 ``"user:123"``）映射为稳定 UUID，
        实现幂等去重。
        """
        return str(uuid.uuid5(namespace, name))

    # ------------------------------------------------------------------ #
    # 变形：去横杠 / 大写 / 字节
    # ------------------------------------------------------------------ #
    @staticmethod
    def hex(upper: bool = False) -> str:
        """无横杠的 32 位十六进制字符串，适合做主键、文件名。"""
        h = uuid.uuid4().hex
        return h.upper() if upper else h

    @staticmethod
    def uuid4_bytes() -> bytes:
        """16 字节的 UUID，适合存 ``BINARY(16)`` 列，最省空间。"""
        return uuid.uuid4().bytes

    # ------------------------------------------------------------------ #
    # 短 UUID（base62 压缩）
    # ------------------------------------------------------------------ #
    @staticmethod
    def short() -> str:
        """短 UUID：把 128 位随机数用 base62 编码，约 22 位，无横杠。

        长度更短、URL 安全，适合短链接、邀请码、可见订单号等。
        """
        num = uuid.uuid4().int
        if num == 0:
            return _BASE62[0]
        chars = []
        base = len(_BASE62)
        while num > 0:
            num, rem = divmod(num, base)
            chars.append(_BASE62[rem])
        return "".join(reversed(chars))

    # ------------------------------------------------------------------ #
    # 时间有序 UUID（对数据库索引更友好）
    # ------------------------------------------------------------------ #
    @staticmethod
    def ordered() -> str:
        """时间有序 UUID：把 uuid1 的时间片重排到高位，使其整体趋势递增。

        作为数据库主键时，趋势递增可减少 B+ 树页分裂，写入更友好
        （类似 “COMB UUID” 思路）。格式仍是标准 36 位 UUID 字符串。
        """
        u = uuid.uuid1()
        # uuid1 的 time_low / time_mid / time_hi 顺序是低位在前，
        # 重排为 高位在前，得到按时间递增的 16 字节。
        fields = u.fields  # (time_low, time_mid, time_hi_version, clock_seq_hi, clock_seq_low, node)
        time_low, time_mid, time_hi_version = fields[0], fields[1], fields[2]
        rest = u.int & ((1 << 64) - 1)  # 低 64 位（clock_seq + node）保持不变
        reordered = (time_hi_version << 112) | (time_mid << 96) | (time_low << 64) | rest
        return str(uuid.UUID(int=reordered))

    # ------------------------------------------------------------------ #
    # 校验
    # ------------------------------------------------------------------ #
    @staticmethod
    def is_valid(value: Union[str, bytes], version: int = None) -> bool:
        """判断字符串/字节是否为合法 UUID；可选校验具体版本（1/3/4/5）。"""
        try:
            u = uuid.UUID(value) if isinstance(value, str) else uuid.UUID(bytes=value)
        except (ValueError, AttributeError, TypeError):
            return False
        return version is None or u.version == version


__all__ = ["UUIDHelper"]
