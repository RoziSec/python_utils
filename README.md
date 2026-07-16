# python_utils

常用 Python 操作类封装，可直接复制到其他项目中使用。包含：

- **数据库模块** (`python_utils.database`)：`SQLiteHelper`、`MySQLHelper`、`MySQLPoolHelper`（连接池版），实现完整增删改查。
- **日志模块** (`python_utils.logger`)：基于 loguru，不输出终端、按文件大小滚动、按等级分文件、可追溯到模块与行号。
- **其它常用工具类**：ID 生成、时间日期、配置读取、文件、加密、缓存/重试、HTTP、Redis、Excel、邮件、并发池。

> 所有工具类都可 `from python_utils import XxxHelper` 直接导入。依赖第三方库的类均为**延迟导入**，只有真正用到时才需安装对应依赖。

## 工具类一览

| 类 | 说明 | 依赖 |
| --- | --- | --- |
| `SQLiteHelper` | SQLite 增删改查 | 标准库 |
| `MySQLHelper` / `MySQLPoolHelper` | MySQL 单连接 / 连接池 | PyMySQL(+DBUtils) |
| `get_logger` / `setup_logger` | loguru 日志 | loguru |
| `UUIDHelper` | UUID（v1/3/4/5、hex、short、有序、校验） | 标准库 |
| `SnowflakeHelper` | 雪花算法分布式 ID（纯数字、有序） | 标准库 |
| `DateTimeHelper` | 时间戳/字符串/datetime 互转、时区、区间、计时器 | 标准库 |
| `ConfigHelper` | 读取 env/json/yaml/ini、环境变量覆盖、类型转换 | 标准库(YAML 需 pyyaml) |
| `FileHelper` | 文本/JSON/CSV 读写、遍历、hash、压缩、安全删除 | 标准库 |
| `CryptoHelper` | md5/sha/hmac/base64、密码加盐哈希、AES | 标准库(AES 需 pycryptodome) |
| `CacheHelper` / `@cache` / `@retry` | 内存 TTL+LRU 缓存、结果缓存、失败重试 | 标准库 |
| `HttpHelper` | requests 封装：超时、重试、session、JSON | requests |
| `RedisHelper` | string/hash/list/set、分布式锁 | redis |
| `ExcelHelper` | xlsx 读写（字典列表 ↔ 工作表、多 sheet） | openpyxl |
| `EmailHelper` | SMTP 发信：HTML、附件、抄送、SSL/TLS | 标准库 |
| `PoolHelper` | 线程/进程池并发 map | 标准库 |

### 简单示例

```python
from python_utils import (
    UUIDHelper, SnowflakeHelper, DateTimeHelper, ConfigHelper,
    FileHelper, CryptoHelper, CacheHelper, cache, retry,
    HttpHelper, RedisHelper, ExcelHelper, EmailHelper, PoolHelper,
)

UUIDHelper.uuid4()
SnowflakeHelper(1, 1).next_id()
DateTimeHelper.day_range()                     # 今天起止
cfg = ConfigHelper("config.yaml"); cfg.get_int("db.port", 3306)
FileHelper.write_json("a.json", {"x": 1})
CryptoHelper.verify_password("123456", CryptoHelper.hash_password("123456"))

@cache(ttl=30)
def load(uid): ...

@retry(times=3, delay=0.5, backoff=2.0)
def call_api(): ...

PoolHelper.map(str, range(10), max_workers=4)  # 并发
```

## 目录结构

```
python_utils/
├── python_utils/
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── sqlite_helper.py     # SQLite 操作类
│   │   ├── mysql_helper.py      # MySQL 操作类（单连接）
│   │   └── mysql_pool_helper.py # MySQL 操作类（连接池版）
│   ├── uuid_helper.py           # UUID 生成
│   ├── snowflake_helper.py      # 雪花算法分布式 ID
│   ├── datetime_helper.py       # 时间日期
│   ├── config_helper.py         # 配置读取
│   ├── file_helper.py           # 文件路径
│   ├── crypto_helper.py         # 加密编码
│   ├── cache_helper.py          # 缓存 + @cache + @retry
│   ├── http_helper.py           # HTTP 请求
│   ├── redis_helper.py          # Redis 操作
│   ├── excel_helper.py          # Excel 读写
│   ├── email_helper.py          # SMTP 邮件
│   ├── pool_helper.py           # 线程/进程池
│   └── logger/
│       ├── __init__.py
│       └── log_helper.py        # loguru 日志封装
├── examples/
│   ├── sql_examples.sql         # 测试用 SQL 语句示例
│   ├── demo_sqlite.py           # SQLite 增删改查演示
│   ├── demo_mysql.py            # MySQL 增删改查演示
│   ├── demo_mysql_pool.py       # MySQL 连接池演示
│   └── demo_logger.py           # 日志演示
├── requirements.txt
└── README.md
```

