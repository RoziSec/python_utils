# -*- coding: utf-8 -*-
"""MySQLHelper 使用示例：完整跑一遍增删改查。

前置：
    1. pip install PyMySQL
    2. 本地有可用 MySQL，并已创建库： CREATE DATABASE test DEFAULT CHARSET utf8mb4;
    3. 根据实际情况修改下面的连接参数。

运行：
    cd E:/Code/python_utils
    python -m examples.demo_mysql
"""

from python_utils import MySQLHelper

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id         INT          PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(64)  NOT NULL,
    age        INT          DEFAULT 0,
    email      VARCHAR(128) UNIQUE,
    created_at DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def main():
    db = MySQLHelper(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="123456",   # ← 改成你自己的密码
        database="test",
    )

    with db:
        # 建表
        db.execute(CREATE_TABLE_SQL)
        # 清空历史数据，便于反复测试
        db.delete("users", where="1=1")

        # 增：单行（MySQL 占位符是 %s）
        uid = db.insert("users", {"name": "张三", "age": 20, "email": "zhang@a.com"})
        print("插入张三，新 id =", uid)

        # 增：批量
        n = db.insert_many("users", [
            {"name": "李四", "age": 25, "email": "li@a.com"},
            {"name": "王五", "age": 30, "email": "wang@a.com"},
        ])
        print("批量插入行数 =", n)

        # 查
        print("age > 18:", db.query("SELECT * FROM users WHERE age > %s", (18,)))
        print("id 最小的一条:", db.query_one("SELECT * FROM users ORDER BY id LIMIT 1"))
        print("总人数:", db.query_value("SELECT COUNT(*) FROM users"))

        # 改
        affected = db.update("users", {"age": 21}, where="name = %s", where_params=("张三",))
        print("更新行数 =", affected)

        # 删
        deleted = db.delete("users", where="age >= %s", where_params=(30,))
        print("删除行数 =", deleted)

        print("最终数据:", db.query("SELECT * FROM users ORDER BY id"))


if __name__ == "__main__":
    main()
