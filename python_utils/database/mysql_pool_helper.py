# -*- coding: utf-8 -*-
"""MySQL 连接池操作类。

基于 ``DBUtils`` 的 ``PooledDB`` + ``PyMySQL`` 实现的**连接池**版本，适合
多线程 / Web 服务 / 高频短查询等场景。相比单连接的 ``MySQLHelper``：

* 连接被复用，避免每次操作都新建 / 销毁连接的开销；
* 线程安全：每个线程从池中借出独立连接，用完自动归还；
* 空闲连接会被自动 ping 保活（``ping=1``），杜绝 “MySQL server has gone away”。

对外方法与 ``MySQLHelper`` 完全一致（execute / query / insert / update /
delete ...），可无缝替换；差异在于内部每次操作都从池借还连接。

依赖：``pip install PyMySQL DBUtils``。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

# 延迟导入：只有真正使用连接池时才要求安装这两个依赖
try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:  # pragma: no cover
    pymysql = None
    DictCursor = None

try:
    from dbutils.pooled_db import PooledDB
except ImportError:  # pragma: no cover
    PooledDB = None

Params = Union[Sequence[Any], Dict[str, Any], None]


def _require_deps():
    missing = []
    if pymysql is None:
        missing.append("PyMySQL")
    if PooledDB is None:
        missing.append("DBUtils")
    if missing:
        raise ImportError(
            "使用 MySQLPoolHelper 需要先安装依赖：pip install " + " ".join(missing)
        )


class MySQLPoolHelper:
    """带连接池的 MySQL 操作助手。

    典型用法（进程内创建一次，全局共享）::

        pool = MySQLPoolHelper(
            host="127.0.0.1", user="root", password="123456", database="test",
            max_connections=10,
        )
        # 单条操作：自动借还连接、自动提交
        pool.insert("users", {"name": "赵六", "age": 28})
        rows = pool.query("SELECT * FROM users WHERE age > %s", (18,))

        # 多条操作放在同一事务中：借用一个连接，异常自动回滚
        with pool.transaction() as tx:
            tx.insert("users", {"name": "钱七", "age": 31})
            tx.update("users", {"age": 32}, where="name = %s", where_params=("钱七",))
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: Optional[str] = None,
        charset: str = "utf8mb4",
        *,
        max_connections: int = 10,
        min_cached: int = 2,
        max_cached: int = 5,
        blocking: bool = True,
        max_usage: Optional[int] = None,
        connect_timeout: int = 10,
    ):
        """创建连接池。

        :param max_connections: 池允许的最大连接数（0/None 表示不限）。
        :param min_cached: 启动时预建并缓存的空闲连接数。
        :param max_cached: 池中最多保留的空闲连接数（超出则关闭）。
        :param blocking: 连接耗尽时是否阻塞等待；``False`` 则直接抛异常。
        :param max_usage: 单个连接最多复用次数，达到后重建；``None`` 表示不限。
        :param connect_timeout: 建立连接的超时时间（秒）。
        """
        _require_deps()
        self._pool = PooledDB(
            creator=pymysql,          # 使用 pymysql 作为底层驱动
            maxconnections=max_connections,
            mincached=min_cached,
            maxcached=max_cached,
            blocking=blocking,
            maxusage=max_usage,
            ping=1,                   # 每次从池取连接时 ping 一下，断线自动重连
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
            connect_timeout=connect_timeout,
            cursorclass=DictCursor,   # fetch 结果为 dict
        )

    def close(self) -> None:
        """关闭整个连接池（进程退出时调用）。"""
        self._pool.close()

    # ------------------------------------------------------------------ #
    # 连接借还
    # ------------------------------------------------------------------ #
    @contextmanager
    def _borrow(self):
        """从池借出一个连接，退出时归还（连接的 close 即归还到池）。"""
        conn = self._pool.connection()
        try:
            yield conn
        finally:
            conn.close()  # 归还到池，并非真正断开

    # ------------------------------------------------------------------ #
    # 底层执行（每次自动借还 + 自动提交）
    # ------------------------------------------------------------------ #
    def execute(self, sql: str, params: Params = None, *, commit: bool = True) -> int:
        """执行单条 SQL（增、删、改、DDL 等），返回受影响行数。"""
        with self._borrow() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if commit:
                    conn.commit()
                return cur.rowcount

    def executemany(self, sql: str, seq_of_params: Iterable[Params], *, commit: bool = True) -> int:
        """批量执行同一条 SQL，返回受影响行数。"""
        with self._borrow() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, seq_of_params)
                if commit:
                    conn.commit()
                return cur.rowcount

    # ------------------------------------------------------------------ #
    # 查（Read）
    # ------------------------------------------------------------------ #
    def query(self, sql: str, params: Params = None) -> List[Dict[str, Any]]:
        """查询多行，返回字典列表。"""
        with self._borrow() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())

    def query_one(self, sql: str, params: Params = None) -> Optional[Dict[str, Any]]:
        """查询单行，无结果返回 ``None``。"""
        with self._borrow() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()

    def query_value(self, sql: str, params: Params = None) -> Any:
        """查询单个标量值（如 ``COUNT(*)``），无结果返回 ``None``。"""
        with self._borrow() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                if not row:
                    return None
                return next(iter(row.values()))

    # ------------------------------------------------------------------ #
    # 增（Create）
    # ------------------------------------------------------------------ #
    def insert(self, table: str, data: Dict[str, Any], *, commit: bool = True) -> int:
        """插入一行，返回新行的自增主键 ``lastrowid``。"""
        cols = ", ".join(f"`{c}`" for c in data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"
        with self._borrow() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(data.values()))
                if commit:
                    conn.commit()
                return cur.lastrowid

    def insert_many(self, table: str, rows: List[Dict[str, Any]], *, commit: bool = True) -> int:
        """批量插入，返回受影响的行数。要求每行的列一致。"""
        if not rows:
            return 0
        cols = list(rows[0].keys())
        col_str = ", ".join(f"`{c}`" for c in cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO `{table}` ({col_str}) VALUES ({placeholders})"
        seq = [tuple(row[c] for c in cols) for row in rows]
        return self.executemany(sql, seq, commit=commit)

    # ------------------------------------------------------------------ #
    # 改（Update）
    # ------------------------------------------------------------------ #
    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: str,
        where_params: Params = None,
        *,
        commit: bool = True,
    ) -> int:
        """更新数据，返回受影响的行数。"""
        set_clause = ", ".join(f"`{k}` = %s" for k in data.keys())
        sql = f"UPDATE `{table}` SET {set_clause} WHERE {where}"
        params = list(data.values()) + list(where_params or [])
        return self.execute(sql, params, commit=commit)

    # ------------------------------------------------------------------ #
    # 删（Delete）
    # ------------------------------------------------------------------ #
    def delete(self, table: str, where: str, where_params: Params = None, *, commit: bool = True) -> int:
        """删除数据，返回受影响的行数。where 不能为空，防止误删全表。"""
        if not where or not where.strip():
            raise ValueError("delete 需要 where 条件；如需清空全表请显式传 where='1=1'")
        sql = f"DELETE FROM `{table}` WHERE {where}"
        return self.execute(sql, where_params, commit=commit)

    # ------------------------------------------------------------------ #
    # 事务：把多条操作绑定到同一个借出的连接上
    # ------------------------------------------------------------------ #
    @contextmanager
    def transaction(self):
        """开启一个事务上下文，内部多条操作复用同一连接。

        正常退出时统一提交，出现异常时自动回滚。``yield`` 出的对象拥有与
        本类一致的 execute / query / insert / update / delete 等方法。
        """
        conn = self._pool.connection()
        bound = _BoundConnection(conn)
        try:
            yield bound
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()  # 归还连接到池


