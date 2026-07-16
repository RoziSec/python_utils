# -*- coding: utf-8 -*-
"""邮件发送操作类。

基于标准库 ``smtplib`` + ``email``，无需第三方依赖。支持纯文本 / HTML 正文、
多收件人、抄送、附件，以及 SSL / STARTTLS 两种加密方式。

    from python_utils import EmailHelper

    mailer = EmailHelper(host="smtp.qq.com", port=465,
                         user="me@qq.com", password="授权码", use_ssl=True)
    mailer.send(
        to=["a@x.com", "b@x.com"],
        subject="日报",
        content="<h3>今日概况</h3>", html=True,
        attachments=["report.xlsx"],
    )
"""

from __future__ import annotations

import smtplib
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Union


class EmailHelper:
    """SMTP 邮件发送工具类。"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        *,
        use_ssl: bool = True,
        sender_name: Optional[str] = None,
        timeout: int = 15,
    ):
        """
        :param host: SMTP 服务器地址，如 ``smtp.qq.com``。
        :param port: 端口；SSL 常用 465，STARTTLS 常用 587。
        :param user: 登录账号（通常即发件邮箱）。
        :param password: 密码或授权码。
        :param use_ssl: True 用 SSL(465)，False 用 STARTTLS(587)。
        :param sender_name: 发件人显示名称。
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self.sender_name = sender_name or user
        self.timeout = timeout

    def send(
        self,
        to: Union[str, List[str]],
        subject: str,
        content: str,
        *,
        html: bool = False,
        cc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Union[str, Path]]] = None,
    ) -> None:
        """发送邮件。

        :param to: 收件人，单个字符串或列表。
        :param subject: 主题。
        :param content: 正文。
        :param html: True 则正文按 HTML 渲染。
        :param cc: 抄送。
        :param attachments: 附件文件路径列表。
        """
        to_list = [to] if isinstance(to, str) else list(to)
        cc_list = ([cc] if isinstance(cc, str) else list(cc)) if cc else []

        msg = MIMEMultipart()
        msg["From"] = f"{Header(self.sender_name, 'utf-8').encode()} <{self.user}>"
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = Header(subject, "utf-8")

        msg.attach(MIMEText(content, "html" if html else "plain", "utf-8"))

        for item in attachments or []:
            p = Path(item)
            part = MIMEApplication(p.read_bytes())
            part.add_header("Content-Disposition", "attachment",
                            filename=("utf-8", "", p.name))
            msg.attach(part)

        recipients = to_list + cc_list
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            server.starttls()
        try:
            server.login(self.user, self.password)
            server.sendmail(self.user, recipients, msg.as_string())
        finally:
            server.quit()


__all__ = ["EmailHelper"]
