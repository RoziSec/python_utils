-- ============================================================================
-- 测试用 SQL 语句示例
-- 说明：
--   * SQLite 与 MySQL 语法大体相同，差异处已在下方分别标注。
--   * 代码中请使用参数化占位符：SQLite 用 ?，MySQL 用 %s，切勿手动拼接字符串。
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 一、建表（DDL）
-- ----------------------------------------------------------------------------

-- SQLite 版本：自增主键用 INTEGER PRIMARY KEY AUTOINCREMENT
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    age        INTEGER DEFAULT 0,
    email      TEXT    UNIQUE,
    created_at TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- MySQL 版本：自增主键用 AUTO_INCREMENT，注意字符集
-- CREATE TABLE IF NOT EXISTS users (
--     id         INT          PRIMARY KEY AUTO_INCREMENT,
--     name       VARCHAR(64)  NOT NULL,
--     age        INT          DEFAULT 0,
--     email      VARCHAR(128) UNIQUE,
--     created_at DATETIME     DEFAULT CURRENT_TIMESTAMP
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ----------------------------------------------------------------------------
-- 二、增（INSERT）
-- ----------------------------------------------------------------------------

-- 单行插入（SQLite）
INSERT INTO users (name, age, email) VALUES (?, ?, ?);
-- 单行插入（MySQL）
-- INSERT INTO users (name, age, email) VALUES (%s, %s, %s);

-- 批量插入（配合 executemany / insert_many 使用同一条 SQL，多组参数）
INSERT INTO users (name, age, email) VALUES (?, ?, ?);


-- ----------------------------------------------------------------------------
-- 三、查（SELECT）
-- ----------------------------------------------------------------------------

-- 查全部
SELECT * FROM users;

-- 条件查询
SELECT id, name, age FROM users WHERE age > ?;

-- 模糊查询
SELECT * FROM users WHERE name LIKE ?;          -- 参数示例： '%张%'

-- 排序 + 分页（SQLite / MySQL 均支持 LIMIT ... OFFSET ...）
SELECT * FROM users ORDER BY age DESC LIMIT ? OFFSET ?;

-- 聚合统计
SELECT COUNT(*)      AS total   FROM users;
SELECT age, COUNT(*) AS cnt     FROM users GROUP BY age HAVING COUNT(*) >= ?;

-- 多条件
SELECT * FROM users WHERE age BETWEEN ? AND ? AND email IS NOT NULL;


-- ----------------------------------------------------------------------------
-- 四、改（UPDATE）
-- ----------------------------------------------------------------------------

-- 按主键更新
UPDATE users SET age = ? WHERE id = ?;

-- 多字段更新
UPDATE users SET name = ?, email = ? WHERE id = ?;


-- ----------------------------------------------------------------------------
-- 五、删（DELETE）
-- ----------------------------------------------------------------------------

-- 按条件删除
DELETE FROM users WHERE id = ?;

-- 按范围删除
DELETE FROM users WHERE age < ?;


-- ----------------------------------------------------------------------------
-- 六、清理（测试收尾）
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS users;
