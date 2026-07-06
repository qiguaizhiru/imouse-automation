# -*- coding: utf-8 -*-
# 错误上报模块 - 通过飞书群自定义机器人 webhook 推送
#
# 相比 QQ 邮箱 SMTP，飞书 webhook 更适合"多台电脑分发"场景：
#   - HTTPS POST，不登录，不会被邮件风控/频率限制
#   - 多台电脑共用一个 webhook 地址
#   - 消息实时推送到飞书群，手机能收到
#
# 机器人安全设置用"自定义关键词"，消息里带上 FEISHU_KEYWORD 即可通过。

import json
import logging
import os
import platform
import socket
import threading
import traceback
from datetime import datetime

try:
    import requests as _requests
except ImportError:
    _requests = None

logger = logging.getLogger("automation.error_reporter")

# ── 内置飞书机器人配置（所有电脑共用）──
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/1f1eeffa-cadb-4c41-ae3c-81f6626801b7"
FEISHU_KEYWORD = "iMouse"    # 机器人安全设置的自定义关键词（消息必须包含）

USER_FILE = None  # 延迟初始化（见下）

from .paths import data_path

USER_FILE = data_path("user.json")
# 可选：webhook 也支持用外部文件覆盖（不改代码就能换群）
WEBHOOK_FILE = data_path("feishu_webhook.txt")


def load_user_info():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_user_info(info):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


def get_machine_info():
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def _resolve_webhook():
    """webhook 优先级：外部文件 > 内置常量"""
    if os.path.exists(WEBHOOK_FILE):
        try:
            with open(WEBHOOK_FILE, "r", encoding="utf-8-sig") as f:
                url = f.read().strip()
            if url:
                return url
        except Exception:
            pass
    return FEISHU_WEBHOOK


class ErrorReporter:
    """错误上报器 - 后台异步推送到飞书群"""

    def __init__(self, config=None):
        cfg = config or {}
        self._webhook = cfg.get("webhook") or _resolve_webhook()
        self._keyword = cfg.get("keyword") or FEISHU_KEYWORD
        self._user_info = load_user_info()
        self._machine = get_machine_info()

    @property
    def username(self):
        return self._user_info.get("username", "未设置")

    @username.setter
    def username(self, value):
        self._user_info["username"] = value
        save_user_info(self._user_info)

    @property
    def is_configured(self):
        return bool(self._webhook) and _requests is not None

    def report_error(self, error, context="", device_name=""):
        """异步推送错误"""
        if not self.is_configured:
            logger.warning("飞书 webhook 未配置，跳过错误上报")
            return
        threading.Thread(
            target=self._send_error,
            args=(error, context, device_name),
            daemon=True,
        ).start()

    def send_test(self):
        """发送测试消息，同步执行，返回 (success, message)"""
        if not _requests:
            return False, "缺少 requests 模块"
        if not self._webhook:
            return False, "飞书 webhook 未配置"
        try:
            text = self._build_text(
                "这是一条测试消息，说明飞书上报配置成功。",
                context="测试连接", device_name="N/A")
            self._post(text)
            return True, "测试消息已发送到飞书群"
        except Exception as e:
            return False, f"发送失败: {e}"

    # 兼容旧调用名
    def send_test_email(self):
        return self.send_test()

    def _send_error(self, error, context, device_name):
        try:
            if isinstance(error, Exception):
                tb = "".join(traceback.format_exception(
                    type(error), error, error.__traceback__))
                error_str = str(error)
            else:
                error_str = str(error)
                tb = ""
            text = self._build_text(error_str, context, device_name, tb)
            self._post(text)
            logger.info("错误已上报到飞书")
        except Exception as e:
            logger.error(f"上报飞书失败: {e}")

    def _build_text(self, error_str, context="", device_name="", tb=""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"【{self._keyword} 错误通知】",
            f"用户: {self.username}",
            f"电脑: {self._machine['hostname']}",
            f"时间: {now}",
            f"设备: {device_name or 'N/A'}",
            f"场景: {context or 'N/A'}",
            f"错误: {error_str}",
        ]
        if tb:
            # 堆栈太长会被飞书截断，保留末尾最相关部分
            tail = tb.strip()
            if len(tail) > 1500:
                tail = "..." + tail[-1500:]
            lines.append("堆栈:\n" + tail)
        return "\n".join(lines)

    def _post(self, text):
        payload = {"msg_type": "text", "content": {"text": text}}
        r = _requests.post(self._webhook, json=payload, timeout=15)
        data = r.json()
        # 飞书成功返回 code=0 (或 StatusCode=0)
        code = data.get("code", data.get("StatusCode", 0))
        if code not in (0, None):
            raise RuntimeError(f"飞书返回错误: {data}")
