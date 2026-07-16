# -*- coding: utf-8 -*-
"""HTTP 请求操作类。

基于 ``requests`` 封装常用请求，内置：

* ``Session`` 连接复用；统一 ``base_url`` / 默认 header / 超时；
* 失败自动重试（对连接错误与 5xx 做指数退避重试）；
* 便捷 JSON 收发：``get_json`` / ``post_json`` 直接返回 dict。

依赖：``pip install requests``（延迟导入，用到才需要）。

    from python_utils import HttpHelper

    http = HttpHelper(base_url="https://api.example.com",
                      headers={"Authorization": "Bearer xxx"}, timeout=10)
    data = http.get_json("/users", params={"page": 1})
    http.post_json("/users", json={"name": "张三"})
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    import requests
    from requests.adapters import HTTPAdapter
    try:
        from urllib3.util.retry import Retry
    except ImportError:  # pragma: no cover
        Retry = None
except ImportError:  # pragma: no cover
    requests = None
    HTTPAdapter = None
    Retry = None


class HttpHelper:
    """HTTP 请求工具类。"""

    def __init__(
        self,
        base_url: str = "",
        *,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        retries: int = 3,
        backoff: float = 0.5,
        verify: bool = True,
    ):
        """
        :param base_url: 基础地址，之后各方法可只传相对路径。
        :param headers: 默认请求头。
        :param timeout: 默认超时秒数。
        :param retries: 失败重试次数（连接错误 / 5xx）。
        :param backoff: 重试退避因子。
        :param verify: 是否校验 SSL 证书。
        """
        if requests is None:
            raise ImportError("使用 HttpHelper 需要先安装：pip install requests")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify = verify
        self._session = requests.Session()
        if headers:
            self._session.headers.update(headers)

        # 配置自动重试
        if Retry is not None and retries > 0:
            retry = Retry(
                total=retries,
                backoff_factor=backoff,
                status_forcelist=(500, 502, 503, 504),
                allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "PATCH"]),
            )
            adapter = HTTPAdapter(max_retries=retry)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    # ------------------------------------------------------------------ #
    # 通用请求
    # ------------------------------------------------------------------ #
    def request(self, method: str, path: str, **kwargs) -> "requests.Response":
        """底层请求；自动补 base_url、超时、verify。返回原始 Response。"""
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("verify", self.verify)
        return self._session.request(method.upper(), self._url(path), **kwargs)

    def get(self, path: str, params: Optional[Dict] = None, **kwargs) -> "requests.Response":
        return self.request("GET", path, params=params, **kwargs)

    def post(self, path: str, data: Any = None, json: Any = None, **kwargs) -> "requests.Response":
        return self.request("POST", path, data=data, json=json, **kwargs)

    def put(self, path: str, data: Any = None, json: Any = None, **kwargs) -> "requests.Response":
        return self.request("PUT", path, data=data, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> "requests.Response":
        return self.request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------ #
    # JSON 便捷方法
    # ------------------------------------------------------------------ #
    def get_json(self, path: str, params: Optional[Dict] = None, **kwargs) -> Any:
        """GET 并返回解析后的 JSON；非 2xx 抛出异常。"""
        resp = self.get(path, params=params, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post_json(self, path: str, json: Any = None, **kwargs) -> Any:
        """POST JSON 并返回解析后的 JSON；非 2xx 抛出异常。"""
        resp = self.post(path, json=json, **kwargs)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    # 下载
    # ------------------------------------------------------------------ #
    def download(self, path: str, save_path: str, *, chunk_size: int = 8192, **kwargs) -> str:
        """流式下载文件到本地，返回保存路径。"""
        from pathlib import Path

        with self.request("GET", path, stream=True, **kwargs) as resp:
            resp.raise_for_status()
            p = Path(save_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
        return save_path

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "HttpHelper":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


__all__ = ["HttpHelper"]
