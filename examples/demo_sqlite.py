# -*- coding: utf-8 -*-
"""SQLiteHelper 使用示例：完整跑一遍增删改查。

运行：
    cd E:/Code/python_utils
    python -m examples.demo_sqlite
"""

from python_utils import SQLiteHelper

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    age        INTEGER DEFAULT 0,
    email      TEXT    UNIQUE,
    created_at TEXT    DEFAULT (datetime('now', 'localtime'))
);
"""


def main():
    # 用内存库演示（改成 "demo.db" 即可落地为文件）
    with SQLiteHelper(":memory:") as db:
        # 建表
        db.execute(CREATE_TABLE_SQL)

        # 增：单行
        uid = db.insert("users", {"name": "张三", "age": 20, "email": "zhang@a.com"})
        print("插入张三，新 id =", uid)

        # 增：批量
        n = db.insert_many("users", [
            {"name": "李四", "age": 25, "email": "li@a.com"},
            {"name": "王五", "age": 30, "email": "wang@a.com"},
        ])
        print("批量插入行数 =", n)

        # 查：多行
        print("age > 18:", db.query("SELECT * FROM users WHERE age > ?", (18,)))

        # 查：单行
        print("id=1:", db.query_one("SELECT * FROM users WHERE id = ?", (1,)))

        # 查：标量
        print("总人数:", db.query_value("SELECT COUNT(*) FROM users"))

        # 改
        affected = db.update("users", {"age": 21}, where="name = ?", where_params=("张三",))
        print("更新行数 =", affected, "-> ", db.query_one("SELECT * FROM users WHERE name = ?", ("张三",)))

        # 删
        deleted = db.delete("users", where="age >= ?", where_params=(30,))
        print("删除行数 =", deleted)

        print("最终数据:", db.query("SELECT * FROM users ORDER BY id"))


if __name__ == "__main__":
    main()
