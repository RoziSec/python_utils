# -*- coding: utf-8 -*-
"""Redis 操作类。

基于 ``redis-py`` 封装常用数据结构操作与分布式锁，与数据库类同一风格。

* string / hash / list / set 常用命令；
* JSON 便捷读写（``set_json`` / ``get_json``）；
* 基于 ``SET NX EX`` 的分布式锁上下文管理器，释放时用 Lua 脚本校验持有者，
  避免误删他人的锁。

依赖：``pip install redis``（延迟导入，用到才需要）。

    from python_utils import RedisHelper

    r = RedisHelper(host="127.0.0.1", port=6379, db=0)
    r.set("k", "v", ex=60)
    r.hset("user:1", {"name": "张三", "age": 20})
    with r.lock("order:1", timeout=10):
        ...  # 临界区
"""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

# 释放锁的原子 Lua：仅当值等于自己的 token 时才删除
_UNLOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisHelper:
    """Redis 操作工具类。"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        *,
        decode_responses: bool = True,
        **kwargs,
    ):
        if redis is None:
            raise ImportError("使用 RedisHelper 需要先安装：pip install redis")
        self._client = redis.Redis(
            host=host, port=port, db=db, password=password,
            decode_responses=decode_responses, **kwargs,
        )

    @property
    def client(self) -> "redis.Redis":
        """暴露底层 client，需要未封装命令时直接用。"""
        return self._client

    # ------------------------------------------------------------------ #
    # string
    # ------------------------------------------------------------------ #
    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> bool:
        """设置字符串；ex 过期秒数，nx=True 仅当不存在时设置。"""
        return bool(self._client.set(key, value, ex=ex, nx=nx))

    def get(self, key: str) -> Any:
        return self._client.get(key)

    def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """把对象序列化为 JSON 存入。"""
        return bool(self._client.set(key, json.dumps(value, ensure_ascii=False), ex=ex))

    def get_json(self, key: str) -> Any:
        """读取并反序列化 JSON；不存在返回 None。"""
        raw = self._client.get(key)
        return json.loads(raw) if raw is not None else None

    def delete(self, *keys: str) -> int:
        return self._client.delete(*keys)

    def exists(self, key: str) -> bool:
        return bool(self._client.exists(key))

    def expire(self, key: str, seconds: int) -> bool:
        return bool(self._client.expire(key, seconds))

    def incr(self, key: str, amount: int = 1) -> int:
        return self._client.incrby(key, amount)

    # ------------------------------------------------------------------ #
    # hash
    # ------------------------------------------------------------------ #
    def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        return self._client.hset(name, mapping=mapping)

    def hget(self, name: str, key: str) -> Any:
        return self._client.hget(name, key)

    def hgetall(self, name: str) -> Dict[str, Any]:
        return self._client.hgetall(name)

    def hdel(self, name: str, *keys: str) -> int:
        return self._client.hdel(name, *keys)

    # ------------------------------------------------------------------ #
    # list
    # ------------------------------------------------------------------ #
    def lpush(self, name: str, *values: Any) -> int:
        return self._client.lpush(name, *values)

    def rpush(self, name: str, *values: Any) -> int:
        return self._client.rpush(name, *values)

    def lpop(self, name: str) -> Any:
        return self._client.lpop(name)

    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        return self._client.lrange(name, start, end)

    # ------------------------------------------------------------------ #
    # set
    # ------------------------------------------------------------------ #
    def sadd(self, name: str, *values: Any) -> int:
        return self._client.sadd(name, *values)

    def smembers(self, name: str) -> set:
        return self._client.smembers(name)

    def sismember(self, name: str, value: Any) -> bool:
        return bool(self._client.sismember(name, value))

    # ------------------------------------------------------------------ #
    # 分布式锁
    # ------------------------------------------------------------------ #
    @contextmanager
    def lock(self, key: str, timeout: int = 10, blocking: bool = True, retry_interval: float = 0.1):
        """基于 SET NX EX 的分布式锁上下文管理器。

        :param key: 锁的键名。
        :param timeout: 锁自动过期时间（秒），防止持有者崩溃后死锁。
        :param blocking: 获取不到锁时是否自旋等待。
        :param retry_interval: 自旋等待的间隔秒数。
        """
        import time

        lock_key = f"lock:{key}"
        token = uuid.uuid4().hex  # 唯一持有者标识
        acquired = False
        try:
            while True:
                if self._client.set(lock_key, token, nx=True, ex=timeout):
                    acquired = True
                    break
                if not blocking:
                    break
                time.sleep(retry_interval)
            if not acquired:
                raise TimeoutError(f"获取锁失败: {key}")
            yield
        finally:
            if acquired:
                # 原子释放：只删自己持有的锁
                self._client.eval(_UNLOCK_LUA, 1, lock_key, token)

    def close(self) -> None:
        self._client.close()


__all__ = ["RedisHelper"]
