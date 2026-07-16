# -*- coding: utf-8 -*-
"""加密与编码操作类。

包含两部分：

* **标准库即可用**：md5 / sha 系列、HMAC 签名、base64 编解码、随机密钥、
  以及基于 ``hashlib.pbkdf2`` 的密码加盐哈希与校验（推荐用它存密码）；
* **需要 ``pycryptodome``（延迟导入）**：AES 对称加解密（CBC 模式）。
  ``pip install pycryptodome``。

    from python_utils import CryptoHelper as C

    C.md5("hello")
    hashed = C.hash_password("123456")     # 存库
    C.verify_password("123456", hashed)    # 登录校验 -> True
    token = C.aes_encrypt("秘密", "0123456789abcdef")
    C.aes_decrypt(token, "0123456789abcdef")
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Union

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:  # pragma: no cover
    AES = None

BytesOrStr = Union[str, bytes]


def _to_bytes(data: BytesOrStr, encoding: str = "utf-8") -> bytes:
    return data if isinstance(data, bytes) else data.encode(encoding)


class CryptoHelper:
    """加密/编码工具类（静态方法）。"""

    # ------------------------------------------------------------------ #
    # 摘要
    # ------------------------------------------------------------------ #
    @staticmethod
    def md5(data: BytesOrStr) -> str:
        return hashlib.md5(_to_bytes(data)).hexdigest()

    @staticmethod
    def sha1(data: BytesOrStr) -> str:
        return hashlib.sha1(_to_bytes(data)).hexdigest()

    @staticmethod
    def sha256(data: BytesOrStr) -> str:
        return hashlib.sha256(_to_bytes(data)).hexdigest()

    @staticmethod
    def hmac_sha256(data: BytesOrStr, key: BytesOrStr) -> str:
        """HMAC-SHA256 签名，常用于接口验签。"""
        return hmac.new(_to_bytes(key), _to_bytes(data), hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------ #
    # base64
    # ------------------------------------------------------------------ #
    @staticmethod
    def b64encode(data: BytesOrStr, *, urlsafe: bool = False) -> str:
        raw = _to_bytes(data)
        enc = base64.urlsafe_b64encode(raw) if urlsafe else base64.b64encode(raw)
        return enc.decode("ascii")

    @staticmethod
    def b64decode(text: str, *, urlsafe: bool = False) -> bytes:
        return base64.urlsafe_b64decode(text) if urlsafe else base64.b64decode(text)

    # ------------------------------------------------------------------ #
    # 随机
    # ------------------------------------------------------------------ #
    @staticmethod
    def random_hex(n_bytes: int = 16) -> str:
        """生成 n_bytes 字节的随机十六进制串（如 token、密钥）。"""
        return os.urandom(n_bytes).hex()

    # ------------------------------------------------------------------ #
    # 密码加盐哈希（推荐用于存储密码）
    # ------------------------------------------------------------------ #
    @staticmethod
    def hash_password(password: str, *, iterations: int = 200_000) -> str:
        """PBKDF2-HMAC-SHA256 加盐哈希。返回 ``算法$迭代$盐$哈希`` 自包含字符串。"""
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """校验明文密码与 ``hash_password`` 生成的哈希是否匹配。"""
        try:
            algo, iter_s, salt_hex, hash_hex = hashed.split("$")
            if algo != "pbkdf2_sha256":
                return False
            dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                     bytes.fromhex(salt_hex), int(iter_s))
            return hmac.compare_digest(dk.hex(), hash_hex)  # 防时序攻击
        except (ValueError, AttributeError):
            return False

    # ------------------------------------------------------------------ #
    # AES 对称加解密（需 pycryptodome）
    # ------------------------------------------------------------------ #
    @staticmethod
    def _require_aes():
        if AES is None:
            raise ImportError("AES 加解密需要先安装：pip install pycryptodome")

    @staticmethod
    def aes_encrypt(plaintext: str, key: BytesOrStr) -> str:
        """AES-CBC 加密，返回 base64(iv + 密文)。key 长度需为 16/24/32 字节。"""
        CryptoHelper._require_aes()
        key_b = _to_bytes(key)
        iv = os.urandom(16)
        cipher = AES.new(key_b, AES.MODE_CBC, iv)
        ct = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
        return base64.b64encode(iv + ct).decode("ascii")

    @staticmethod
    def aes_decrypt(token: str, key: BytesOrStr) -> str:
        """解密 ``aes_encrypt`` 的结果。"""
        CryptoHelper._require_aes()
        key_b = _to_bytes(key)
        raw = base64.b64decode(token)
        iv, ct = raw[:16], raw[16:]
        cipher = AES.new(key_b, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(ct), AES.block_size).decode()


__all__ = ["CryptoHelper"]
