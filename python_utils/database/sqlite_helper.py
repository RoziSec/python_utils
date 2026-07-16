# -*- coding: utf-8 -*-
"""SQLite 操作类。

封装了 SQLite 的连接管理与增删改查（CRUD）常用操作，特点：

* 全部使用参数化查询（占位符 ``?``），从根本上避免 SQL 注入；
* 支持 ``with`` 上下文管理，自动提交/回滚并关闭连接；
* 查询结果以 ``dict`` 形式返回，字段名即为键，使用更直观；
* 提供 execute / executemany / 事务等底层能力，便于扩展。

依赖：Python 内置的 ``sqlite3``，无需额外安装。
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

# 一条 SQL 的参数，可以是位置参数序列，也可以是命名参数字典
Params = Union[Sequence[Any], Dict[str, Any], None]


class SQLiteHelper:
    """SQLite 数据库操作助手。

    示例::

        with SQLiteHelper("demo.db") as db:
            db.execute(CREATE_TABLE_SQL)
            db.insert("users", {"name": "张三", "age": 20})
            rows = db.query("SELECT * FROM users WHERE age > ?", (18,))
    """

    def __init__(self, db_path: str = ":memory:", timeout: float = 5.0):
        """初始化。

        :param db_path: 数据库文件路径；``:memory:`` 表示内存数据库。
        :param timeout: 获取锁的超时时间（秒）。
        """
        self.db_path = db_path
        self.timeout = timeout
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------ #
    # 连接管理
    # ------------------------------------------------------------------ #
    def connect(self) -> "SQLiteHelper":
        """建立连接（若已连接则复用）。"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            # 让查询结果可以按列名访问
            self._conn.row_factory = sqlite3.Row
            # 开启外键约束（SQLite 默认关闭）
            self._conn.execute("PRAGMA foreign_keys = ON;")
        return self

    def close(self) -> None:
        """关闭连接。"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        """返回底层连接对象，未连接时自动连接。"""
        if self._conn is None:
            self.connect()
        assert self._conn is not None
        return self._conn

    # 上下文管理：with 进入自动连接，退出自动提交/回滚并关闭
    def __enter__(self) -> "SQLiteHelper":
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
    def execute(self, sql: str, params: Params = None, *, commit: bool = True) -> sqlite3.Cursor:
        """执行单条 SQL（增、删、改、建表等）。

        :param sql: SQL 语句，使用 ``?`` 或 ``:name`` 占位。
        :param params: 与占位符对应的参数。
        :param commit: 是否立即提交，处于事务批处理时可置 ``False``。
        :return: 游标对象，可读取 ``rowcount`` / ``lastrowid``。
        """
        cur = self.conn.execute(sql, params or ())
        if commit:
            self.conn.commit()
        return cur

    def executemany(self, sql: str, seq_of_params: Iterable[Params], *, commit: bool = True) -> sqlite3.Cursor:
        """批量执行同一条 SQL（如批量插入）。"""
        cur = self.conn.executemany(sql, seq_of_params)
        if commit:
            self.conn.commit()
        return cur

    # ------------------------------------------------------------------ #
    # 查（Read）
    # ------------------------------------------------------------------ #
    def query(self, sql: str, params: Params = None) -> List[Dict[str, Any]]:
        """查询多行，返回字典列表。"""
        cur = self.conn.execute(sql, params or ())
        return [dict(row) for row in cur.fetchall()]

    def query_one(self, sql: str, params: Params = None) -> Optional[Dict[str, Any]]:
        """查询单行，无结果返回 ``None``。"""
        cur = self.conn.execute(sql, params or ())
        row = cur.fetchone()
        return dict(row) if row is not None else None

    def query_value(self, sql: str, params: Params = None) -> Any:
        """查询单个标量值（如 ``COUNT(*)``），无结果返回 ``None``。"""
        cur = self.conn.execute(sql, params or ())
        row = cur.fetchone()
        return row[0] if row is not None else None

    # ------------------------------------------------------------------ #
    # 增（Create）
    # ------------------------------------------------------------------ #
    def insert(self, table: str, data: Dict[str, Any], *, commit: bool = True) -> int:
        """插入一行，返回新行的自增主键 ``lastrowid``。

        :param table: 表名。
        :param data: 列名 -> 值 的字典。
        """
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        cur = self.execute(sql, tuple(data.values()), commit=commit)
        return cur.lastrowid

    def insert_many(self, table: str, rows: List[Dict[str, Any]], *, commit: bool = True) -> int:
        """批量插入，返回受影响的行数。要求每行的列一致。"""
        if not rows:
            return 0
        cols = list(rows[0].keys())
        col_str = ", ".join(cols)
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"
        seq = [tuple(row[c] for c in cols) for row in rows]
        cur = self.executemany(sql, seq, commit=commit)
        return cur.rowcount

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

        :param data: 需要更新的 列名 -> 新值。
        :param where: WHERE 条件（不含 ``WHERE`` 关键字），如 ``"id = ?"``。
        :param where_params: WHERE 条件中占位符的参数。
        """
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = list(data.values()) + list(where_params or [])
        cur = self.execute(sql, params, commit=commit)
        return cur.rowcount

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
        sql = f"DELETE FROM {table} WHERE {where}"
        cur = self.execute(sql, where_params, commit=commit)
        return cur.rowcount

    # ------------------------------------------------------------------ #
    # 事务
    # ------------------------------------------------------------------ #
    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()
