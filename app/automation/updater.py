# -*- coding: utf-8 -*-
# 在线更新模块 - 源码热更新
#
# 原理：业务代码(automation/*.py + icon)放在 exe 同级的 app/ 下(明文)。
# 更新时从 GitHub 拉 version.json 对比版本，下载改动的文件覆盖 app/，重启生效。
# 不用重新打包整个 exe —— 改业务逻辑只需 push 几个 .py 到 GitHub。

import json
import logging
import os
import sys
import time
import threading

try:
    import requests as _requests
except ImportError:
    _requests = None

from .version import VERSION
from .paths import is_frozen

logger = logging.getLogger("automation.updater")

# GitHub 仓库（复用旧程序的仓库；raw 原生 + 多个 CDN 反代，国内也能拉）
# 新程序的更新文件放在仓库的 app/ 子目录，与旧程序(根目录)完全隔离，互不影响。
_REPO_BASES = [
    "https://raw.githubusercontent.com/qiguaizhiru/imouse-automation/main",
    "https://ghfast.top/https://raw.githubusercontent.com/qiguaizhiru/imouse-automation/main",
    "https://fastly.jsdelivr.net/gh/qiguaizhiru/imouse-automation@main",
    "https://gcore.jsdelivr.net/gh/qiguaizhiru/imouse-automation@main",
    "https://cdn.jsdmirror.com/gh/qiguaizhiru/imouse-automation@main",
    "https://ghproxy.com/https://raw.githubusercontent.com/qiguaizhiru/imouse-automation/main",
]
# 新程序更新根 = 仓库/app
UPDATE_URLS = [f"{b}/app" for b in _REPO_BASES]

# version.json 里读哪个通道
UPDATE_CHANNEL = "app"


def _version_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except Exception:
        return (0,)


def version_ge(v1, v2):
    """v1 >= v2 ?"""
    t1, t2 = _version_tuple(v1), _version_tuple(v2)
    n = max(len(t1), len(t2))
    t1 += (0,) * (n - len(t1))
    t2 += (0,) * (n - len(t2))
    return t1 >= t2


def _app_root():
    """业务代码所在目录：打包=exe同级/app，开发=项目根"""
    if is_frozen():
        return os.path.join(os.path.dirname(sys.executable), "app")
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Updater:
    """在线更新器"""

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.local_version = VERSION

    def _log(self, msg):
        logger.info(msg)
        if self.log_callback:
            self.log_callback(msg)

    def check_async(self, on_result):
        """后台检查更新。on_result(result_dict) 在完成后回调（需自行切回主线程）。
        result: {"status": "latest"|"available"|"error", "remote_version", "changelog", "files", "message"}
        """
        threading.Thread(target=lambda: on_result(self.check()), daemon=True).start()

    def check(self):
        if not _requests:
            return {"status": "error", "message": "缺少 requests 模块"}
        remote = self._fetch_version_json()
        if not remote:
            return {"status": "error", "message": "无法访问更新服务器（所有源都失败）"}

        channel = remote.get(UPDATE_CHANNEL, remote)
        remote_version = channel.get("version", "")
        changelog = channel.get("changelog", "")
        files = channel.get("files", [])
        if not remote_version:
            return {"status": "error", "message": "version.json 格式错误"}

        if version_ge(self.local_version, remote_version):
            return {"status": "latest", "remote_version": remote_version,
                    "message": f"已是最新版本 {self.local_version}"}

        return {"status": "available", "remote_version": remote_version,
                "changelog": changelog, "files": files}

    def _fetch_version_json(self):
        for base in UPDATE_URLS:
            try:
                r = _requests.get(f"{base}/version.json?t={int(time.time())}", timeout=8)
                if r.status_code == 200:
                    self._log(f"更新源: {base.split('//')[1].split('/')[0]}")
                    return r.json()
            except Exception:
                continue
        return None

    def download_and_apply(self, remote_version, files, on_done):
        """下载文件到临时目录，全部成功后生成重启脚本。on_done(ok, message)。"""
        threading.Thread(
            target=lambda: self._do_download(remote_version, files, on_done),
            daemon=True,
        ).start()

    def _do_download(self, remote_version, files, on_done):
        try:
            app_root = _app_root()
            tmp_dir = os.path.join(app_root, ".update_tmp")
            import shutil
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
            os.makedirs(tmp_dir, exist_ok=True)

            cache_buster = f"?v={remote_version}"
            for i, fn in enumerate(files):
                self._log(f"下载 ({i+1}/{len(files)}): {fn}")
                if not self._download_one(fn, tmp_dir, cache_buster):
                    on_done(False, f"下载失败: {fn}")
                    return

            # 生成重启脚本：等 exe 退出 -> 用临时文件覆盖 app/ -> 重启
            bat = self._write_restart_script(app_root, tmp_dir, files)
            self._log(f"下载完成，共 {len(files)} 个文件")
            on_done(True, bat)
        except Exception as e:
            logger.error(f"更新下载异常: {e}")
            on_done(False, str(e))

    def _download_one(self, fn, tmp_dir, cache_buster):
        for base in UPDATE_URLS:
            try:
                r = _requests.get(f"{base}/{fn}{cache_buster}", timeout=60)
                if r.status_code == 200 and len(r.content) > 0:
                    out = os.path.join(tmp_dir, fn.replace("/", os.sep))
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(out, "wb") as f:
                        f.write(r.content)
                    return True
            except Exception:
                continue
        return False

    def _write_restart_script(self, app_root, tmp_dir, files):
        """生成 Windows bat：覆盖文件并重启 exe/程序"""
        if is_frozen():
            exe_path = sys.executable
            exe_dir = os.path.dirname(exe_path)
            restart_cmd = f'start "" "{exe_path}"'
        else:
            exe_dir = app_root
            restart_cmd = 'start "" run.bat'

        bat_path = os.path.join(exe_dir, "_do_update.bat")
        # 用 gbk 编码 + chcp 936(而非65001)：中文 Windows 默认代码页是 936，
        # 这样 bat 里的中文路径(如 iMouse自动化中心)能被 copy 正确解析。
        # 之前用 65001 会导致中文路径乱码、copy 失败，更新看似成功实则没生效。
        lines = [
            "@echo off",
            "chcp 936 > nul",
            "title iMouse gengxin",
            "echo 正在应用更新，请稍候...",
            "timeout /t 3 /nobreak > nul",
        ]
        for fn in files:
            rel = fn.replace("/", "\\")
            src = os.path.join(tmp_dir, rel)
            dst = os.path.join(app_root, rel)
            sub = os.path.dirname(dst)
            lines.append(f'if not exist "{sub}" mkdir "{sub}"')
            lines.append(f'copy /Y "{src}" "{dst}" > nul')
        lines += [
            f'rd /s /q "{tmp_dir}"',
            "echo 更新完成，正在重启...",
            "timeout /t 1 /nobreak > nul",
            f'cd /d "{exe_dir}"',
            restart_cmd,
            'del "%~f0"',
        ]
        with open(bat_path, "w", encoding="gbk", errors="replace") as f:
            f.write("\r\n".join(lines))
        return bat_path