## 安装依赖

```bash
pip install -r requirements.txt
```

> SQLite 使用 Python 内置 `sqlite3`，无需额外安装；仅 MySQL 需要 `PyMySQL`。

## 快速上手

### SQLite

```python
from python_utils import SQLiteHelper

with SQLiteHelper("demo.db") as db:          # 上下文自动提交/回滚/关闭
    db.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, age INT)")
    uid = db.insert("users", {"name": "张三", "age": 20})   # 增
    db.update("users", {"age": 21}, where="id = ?", where_params=(uid,))  # 改
    rows = db.query("SELECT * FROM users WHERE age > ?", (18,))           # 查
    db.delete("users", where="id = ?", where_params=(uid,))              # 删
```

### MySQL

```python
from python_utils import MySQLHelper

db = MySQLHelper(host="127.0.0.1", user="root", password="123456", database="test")
with db:
    db.insert("users", {"name": "李四", "age": 22})          # 占位符内部用 %s
    rows = db.query("SELECT * FROM users WHERE age > %s", (18,))
```

两个类的方法签名一致，区别仅在于 SQL 占位符：**SQLite 用 `?`，MySQL 用 `%s`**。

### MySQL 连接池版（多线程 / Web 服务推荐）

`MySQLPoolHelper` 基于 `DBUtils.PooledDB`，API 与 `MySQLHelper` 完全一致，可无缝替换。
进程内创建一次、全局复用，每次操作自动从池中借还连接，线程安全并自动保活。

```python
from python_utils import MySQLPoolHelper

pool = MySQLPoolHelper(host="127.0.0.1", user="root", password="123456",
                       database="test", max_connections=10)

pool.insert("users", {"name": "赵六", "age": 28})            # 单条：自动借还+提交
rows = pool.query("SELECT * FROM users WHERE age > %s", (18,))

with pool.transaction() as tx:      # 事务：多条操作复用同一连接，异常自动回滚
    tx.insert("users", {"name": "钱七", "age": 31})
    tx.update("users", {"age": 32}, where="name = %s", where_params=("钱七",))
```

| 场景 | 推荐 |
| --- | --- |
| 脚本、单线程、低频操作 | `MySQLHelper` |
| 多线程、Web 服务、高频短查询 | `MySQLPoolHelper` |

常用方法：`execute` / `executemany` / `query` / `query_one` / `query_value` /
`insert` / `insert_many` / `update` / `delete` / `commit` / `rollback`。

### 日志

```python
from python_utils.logger import setup_logger, get_logger

setup_logger(log_dir="logs", rotation="10 MB", retention="30 days")  # 入口处配置一次
log = get_logger()
log.info("服务启动")
log.error("出错啦")
```

特性说明：

| 需求 | 实现 |
| --- | --- |
| 不打印到终端 | 初始化时 `logger.remove()` 移除默认控制台 handler（`console=True` 可临时开启） |
| 按固定大小定期存储 | `rotation="10 MB"` 写满即切割，`retention` 定期清理，`compression` 压缩旧文件 |
| 追溯到模块与行号 | 日志格式含 `{name}:{function}:{line}` |
| 按等级分文件 | `debug.log`/`info.log`/`warning.log`/`error.log`/`critical.log` 各存对应等级，另有 `all.log` 汇总 |

## 运行示例

```bash
cd E:/Code/python_utils
python -m examples.demo_all        # ★ 综合示例：一次演示所有工具类，直接可跑
python -m examples.demo_sqlite     # SQLite 增删改查
python -m examples.demo_logger     # 日志，输出到 examples/logs
python -m examples.demo_mysql      # MySQL（需先配置好数据库与连接参数）
python -m examples.demo_mysql_pool # MySQL 连接池
```

推荐先跑 `demo_all.py` —— 它把每个类的典型用法都演示了一遍，纯本地能跑的
（SQLite/日志/UUID/雪花/时间/配置/文件/加密/缓存/重试/并发池/Excel）会真实
执行并打印结果，需要外部服务的（MySQL/Redis/邮件/HTTP）会自动跳过。

测试用 SQL 语句见 [`examples/sql_examples.sql`](examples/sql_examples.sql)。
