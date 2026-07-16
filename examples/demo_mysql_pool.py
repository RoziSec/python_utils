# -*- coding: utf-8 -*-
"""MySQLPoolHelper（连接池版）使用示例。

前置：
    1. pip install PyMySQL DBUtils
    2. 本地有可用 MySQL，并已建库： CREATE DATABASE test DEFAULT CHARSET utf8mb4;
    3. 根据实际情况修改连接参数。

运行：
    cd E:/Code/python_utils
    python -m examples.demo_mysql_pool
"""

import threading

from python_utils import MySQLPoolHelper

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
    # 进程内创建一次连接池，全局复用
    pool = MySQLPoolHelper(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="123456",     # ← 改成你自己的密码
        database="test",
        max_connections=10,    # 池最大连接数
        min_cached=2,          # 预建 2 个空闲连接
    )

    # 建表 + 清空历史
    pool.execute(CREATE_TABLE_SQL)
    pool.delete("users", where="1=1")

    # ---- 单条操作：每次自动借还连接、自动提交 ----
    pool.insert("users", {"name": "张三", "age": 20, "email": "zhang@a.com"})
    pool.insert_many("users", [
        {"name": "李四", "age": 25, "email": "li@a.com"},
        {"name": "王五", "age": 30, "email": "wang@a.com"},
    ])
    print("总人数:", pool.query_value("SELECT COUNT(*) FROM users"))

    # ---- 事务：多条操作复用同一连接，异常自动回滚 ----
    with pool.transaction() as tx:
        tx.insert("users", {"name": "赵六", "age": 28, "email": "zhao@a.com"})
        tx.update("users", {"age": 21}, where="name = %s", where_params=("张三",))
    print("事务后:", pool.query("SELECT name, age FROM users ORDER BY id"))

    # ---- 多线程并发验证连接池线程安全 ----
    def worker(i):
        pool.query("SELECT * FROM users WHERE age > %s", (18,))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print("20 个线程并发查询完成，连接池工作正常。")

    pool.close()


if __name__ == "__main__":
    main()
