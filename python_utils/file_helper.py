# -*- coding: utf-8 -*-
"""文件与路径操作类。

封装日常文件读写与目录处理：文本 / JSON / CSV 读写、目录遍历、
文件 hash、压缩解包、安全删除、大小格式化等。全部为静态方法。

    from python_utils import FileHelper as F

    F.write_json("out.json", {"a": 1})
    data = F.read_json("out.json")
    for p in F.walk("src", pattern="*.py"):
        ...
    print(F.md5("out.json"))
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union

PathLike = Union[str, Path]


class FileHelper:
    """文件/路径工具类（静态方法）。"""

    # ------------------------------------------------------------------ #
    # 文本
    # ------------------------------------------------------------------ #
    @staticmethod
    def read_text(path: PathLike, encoding: str = "utf-8") -> str:
        return Path(path).read_text(encoding=encoding)

    @staticmethod
    def write_text(path: PathLike, content: str, encoding: str = "utf-8", *, append: bool = False) -> None:
        """写文本，自动创建父目录；``append=True`` 为追加。"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a" if append else "w", encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def read_lines(path: PathLike, encoding: str = "utf-8", *, strip: bool = True) -> List[str]:
        text = Path(path).read_text(encoding=encoding)
        lines = text.splitlines()
        return [ln.strip() for ln in lines] if strip else lines

    # ------------------------------------------------------------------ #
    # JSON
    # ------------------------------------------------------------------ #
    @staticmethod
    def read_json(path: PathLike, encoding: str = "utf-8") -> Any:
        return json.loads(Path(path).read_text(encoding=encoding))

    @staticmethod
    def write_json(path: PathLike, data: Any, encoding: str = "utf-8", *, indent: int = 2) -> None:
        """写 JSON（默认缩进美化、保留中文）。"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding=encoding)

    # ------------------------------------------------------------------ #
    # CSV
    # ------------------------------------------------------------------ #
    @staticmethod
    def read_csv(path: PathLike, encoding: str = "utf-8-sig") -> List[Dict[str, str]]:
        """读 CSV 为字典列表（首行为表头）。"""
        with Path(path).open("r", encoding=encoding, newline="") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def write_csv(path: PathLike, rows: Iterable[Dict[str, Any]],
                  fieldnames: Optional[List[str]] = None, encoding: str = "utf-8-sig") -> None:
        """写 CSV（字典列表）。fieldnames 省略时取第一行的键。"""
        rows = list(rows)
        if not rows:
            return
        fieldnames = fieldnames or list(rows[0].keys())
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding=encoding, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # ------------------------------------------------------------------ #
    # 目录遍历
    # ------------------------------------------------------------------ #
    @staticmethod
    def walk(directory: PathLike, pattern: str = "*", *, recursive: bool = True) -> Iterator[Path]:
        """遍历目录下匹配 pattern 的文件，返回 Path 迭代器。"""
        d = Path(directory)
        globber = d.rglob if recursive else d.glob
        for p in globber(pattern):
            if p.is_file():
                yield p

    @staticmethod
    def ensure_dir(directory: PathLike) -> Path:
        """确保目录存在（含多级），返回 Path。"""
        p = Path(directory)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------ #
    # hash
    # ------------------------------------------------------------------ #
    @staticmethod
    def file_hash(path: PathLike, algo: str = "md5", chunk_size: int = 8192) -> str:
        """计算文件哈希（默认 md5，可传 sha1/sha256），分块读取支持大文件。"""
        h = hashlib.new(algo)
        with Path(path).open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def md5(path: PathLike) -> str:
        return FileHelper.file_hash(path, "md5")

    @staticmethod
    def sha256(path: PathLike) -> str:
        return FileHelper.file_hash(path, "sha256")

    # ------------------------------------------------------------------ #
    # 复制 / 移动 / 删除
    # ------------------------------------------------------------------ #
    @staticmethod
    def copy(src: PathLike, dst: PathLike) -> None:
        """复制文件或目录树。"""
        src, dst = Path(src), Path(dst)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    @staticmethod
    def move(src: PathLike, dst: PathLike) -> None:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

    @staticmethod
    def remove(path: PathLike, *, missing_ok: bool = True) -> None:
        """安全删除文件或目录，默认不存在也不报错。"""
        p = Path(path)
        if not p.exists():
            if missing_ok:
                return
            raise FileNotFoundError(p)
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()

    # ------------------------------------------------------------------ #
    # 压缩 / 解压
    # ------------------------------------------------------------------ #
    @staticmethod
    def zip_dir(src_dir: PathLike, zip_path: PathLike) -> Path:
        """把目录打包为 zip，返回 zip 路径。"""
        zip_path = Path(zip_path)
        base = zip_path.with_suffix("")  # make_archive 会自动补 .zip
        archive = shutil.make_archive(str(base), "zip", root_dir=str(src_dir))
        return Path(archive)

    @staticmethod
    def unzip(zip_path: PathLike, dst_dir: PathLike) -> None:
        """解压 zip 到目标目录。"""
        shutil.unpack_archive(str(zip_path), str(dst_dir))

    # ------------------------------------------------------------------ #
    # 杂项
    # ------------------------------------------------------------------ #
    @staticmethod
    def size(path: PathLike) -> int:
        """文件字节数。"""
        return Path(path).stat().st_size

    @staticmethod
    def human_size(num_bytes: int) -> str:
        """字节数转人类可读，如 '1.5 MB'。"""
        size = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


__all__ = ["FileHelper"]
