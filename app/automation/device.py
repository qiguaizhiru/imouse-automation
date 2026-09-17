import base64
import json
import os
import time
import random
import logging
import requests
from io import BytesIO
from typing import Optional

from .coordinates import get_coords, detect_model_type
from .imouse_backend import make_backend, ImouseBackend, ProBackend, version_label

logger = logging.getLogger("automation.device")


class Device:
    """对单个 iMouse 设备的操作封装，提供高层 TikTok 交互方法"""

    def __init__(self, device_id, name, api_url=None, info=None, group_name="",
                 node_name="本机", backend: ImouseBackend = None):
        self.device_id = device_id
        self.name = name
        self.info = info or {}
        self.group_name = group_name
        self.node_name = node_name      # 所属节点（哪台电脑）
        # 版本适配层：Pro / XP 的接口差异都封装在 backend 里
        if backend is None:
            # 兼容老调用：只给了 api_url 就当 Pro
            host = "127.0.0.1"
            if api_url:
                try:
                    host = api_url.split("//", 1)[1].split(":", 1)[0]
                except Exception:
                    pass
            backend = ProBackend(host)
        self.backend = backend
        self.api_url = backend.api_url
        # 机型识别 + 加载对应坐标
        self.model_type = detect_model_type(self.info, group_name)
        self.coords = get_coords(self.model_type)

    def __repr__(self):
        return (f"Device({self.name!r}, id={self.device_id!r}, "
                f"type={self.model_type}, node={self.node_name!r}, "
                f"imouse={self.backend.version})")

    @property
    def imouse_version(self):
        return self.backend.version

    @property
    def full_name(self):
        """带节点前缀的唯一名称，避免不同电脑设备重名"""
        return f"{self.node_name}/{self.name}"

    # ── 坐标辅助 ──

    def _pt(self, key):
        """取坐标点 (x, y)，自动加抖动"""
        c = self.coords.get(key)
        if not c:
            logger.warning(f"[{self.name}] 坐标缺失: {key}")
            return (0, 0)
        j = self.coords.get("jitter", 10)
        x = c[0] + random.randint(-j, j)
        y = c[1] + random.randint(-j, j)
        return (x, y)

    def _swipe_pts(self, key):
        """取滑动坐标，自动加抖动"""
        sw = self.coords.get(key, {})
        j = self.coords.get("jitter", 10)
        return (
            sw.get("sx", 200) + random.randint(-j, j),
            sw.get("sy", 600) + random.randint(-j, j),
            sw.get("ex", 200) + random.randint(-j, j),
            sw.get("ey", 200) + random.randint(-j, j),
        )

    # ── 底层 API 调用（保留给老代码；新代码请直接用 self.backend） ──

    def _post(self, fun, data, quiet=False, timeout=30):
        """直接透传一个 fun。注意：fun 名是版本相关的，
        只在你明确知道当前版本的情况下用；否则用下面的高层方法。"""
        return self.backend.post(fun, data, timeout=timeout, quiet=quiet)

    def _ok(self, resp):
        return self.backend.ok(resp)

    # ── 基础操作 ──

    def tap(self, x, y):
        logger.debug(f"[{self.name}] tap({x}, {y})")
        return self.backend.click(self.device_id, x, y)

    def swipe(self, sx, sy, ex, ey, length=0.9):
        direction = "up" if ey < sy else "down" if ey > sy else ("left" if ex < sx else "right")
        logger.debug(f"[{self.name}] swipe {direction} ({sx},{sy})->({ex},{ey})")
        return self.backend.swipe(self.device_id, direction, length, sx, sy, ex, ey)

    def swipe_dir(self, direction, length=0.5, sx=None, sy=None):
        """按方向+距离滑动（与验证过的养号流程一致，只给方向+距离+起点）"""
        logger.debug(f"[{self.name}] swipe_dir {direction} len={length} ({sx},{sy})")
        return self.backend.swipe(self.device_id, direction, length, sx, sy)

    def press_home(self):
        """回主屏幕（用 WIN+h，与验证过的养号/发布流程一致）"""
        logger.debug(f"[{self.name}] press_home")
        return self.backend.send_key(self.device_id, "", "WIN+h")

    def is_landscape(self):
        """截图判断是否横屏（宽>高）。养号刷到直播会横屏，需特殊处理。
        返回 True/False，截图失败返回 None。"""
        b64 = self.screenshot_b64()
        if not b64:
            return None
        try:
            from .vision import get_image_size
            size = get_image_size(b64)
            if not size:
                return None
            w, h = size
            return w > h
        except Exception:
            return None

    def open_url(self, url):
        logger.debug(f"[{self.name}] open_url: {url}")
        return self.backend.open_url(self.device_id, url)

    def send_key(self, key="", fn_key=None):
        """发送按键，如 fn_key='HOME' 返回主屏幕"""
        return self.backend.send_key(self.device_id, key, fn_key)

    def send_text(self, text):
        """发送批量字符（直接输入文本框）"""
        return self.backend.send_text(self.device_id, text)

    def album_upload(self, file_paths, album="Recents", outtime=60000):
        """上传本地图片/视频文件到手机相册。
        file_paths: 本地文件路径列表，如 [r'D:\\a.jpg']"""
        return self.backend.album_upload(self.device_id, file_paths, album, outtime)

    def file_upload(self, file_paths, path="/", outtime=60000):
        """上传本地文件到手机文件系统（iOS 15+）。path 为手机上的目标目录"""
        return self.backend.file_upload(self.device_id, file_paths, path, outtime)

    def send_clipboard(self, text):
        return self.backend.set_clipboard(self.device_id, text)

    def get_clipboard(self):
        return self.backend.get_clipboard(self.device_id)

    def screenshot_b64(self):
        return self.backend.screenshot_b64(self.device_id)

    def ocr(self, rect=None):
        return self.backend.ocr(self.device_id, rect)

    def find_image_native(self, img_b64, similarity=0.7, rect=None):
        """iMouse 原生识图（服务端匹配），返回 (x, y, conf) 或 None。
        与验证过的养号流程一致，不做本地cv匹配，避免误匹配 + 减少截图。"""
        return self.backend.find_image(self.device_id, img_b64, similarity, rect)

    def find_image(self, img_b64, similarity=0.8, rect=None):
        """查找图片：优先本地 OpenCV 模板匹配，失败回退 iMouse 原生识图。
        （发布流程用；养号用 find_image_native 更稳）"""
        local = self._find_image_local(img_b64, similarity, rect)
        if local:
            return local
        return self.find_image_native(img_b64, similarity, rect)

    def _find_image_local(self, img_b64, similarity, rect):
        """本地识图：截图 -> cv 模板匹配 -> 截图坐标换算回逻辑坐标"""
        from .vision import cv_find_image, cv_available
        if not cv_available():
            return None
        screen = self.screenshot_b64()
        if not screen:
            return None
        hit = cv_find_image(screen, img_b64, similarity, rect)
        if not hit:
            return None
        sx, sy, conf = hit
        # 截图像素坐标 -> 逻辑坐标
        lx, ly = self._screen_to_logical(screen, sx, sy)
        return (lx, ly, conf)

    def _screen_to_logical(self, screen_b64, sx, sy):
        """把截图像素坐标换算成逻辑点击坐标"""
        try:
            logical_w = int(self.info.get("width", 0) or 0)
            logical_h = int(self.info.get("height", 0) or 0)
            if not logical_w or not logical_h:
                return (sx, sy)
            from .vision import get_image_size
            size = get_image_size(screen_b64)
            if not size:
                return (sx, sy)
            screen_w, screen_h = size
            if screen_w == logical_w and screen_h == logical_h:
                return (sx, sy)
            lx = int(round(sx * logical_w / screen_w))
            ly = int(round(sy * logical_h / screen_h))
            return (lx, ly)
        except Exception:
            return (sx, sy)

    def find_image_file(self, image_path, similarity=0.7):
        """从本地文件读取模板图，在设备屏幕上查找，返回 (x, y, conf) 或 None"""
        if not os.path.exists(image_path):
            logger.warning(f"[{self.name}] 模板图不存在: {image_path}")
            return None
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        return self.find_image(img_b64, similarity)

    def find_image_file_native(self, image_path, similarity=0.7):
        """从本地文件读模板图，用 iMouse 原生识图查找（养号用，更稳）"""
        if not os.path.exists(image_path):
            logger.warning(f"[{self.name}] 模板图不存在: {image_path}")
            return None
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        return self.find_image_native(img_b64, similarity)

    def find_image_bytes(self, img_bytes, similarity=0.7):
        """从字节数据查找模板图，返回 (x, y, conf) 或 None"""
        img_b64 = base64.b64encode(img_bytes).decode()
        return self.find_image(img_b64, similarity)

    # ── 高层 TikTok 操作 ──

    def open_tiktok(self):
        """URL scheme 打开 TikTok。优先 tiktok://（V2.0 实战程序验证过），
        被拒绝时再试 snssdk1233://。返回最后一次调用的响应。"""
        r = self.open_url("tiktok://")
        if r is not None and not self._ok(r):
            r = self.open_url("snssdk1233://")
        time.sleep(random.uniform(4, 6))
        return r

    def swipe_next_video(self):
        """在推荐页上滑切换下一个视频"""
        self.swipe(*self._swipe_pts("swipe_next"))

    def swipe_previous_video(self):
        """下滑回到上一个视频"""
        self.swipe(*self._swipe_pts("swipe_prev"))

    def double_tap_like(self):
        """双击屏幕中央点赞"""
        x, y = self._pt("video_center")
        self.tap(x, y)
        time.sleep(random.uniform(0.1, 0.25))
        self.tap(x, y)

    def tap_like_button(self):
        """点击右侧爱心按钮点赞"""
        self.tap(*self._pt("like_button"))

    def tap_comment_button(self):
        """点击评论按钮"""
        self.tap(*self._pt("comment_button"))

    def tap_share_button(self):
        """点击分享按钮"""
        self.tap(*self._pt("share_button"))

    def tap_follow_button(self):
        """点击头像下方的+号关注"""
        self.tap(*self._pt("follow_button"))

    def tap_avatar(self):
        """点击头像进入主页"""
        self.tap(*self._pt("avatar"))

    def tap_search(self):
        """点击搜索图标"""
        self.tap(*self._pt("search"))

    def tap_home_tab(self):
        """点击底部首页tab"""
        self.tap(*self._pt("home_tab"))

    def tap_discover_tab(self):
        """点击底部发现tab"""
        self.tap(*self._pt("discover_tab"))

    def tap_inbox_tab(self):
        """点击底部收件箱tab"""
        self.tap(*self._pt("inbox_tab"))

    def tap_profile_tab(self):
        """点击底部个人页tab"""
        self.tap(*self._pt("profile_tab"))

    def tap_back(self):
        """点击左上角返回"""
        self.tap(*self._pt("back"))

    def human_wait(self, min_sec=1.0, max_sec=3.0):
        """随机等待，模拟人类操作间隔"""
        time.sleep(random.uniform(min_sec, max_sec))


