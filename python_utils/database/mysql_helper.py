# -*- coding: utf-8 -*-
"""MySQL 操作类。

基于 ``PyMySQL`` 封装 MySQL 的连接管理与增删改查（CRUD），特点：

* 全部使用参数化查询（占位符 ``%s``），避免 SQL 注入；
* 支持 ``with`` 上下文管理，自动提交/回滚并关闭连接；
* 内置断线自动重连（``ping``），长连接更稳定；
* 查询结果以 ``dict`` 形式返回（``DictCursor``）。

依赖：``pip install PyMySQL``。

注意：MySQL 占位符统一使用 ``%s``（无论字段是什么类型都用 ``%s``，
不要写成 ``%d``），命名参数用 ``%(name)s``。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

# 延迟导入 pymysql：只有真正使用 MySQL 时才需要安装，
# 这样仅用 SQLite 的项目无需安装 PyMySQL 也能正常 import。
try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:  # pragma: no cover
    pymysql = None
    DictCursor = None

Params = Union[Sequence[Any], Dict[str, Any], None]


def _require_pymysql():
    if pymysql is None:
        raise ImportError("使用 MySQLHelper 需要先安装依赖：pip install PyMySQL")


class MySQLHelper:
    """MySQL 数据库操作助手。

    示例::

        db = MySQLHelper(host="127.0.0.1", user="root",
                         password="123456", database="test")
        with db:
            db.insert("users", {"name": "李四", "age": 22})
            rows = db.query("SELECT * FROM users WHERE age > %s", (18,))
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: Optional[str] = None,
        charset: str = "utf8mb4",
        autocommit: bool = False,
        connect_timeout: int = 10,
    ):
        """初始化连接参数（此时并不会真正连接）。"""
        _require_pymysql()
        self._config = dict(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
            autocommit=autocommit,
            connect_timeout=connect_timeout,
            cursorclass=DictCursor,  # 让 fetch 结果为 dict
        )
        self._conn: Optional[pymysql.connections.Connection] = None

    # ------------------------------------------------------------------ #
    # 连接管理
    # ------------------------------------------------------------------ #
    def connect(self) -> "MySQLHelper":
        """建立连接（若已连接则复用）。"""
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(**self._config)
        return self

    def close(self) -> None:
        """关闭连接。"""
        if self._conn is not None and self._conn.open:
            self._conn.close()
        self._conn = None

    @property
    def conn(self) -> pymysql.connections.Connection:
        """返回底层连接，未连接时自动连接，断线时自动重连。"""
        if self._conn is None or not self._conn.open:
            self.connect()
        else:
            # 连接可能因超时被服务端断开，ping 会在需要时自动重连
            self._conn.ping(reconnect=True)
        assert self._conn is not None
        return self._conn

    def __enter__(self) -> "MySQLHelper":
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.close()

    # ------------------------------------------------------------------ #
    # 底层执行
    # ------------------------------------------------------------------ #
    def execute(self, sql: str, params: Params = None, *, commit: bool = True) -> int:
        """执行单条 SQL（增、删、改、DDL 等），返回受影响行数。"""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            if commit:
                self.conn.commit()
            return cur.rowcount

    def executemany(self, sql: str, seq_of_params: Iterable[Params], *, commit: bool = True) -> int:
        """批量执行同一条 SQL，返回受影响行数。"""
        with self.conn.cursor() as cur:
            cur.executemany(sql, seq_of_params)
            if commit:
                self.conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------ #
    # 查（Read）
    # ------------------------------------------------------------------ #
    def query(self, sql: str, params: Params = None) -> List[Dict[str, Any]]:
        """查询多行，返回字典列表。"""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def query_one(self, sql: str, params: Params = None) -> Optional[Dict[str, Any]]:
        """查询单行，无结果返回 ``None``。"""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def query_value(self, sql: str, params: Params = None) -> Any:
        """查询单个标量值（如 ``COUNT(*)``），无结果返回 ``None``。"""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if not row:
                return None
            # DictCursor 下取字典的第一个值
            return next(iter(row.values()))

    # ------------------------------------------------------------------ #
    # 增（Create）
    # ------------------------------------------------------------------ #
    def insert(self, table: str, data: Dict[str, Any], *, commit: bool = True) -> int:
        """插入一行，返回新行的自增主键 ``lastrowid``。"""
        cols = ", ".join(f"`{c}`" for c in data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"
        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(data.values()))
            if commit:
                self.conn.commit()
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
        """更新数据，返回受影响的行数。

        :param where: WHERE 条件（不含 ``WHERE``），如 ``"id = %s"``。
        """
        set_clause = ", ".join(f"`{k}` = %s" for k in data.keys())
        sql = f"UPDATE `{table}` SET {set_clause} WHERE {where}"
        params = list(data.values()) + list(where_params or [])
        return self.execute(sql, params, commit=commit)

    # ------------------------------------------------------------------ #
    # 删（Delete）
    # ------------------------------------------------------------------ #
    def delete(self, table: str, where: str, where_params: Params = None, *, commit: bool = True) -> int:
        """删除数据，返回受影响的行数。

        为避免误删全表，``where`` 不允许为空。若确需清空全表，请显式传入
        ``where="1=1"``。
        """
        if not where or not where.strip():
            raise ValueError("delete 需要 where 条件；如需清空全表请显式传 where='1=1'")
        sql = f"DELETE FROM `{table}` WHERE {where}"
        return self.execute(sql, where_params, commit=commit)

    # ------------------------------------------------------------------ #
    # 事务
    # ------------------------------------------------------------------ #
    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()
