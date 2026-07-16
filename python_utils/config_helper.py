# -*- coding: utf-8 -*-
"""配置读取操作类。

统一读取 ``.env`` / ``.json`` / ``.yaml`` / ``.ini`` 配置，并提供：

* 点号路径访问嵌套键：``cfg.get("db.host")``；
* 环境变量覆盖：同名环境变量优先级高于文件（便于容器化部署）；
* 默认值与类型转换：``get_int`` / ``get_bool`` / ``get_list`` 等。

YAML 需要 ``pip install pyyaml``（延迟导入，用到才需要）；其余格式用标准库。

    from python_utils import ConfigHelper

    cfg = ConfigHelper("config.yaml", env_prefix="APP_")
    host = cfg.get("db.host", "127.0.0.1")   # 若存在环境变量 APP_DB_HOST 则优先
    port = cfg.get_int("db.port", 3306)
"""

from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_MISSING = object()


class ConfigHelper:
    """配置读取工具类。"""

    def __init__(self, path: Optional[Union[str, Path]] = None, *, env_prefix: str = ""):
        """
        :param path: 配置文件路径，按扩展名自动识别格式；可为空只用环境变量。
        :param env_prefix: 环境变量覆盖时的前缀，如 ``"APP_"``。
        """
        self.env_prefix = env_prefix
        self._data: Dict[str, Any] = {}
        if path:
            self.load(path)

    # ------------------------------------------------------------------ #
    # 加载
    # ------------------------------------------------------------------ #
    def load(self, path: Union[str, Path]) -> "ConfigHelper":
        """按扩展名加载配置文件（.env/.json/.yaml/.yml/.ini/.cfg）。"""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"配置文件不存在: {p}")
        suffix = p.suffix.lower()
        if suffix == ".json":
            self._data = json.loads(p.read_text(encoding="utf-8"))
        elif suffix in (".yaml", ".yml"):
            if yaml is None:
                raise ImportError("读取 YAML 需要先安装：pip install pyyaml")
            self._data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        elif suffix in (".ini", ".cfg"):
            parser = configparser.ConfigParser()
            parser.read(p, encoding="utf-8")
            self._data = {s: dict(parser.items(s)) for s in parser.sections()}
        elif suffix == ".env" or p.name == ".env":
            self._data = self._parse_env(p.read_text(encoding="utf-8"))
        else:
            raise ValueError(f"不支持的配置格式: {suffix}")
        return self

    @staticmethod
    def _parse_env(text: str) -> Dict[str, str]:
        """解析 .env 文本为字典（忽略注释与空行，去掉引号）。"""
        result: Dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            result[key.strip()] = val.strip().strip('"').strip("'")
        return result

    # ------------------------------------------------------------------ #
    # 取值
    # ------------------------------------------------------------------ #
    def get(self, key: str, default: Any = None) -> Any:
        """按点号路径取值，环境变量优先。

        ``key="db.host"`` 会先查环境变量 ``{prefix}DB_HOST``，再查文件里的嵌套键。
        """
        env_key = self.env_prefix + key.upper().replace(".", "_")
        if env_key in os.environ:
            return os.environ[env_key]

        node: Any = self._data
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def get_int(self, key: str, default: int = 0) -> int:
        v = self.get(key, _MISSING)
        return default if v is _MISSING else int(v)

    def get_float(self, key: str, default: float = 0.0) -> float:
        v = self.get(key, _MISSING)
        return default if v is _MISSING else float(v)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """字符串 true/1/yes/on（不区分大小写）视为 True。"""
        v = self.get(key, _MISSING)
        if v is _MISSING:
            return default
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on", "y")

    def get_list(self, key: str, default: Optional[List] = None, sep: str = ",") -> List:
        """取列表；文件里本就是 list 直接返回，字符串则按分隔符切分。"""
        v = self.get(key, _MISSING)
        if v is _MISSING:
            return default or []
        if isinstance(v, list):
            return v
        return [item.strip() for item in str(v).split(sep) if item.strip()]

    def all(self) -> Dict[str, Any]:
        """返回全部配置（浅拷贝）。"""
        return dict(self._data)

    def __getitem__(self, key: str) -> Any:
        v = self.get(key, _MISSING)
        if v is _MISSING:
            raise KeyError(key)
        return v

    def __contains__(self, key: str) -> bool:
        return self.get(key, _MISSING) is not _MISSING


__all__ = ["ConfigHelper"]