class DeviceManager:
    """管理单个 iMouse 节点（一台电脑）的设备。
    version='auto' 时自动探测该节点跑的是 Pro 还是 XP，选对应接口。"""

    def __init__(self, host="127.0.0.1", port=None, node_name="本机", version="auto"):
        self.host = host
        self.node_name = node_name
        self.requested_version = (version or "auto").lower()
        self.requested_port = port
        self.backend: Optional[ImouseBackend] = None
        self._ensure_backend()

    # ── 版本探测 / 后端 ──

    def _ensure_backend(self, force=False):
        """探测并创建后端。探测失败时 backend 为 None（节点离线）。"""
        if self.backend is not None and not force:
            return self.backend
        # port=0 / None 视为"用该版本默认端口"；老配置里写死的 9912 若版本是 auto 也忽略
        port = self.requested_port or None
        if self.requested_version == "auto" and port in (9911, 9912):
            port = None
        self.backend = make_backend(self.host, port, self.requested_version)
        if self.backend:
            logger.info(f"[{self.node_name}] iMouse {version_label(self.backend.version)} "
                        f"@ {self.backend.host}:{self.backend.port}")
        else:
            logger.warning(f"[{self.node_name}] 未探测到 iMouse（Pro:9912 / XP:9911 均不通）")
        return self.backend

    @property
    def version(self):
        return self.backend.version if self.backend else None

    @property
    def version_label(self):
        return version_label(self.version)

    @property
    def port(self):
        return self.backend.port if self.backend else (self.requested_port or 0)

    @property
    def api_url(self):
        return self.backend.api_url if self.backend else f"http://{self.host}:{self.port}/api"

    def probe(self, timeout=6):
        """探测节点连通性，返回 (online: bool, device_count: int)。
        区分'离线'(连不上)和'在线但无设备'。会顺便刷新版本探测。"""
        self._ensure_backend(force=True)
        if not self.backend:
            return False, 0
        try:
            devs = self.backend.device_list()
            return True, len(devs)
        except Exception:
            return False, 0

    def _make_device(self, did, info, gmap):
        gid = str(info.get("gid", ""))
        group_name = gmap.get(gid, "")
        # 设备名优先用自定义 name，没有则用 device_name（系统型号）
        name = info.get("name") or info.get("device_name") or did
        return Device(
            device_id=did,
            name=name,
            info=info,
            group_name=group_name,
            node_name=self.node_name,
            backend=self.backend,
        )

    def get_devices(self):
        if not self._ensure_backend():
            logger.error(f"[{self.node_name}] 连接 iMouse 失败：未探测到服务")
            return []
        try:
            gmap = self.backend.group_list()
            data = self.backend.device_list()
            devices = [self._make_device(did, info, gmap) for did, info in data.items()]
            se_count = sum(1 for d in devices if d.model_type == "se")
            logger.info(f"[{self.node_name}] {self.version_label} 获取到 {len(devices)} 台设备 "
                        f"(SE机型: {se_count})")
            return devices
        except Exception as e:
            logger.error(f"[{self.node_name}] 获取设备列表失败: {e}")
            return []

    def get_device_by_name(self, name):
        for dev in self.get_devices():
            if dev.name == name:
                return dev
        return None

    def get_online_devices(self):
        return self.get_devices()
