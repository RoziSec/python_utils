# -*- coding: utf-8 -*-
"""python_utils 综合示例 —— 一次演示所有封装的操作类。

直接运行即可，无需任何外部服务：
    cd E:/Code/python_utils
    python -m examples.demo_all

说明：
* 纯本地能跑的类（SQLite / 日志 / UUID / 雪花 / 时间 / 配置 / 文件 /
  加密 / 缓存 / 重试 / 并发池 / Excel）会真实执行并打印结果；
* 需要外部服务的类（MySQL / Redis / 邮件 / HTTP 联网）用 try 包裹，
  连不上时打印“已跳过”提示，不影响整体运行；
* 运行产生的临时文件都放在系统临时目录，结束自动清理。
"""

from __future__ import annotations

import sys
import tempfile
import shutil
from pathlib import Path

# 让 Windows 终端也能正常显示中文（避免代码页乱码）
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def title(text: str) -> None:
    """打印分节标题。"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


# ====================================================================== #
# 1. SQLiteHelper —— 数据库增删改查
# ====================================================================== #
def demo_sqlite() -> None:
    title("1. SQLiteHelper（数据库增删改查）")
    from python_utils import SQLiteHelper

    with SQLiteHelper(":memory:") as db:  # 内存库，用完即弃
        db.execute("""
            CREATE TABLE users (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age  INTEGER
            )
        """)
        # 增
        uid = db.insert("users", {"name": "张三", "age": 20})
        db.insert_many("users", [
            {"name": "李四", "age": 25},
            {"name": "王五", "age": 30},
        ])
        print("插入张三 id =", uid)
        # 查
        print("age>18 :", db.query("SELECT * FROM users WHERE age > ?", (18,)))
        print("总人数 :", db.query_value("SELECT COUNT(*) FROM users"))
        # 改
        db.update("users", {"age": 21}, where="name = ?", where_params=("张三",))
        print("改后张三:", db.query_one("SELECT * FROM users WHERE name = ?", ("张三",)))
        # 删
        n = db.delete("users", where="age >= ?", where_params=(30,))
        print("删除行数:", n, "-> 剩余:", db.query("SELECT name FROM users"))


# ====================================================================== #
# 2. 日志模块
# ====================================================================== #
def demo_logger(work_dir: Path) -> None:
    title("2. 日志模块（loguru：按等级分文件、可追溯行号）")
    from python_utils.logger import setup_logger, get_logger

    log_dir = work_dir / "logs"
    setup_logger(log_dir=log_dir, rotation="5 MB", console=False, force=True)
    log = get_logger()
    log.debug("这是 DEBUG！@@@@E！@EFAW")
    log.info("这是 INFO")
    log.warning("这是 WARNING")
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("捕获到异常")

    files = sorted(p.name for p in log_dir.glob("*.log"))
    print("生成的日志文件sfsdfsaf:", files)
    print("info.log 内容示例:")
    print("   ", (log_dir / "info.log").read_text(encoding="utf-8").strip())


# ====================================================================== #
# 3. UUIDHelper
# ====================================================================== #
def demo_uuid() -> None:
    title("3. UUIDHelper（各类 UUID）")
    from python_utils import UUIDHelper as U

    print("uuid4  :", U.uuid4())
    print("hex    :", U.hex())
    print("short  :", U.short())
    print("ordered:", U.ordered())
    print("uuid5  :", U.uuid5("user:123"), "(同输入恒定)")
    print("校验    :", U.is_valid(U.uuid4()), U.is_valid("not-uuid"))


# ====================================================================== #
# 4. SnowflakeHelper
# ====================================================================== #
def demo_snowflake() -> None:
    title("4. SnowflakeHelper（雪花分布式 ID）")
    from python_utils import SnowflakeHelper

    sf = SnowflakeHelper(datacenter_id=1, worker_id=1)
    ids = [sf.next_id() for _ in range(5)]
    print("连续 5 个 ID:", ids)
    print("是否递增且唯一:", ids == sorted(ids) and len(set(ids)) == 5)


# ====================================================================== #
# 5. DateTimeHelper
# ====================================================================== #
def demo_datetime() -> None:
    title("5. DateTimeHelper（时间日期）")
    from python_utils import DateTimeHelper as DT

    print("现在        :", DT.now_str())
    print("当前时间戳  :", DT.timestamp())
    ts = DT.to_timestamp("2026-07-06 12:00:00")
    print("字符串->戳  :", ts, "-> 戳->字符串:", DT.from_timestamp(ts))
    print("3天后       :", DT.shift(days=3).strftime(DT.DEFAULT_FMT))
    print("相对时间    :", DT.humanize(DT.shift(minutes=-3)))
    print("今天区间    :", DT.day_range())
    print("本月区间    :", DT.month_range())
    with DT.Timer() as t:
        sum(range(1_000_000))
    print("计时(秒)    :", round(t.elapsed, 4))


# ====================================================================== #
# 6. ConfigHelper
# ====================================================================== #
def demo_config(work_dir: Path) -> None:
    title("6. ConfigHelper（配置读取）")
    from python_utils import ConfigHelper

    # 造一个 json 配置演示嵌套键 + 类型转换
    cfg_path = work_dir / "config.json"
    cfg_path.write_text(
        '{"db": {"host": "127.0.0.1", "port": 3306}, "debug": true, "tags": ["a", "b"]}',
        encoding="utf-8",
    )
    cfg = ConfigHelper(cfg_path)
    print("db.host     :", cfg.get("db.host"))
    print("db.port(int):", cfg.get_int("db.port"))
    print("debug(bool) :", cfg.get_bool("debug"))
    print("tags(list)  :", cfg.get_list("tags"))
    print("缺省值      :", cfg.get("db.password", "默认密码"))


# ====================================================================== #
# 7. FileHelper
# ====================================================================== #
def demo_file(work_dir: Path) -> None:
    title("7. FileHelper（文件读写/遍历/hash/压缩）")
    from python_utils import FileHelper as F

    d = work_dir / "files"
    F.write_json(d / "a.json", {"name": "张三", "age": 20})
    print("读 JSON     :", F.read_json(d / "a.json"))
    F.write_csv(d / "a.csv", [{"x": 1, "y": 2}, {"x": 3, "y": 4}])
    print("读 CSV      :", F.read_csv(d / "a.csv"))
    print("md5         :", F.md5(d / "a.json"))
    print("文件大小    :", F.human_size(F.size(d / "a.json")))
    print("遍历 *.json :", [p.name for p in F.walk(d, "*.json")])
    zip_path = F.zip_dir(d, work_dir / "backup.zip")
    print("已打包 zip  :", zip_path.name, F.human_size(F.size(zip_path)))


# ====================================================================== #
# 8. CryptoHelper
# ====================================================================== #
def demo_crypto() -> None:
    title("8. CryptoHelper（加密/编码/密码）")
    from python_utils import CryptoHelper as C

    print("md5         :", C.md5("hello"))
    print("sha256      :", C.sha256("hello")[:16], "...")
    print("hmac        :", C.hmac_sha256("data", "key")[:16], "...")
    print("base64      :", C.b64encode("你好"), "->", C.b64decode(C.b64encode("你好")).decode())
    hashed = C.hash_password("123456")
    print("密码哈希    :", hashed[:40], "...")
    print("校验密码    :", C.verify_password("123456", hashed), "/", C.verify_password("错误", hashed))
    # AES 需要 pycryptodome，未装则跳过
    try:
        token = C.aes_encrypt("秘密内容", "0123456789abcdef")
        print("AES 加解密  :", C.aes_decrypt(token, "0123456789abcdef"))
    except ImportError:
        print("AES 加解密  : (未装 pycryptodome，已跳过)")


# ====================================================================== #
# 9. CacheHelper / @cache / @retry
# ====================================================================== #
def demo_cache() -> None:
    title("9. CacheHelper + @cache + @retry")
    from python_utils import CacheHelper, cache, retry

    c = CacheHelper(maxsize=100, ttl=60)
    c.set("k", 123)
    print("缓存对象取值:", c.get("k"), "| 'k' in c:", "k" in c)

    calls = {"n": 0}

    @cache(ttl=30)
    def square(x):
        calls["n"] += 1
        return x * x

    square(9); square(9)
    print("@cache 命中 :", "第二次未再计算" if calls["n"] == 1 else "异常")

    attempts = {"n": 0}

    @retry(times=3, delay=0.01, backoff=2.0)
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ValueError("模拟失败")
        return "成功"

    print("@retry 结果 :", flaky(), f"(重试到第 {attempts['n']} 次成功)")


# ====================================================================== #
# 10. PoolHelper
# ====================================================================== #
def demo_pool() -> None:
    title("10. PoolHelper（线程/进程池并发）")
    from python_utils import PoolHelper

    def double(x):
        return x * 2

    print("并发 map(保序):", PoolHelper.map(double, range(8), max_workers=4))


# ====================================================================== #
# 11. ExcelHelper
# ====================================================================== #
def demo_excel(work_dir: Path) -> None:
    title("11. ExcelHelper（Excel 读写，需 openpyxl）")
    try:
        from python_utils import ExcelHelper
    except ImportError:
        print("(未装 openpyxl，已跳过)")
        return
    try:
        rows = [{"姓名": "张三", "年龄": 20}, {"姓名": "李四", "年龄": 25}]
        path = work_dir / "out.xlsx"
        ExcelHelper.write(path, rows)
        print("写入 Excel  :", path.name)
        print("读回内容    :", ExcelHelper.read(path))
    except ImportError:
        print("(未装 openpyxl，已跳过)")


# ====================================================================== #
# 12. HttpHelper（需要网络，联网失败则跳过）
# ====================================================================== #
def demo_http() -> None:
    title("12. HttpHelper（需 requests + 网络）")
    try:
        from python_utils import HttpHelper
    except ImportError:
        print("(未装 requests，已跳过)")
        return
    try:
        http = HttpHelper(base_url="https://httpbin.org", timeout=5, retries=1)
        data = http.get_json("/get", params={"hello": "world"})
        print("GET /get 返回的 args:", data.get("args"))
        http.close()
    except Exception as e:  # 网络不通/超时都在此跳过
        print(f"(联网失败，已跳过：{type(e).__name__})")


# ====================================================================== #
# 13. RedisHelper（需要 Redis 服务）
# ====================================================================== #
def demo_redis() -> None:
    title("13. RedisHelper（需 redis 库 + Redis 服务）")
    try:
        from python_utils import RedisHelper
    except ImportError:
        print("(未装 redis，已跳过)")
        return
    try:
        r = RedisHelper(host="127.0.0.1", port=6379, db=0)
        r.set("demo:k", "v", ex=30)
        print("set/get     :", r.get("demo:k"))
        r.set_json("demo:j", {"name": "张三"})
        print("set/get JSON:", r.get_json("demo:j"))
        with r.lock("demo:lock", timeout=5):
            print("分布式锁    : 已进入临界区")
        r.delete("demo:k", "demo:j")
        r.close()
    except Exception as e:
        print(f"(连接 Redis 失败，已跳过：{type(e).__name__})")


# ====================================================================== #
# 14. EmailHelper（需要 SMTP 账号，仅演示构造，不真的发信）
# ====================================================================== #
def demo_email() -> None:
    title("14. EmailHelper（SMTP 发信，仅演示用法）")
    from python_utils import EmailHelper

    mailer = EmailHelper(
        host="smtp.qq.com", port=465,
        user="you@qq.com", password="你的授权码", use_ssl=True,
    )
    print("已构造发件器，真实发送请取消下面注释并填好账号：")
    print("""    mailer.send(
        to=["a@x.com"], subject="日报",
        content="<h3>今日概况</h3>", html=True,
        attachments=["report.xlsx"],
    )""")
    _ = mailer  # 避免未使用告警


# ====================================================================== #
# 15. MySQLHelper / MySQLPoolHelper（需要 MySQL 服务）
# ====================================================================== #
def demo_mysql() -> None:
    title("15. MySQL（单连接 / 连接池，需 MySQL 服务）")
    try:
        from python_utils import MySQLHelper
    except ImportError:
        print("(未装 PyMySQL，已跳过)")
        return
    try:
        db = MySQLHelper(host="127.0.0.1", user="root", password="123456", database="test")
        with db:
            print("MySQL 版本  :", db.query_value("SELECT VERSION()"))
    except Exception as e:
        print(f"(连接 MySQL 失败，已跳过：{type(e).__name__})")
        print("  用法与 SQLiteHelper 相同，占位符换成 %s；连接池版见 demo_mysql_pool.py")


# ====================================================================== #
# 主流程
# ====================================================================== #
def main() -> None:
    work_dir = Path(tempfile.mkdtemp(prefix="pyutils_demo_"))
    print("临时工作目录:", work_dir)
    try:
        demo_sqlite()
        demo_logger(work_dir)
        demo_uuid()
        demo_snowflake()
        demo_datetime()
        demo_config(work_dir)
        demo_file(work_dir)
        demo_crypto()
        demo_cache()
        demo_pool()
        demo_excel(work_dir)
        demo_http()
        demo_redis()
        demo_email()
        demo_mysql()
        print("\n" + "=" * 60)
        print("  全部演示完成 ✅")
        print("=" * 60)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)  # 清理临时文件


if __name__ == "__main__":
    main()