class _BoundConnection:
    """绑定到单个连接的操作代理，供 ``transaction()`` 内部使用。

    与 ``MySQLPoolHelper`` 方法同名，但所有操作都跑在同一连接上且不自动提交，
    由外层 ``transaction()`` 统一 commit / rollback。
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params: Params = None) -> int:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def executemany(self, sql: str, seq_of_params: Iterable[Params]) -> int:
        with self._conn.cursor() as cur:
            cur.executemany(sql, seq_of_params)
            return cur.rowcount

    def query(self, sql: str, params: Params = None) -> List[Dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def query_one(self, sql: str, params: Params = None) -> Optional[Dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def query_value(self, sql: str, params: Params = None) -> Any:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if not row:
                return None
            return next(iter(row.values()))

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        cols = ", ".join(f"`{c}`" for c in data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"
        with self._conn.cursor() as cur:
            cur.execute(sql, tuple(data.values()))
            return cur.lastrowid

    def insert_many(self, table: str, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0
        cols = list(rows[0].keys())
        col_str = ", ".join(f"`{c}`" for c in cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO `{table}` ({col_str}) VALUES ({placeholders})"
        seq = [tuple(row[c] for c in cols) for row in rows]
        return self.executemany(sql, seq)

    def update(self, table: str, data: Dict[str, Any], where: str, where_params: Params = None) -> int:
        set_clause = ", ".join(f"`{k}` = %s" for k in data.keys())
        sql = f"UPDATE `{table}` SET {set_clause} WHERE {where}"
        params = list(data.values()) + list(where_params or [])
        return self.execute(sql, params)

    def delete(self, table: str, where: str, where_params: Params = None) -> int:
        if not where or not where.strip():
            raise ValueError("delete 需要 where 条件；如需清空全表请显式传 where='1=1'")
        sql = f"DELETE FROM `{table}` WHERE {where}"
        return self.execute(sql, where_params)
