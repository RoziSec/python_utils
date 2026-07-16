"""python_utils —— 常用 Python 操作类封装。

模块一览：
    database        : SQLite / MySQL(单连接) / MySQL(连接池) 增删改查
    logger          : 基于 loguru 的日志（按大小滚动、按等级分文件）
    uuid_helper     : UUID 生成
    snowflake_helper: 雪花算法分布式 ID
    datetime_helper : 时间日期处理
    config_helper   : 配置读取（env/json/yaml/ini）
    file_helper     : 文件与路径操作
    crypto_helper   : 加密与编码
    cache_helper    : 内存缓存 + @cache + @retry
    http_helper     : HTTP 请求（requests 封装）
    redis_helper    : Redis 操作
    excel_helper    : Excel 读写
    email_helper    : SMTP 邮件发送
    pool_helper     : 线程/进程池并发

说明：依赖第三方库的类（MySQL/Redis/HTTP/Excel/AES 等）均为延迟导入，
只有真正使用到时才需要安装对应依赖，仅用标准库部分无需任何安装。
"""

from .database import SQLiteHelper, MySQLHelper, MySQLPoolHelper
from .logger import get_logger, setup_logger
from .uuid_helper import UUIDHelper
from .snowflake_helper import SnowflakeHelper
from .datetime_helper import DateTimeHelper
from .config_helper import ConfigHelper
from .file_helper import FileHelper
from .crypto_helper import CryptoHelper
from .cache_helper import CacheHelper, cache, retry
from .http_helper import HttpHelper
from .redis_helper import RedisHelper
from .excel_helper import ExcelHelper
from .email_helper import EmailHelper
from .pool_helper import PoolHelper

__all__ = [
    # 数据库
    "SQLiteHelper",
    "MySQLHelper",
    "MySQLPoolHelper",
    # 日志
    "get_logger",
    "setup_logger",
    # ID
    "UUIDHelper",
    "SnowflakeHelper",
    # 常用工具
    "DateTimeHelper",
    "ConfigHelper",
    "FileHelper",
    "CryptoHelper",
    "CacheHelper",
    "cache",
    "retry",
    "HttpHelper",
    "RedisHelper",
    "ExcelHelper",
    "EmailHelper",
    "PoolHelper",
]

__version__ = "1.1.0"
