import base64
import json
import os
import time
import random
import logging
import requests
from io import BytesIO

from .coordinates import get_coords, detect_model_type

logger = logging.getLogger("automation.device")


class Device:
    """对单个 iMouse 设备的操作封装，提供高层 TikTok 交互方法"""

    def __init__(self, device_id, name, api_url, info=None, group_name="",
                 node_name="本机"):
        self.device_id = device_id
        self.name = name
        self.api_url = api_url
        self.info = info or {}
        self.group_name = group_name
        self.node_name = node_name      # 所属节点（哪台电脑）
        # 机型识别 + 加载对应坐标
        self.model_type = detect_model_type(self.info, group_name)
        self.coords = get_coords(self.model_type)
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def __repr__(self):
        return (f"Device({self.name!r}, id={self.device_id!r}, "
                f"type={self.model_type}, node={self.node_name!r})")

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

    # ── 底层 API 调用 ──

    def _post(self, fun, data, quiet=False):
        try:
            r = self._session.post(
                self.api_url,
                json={"fun": fun, "data": data, "msgid": 0},
                timeout=30,
            )
            return r.json()
        except Exception as e:
            if not quiet:
                logger.warning(f"[{self.name}] API调用失败 {fun}: {e}")
            return None

    # ── 基础操作 ──

    def tap(self, x, y):
        logger.debug(f"[{self.name}] tap({x}, {y})")
        return self._post("click", {
            "deviceid": self.device_id, "button": "left",
            "x": x, "y": y, "time": 0,
        })

    def swipe(self, sx, sy, ex, ey, length=0.9):
        direction = "up" if ey < sy else "down" if ey > sy else ("left" if ex < sx else "right")
        logger.debug(f"[{self.name}] swipe {direction} ({sx},{sy})->({ex},{ey})")
        return self._post("swipe", {
            "deviceid": self.device_id, "direction": direction,
            "button": "left", "length": length,
            "sx": sx, "sy": sy, "ex": ex, "ey": ey, "for": 0,
        })

    def swipe_dir(self, direction, length=0.5, sx=None, sy=None):
        """按方向+距离滑动（与验证过的养号流程一致，只给方向+距离+起点）"""
        logger.debug(f"[{self.name}] swipe_dir {direction} len={length} ({sx},{sy})")
        data = {"deviceid": self.device_id, "direction": direction, "length": length}
        if sx is not None:
            data["sx"] = sx
        if sy is not None:
            data["sy"] = sy
        return self._post("swipe", data)

    def press_home(self):
        """回主屏幕（用 WIN+h，与验证过的养号/发布流程一致）"""
        logger.debug(f"[{self.name}] press_home")
        return self._post("send_key", {
            "deviceid": self.device_id, "key": "", "fn_key": "WIN+h",
        })

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
        # devlist 传空（与验证过的养号流程一致），只对 deviceid 生效
        logger.debug(f"[{self.name}] open_url: {url}")
        return self._post("shortcut", {
            "deviceid": self.device_id, "id": 13,
            "devlist": [],
            "parameter": json.dumps({"url": url}),
            "outtime": 30000,
        })

    def send_key(self, key="", fn_key=None):
        """发送按键，如 fn_key='HOME' 返回主屏幕"""
        data = {"deviceid": self.device_id, "key": key}
        if fn_key:
            data["fn_key"] = fn_key
        return self._post("send_key", data)

    def send_text(self, text):
        """发送批量字符（直接输入文本框）"""
        return self._post("send_text", {
            "deviceid": self.device_id, "key": text, "fn_key": None,
        })

    def send_clipboard(self, text):
        hex_text = text.encode("utf-8").hex()
        return self._post("shortcut", {
            "deviceid": self.device_id, "id": 10,
            "devlist": [self.device_id],
            "parameter": json.dumps({"text": hex_text}),
            "outtime": 15000,
        })

    def get_clipboard(self):
        r = self._post("shortcut", {
            "deviceid": self.device_id, "id": 11,
            "parameter": "{}",
            "outtime": 15000,
        }, quiet=True)
        if r and r.get("status") == 0:
            rd = r.get("retdata", {})
            if isinstance(rd, dict) and "text" in rd:
                try:
                    return bytes.fromhex(rd["text"]).decode("utf-8")
                except Exception:
                    return rd["text"]
        return None

    def screenshot_b64(self):
        r = self._post("get_device_screenshot", {
            "deviceid": self.device_id, "isJpg": True,
            "gzip": False, "original": False,
        }, quiet=True)
        if r and r.get("status") == 0:
            d = r.get("data", {})
            return d.get("img") or d.get("screenshot")
        return None

    def ocr(self, rect=None):
        data = {"deviceid": self.device_id, "original": False}
        if rect:
            data["rect"] = rect
        r = self._post("ocr", data, quiet=True)
        if r and r.get("status") == 0:
            return r.get("data", {})
        return None

    def find_image_native(self, img_b64, similarity=0.7, rect=None):
        """iMouse 原生识图（服务端匹配），返回 (x, y, conf) 或 None。
        与验证过的养号流程一致，不做本地cv匹配，避免误匹配 + 减少截图。"""
        data = {
            "deviceid": self.device_id,
            "img": img_b64, "similarity": similarity,
        }
        if rect:
            data["rect"] = rect
        r = self._post("find_image", data, quiet=True)
        if r and r.get("status") in (0, 200):
            rd = r.get("data", {})
            result = rd.get("result")
            if result and len(result) >= 2:
                return (result[0], result[1], rd.get("confidence", 0))
        return None

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
        self.open_url("snssdk1233://")
        time.sleep(random.uniform(4, 6))

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
    """管理单个 iMouse 节点（一台电脑）的设备"""

    def __init__(self, host="127.0.0.1", port=9912, node_name="本机"):
        self.host = host
        self.port = port
        self.node_name = node_name
        self.api_url = f"http://{host}:{port}/api"
        self._session = requests.Session()

    def probe(self, timeout=6):
        """探测节点连通性，返回 (online: bool, device_count: int)。
        区分'离线'(连不上)和'在线但无设备'。"""
        try:
            r = self._session.post(
                self.api_url,
                json={"fun": "get_device_list", "data": {}, "msgid": 1},
                timeout=timeout,
            )
            resp = r.json()
            data = resp.get("data")
            count = len(data) if isinstance(data, (dict, list)) else 0
            return True, count
        except Exception:
            return False, 0

    def _get_group_map(self):
        """获取 gid -> 组名 映射"""
        gmap = {}
        try:
            r = self._session.post(
                self.api_url,
                json={"fun": "get_group_list", "data": {}, "msgid": 9},
                timeout=8,
            )
            data = r.json().get("data")
            if isinstance(data, dict):
                for gid, ginfo in data.items():
                    if isinstance(ginfo, dict):
                        gmap[str(gid)] = ginfo.get("name", "")
                    else:
                        gmap[str(gid)] = str(ginfo)
            elif isinstance(data, list):
                for ginfo in data:
                    if isinstance(ginfo, dict):
                        gid = str(ginfo.get("gid", ginfo.get("id", "")))
                        gmap[gid] = ginfo.get("name", "")
        except Exception as e:
            logger.debug(f"获取分组列表失败（将用分辨率/型号判断机型）: {e}")
        return gmap

    def _make_device(self, did, info, gmap):
        gid = str(info.get("gid", ""))
        group_name = gmap.get(gid, "")
        # 设备名优先用自定义 name，没有则用 device_name（系统型号）
        name = info.get("name") or info.get("device_name") or did
        return Device(
            device_id=did,
            name=name,
            api_url=self.api_url,
            info=info,
            group_name=group_name,
            node_name=self.node_name,
        )

    def get_devices(self):
        try:
            gmap = self._get_group_map()
            r = self._session.post(
                self.api_url,
                json={"fun": "get_device_list", "data": {}, "msgid": 1},
                timeout=10,
            )
            resp = r.json()
            if resp.get("status") != 0:
                logger.error(f"获取设备列表失败: {resp}")
                return []
            data = resp.get("data", {})
            devices = []
            if isinstance(data, dict):
                for did, info in data.items():
                    if isinstance(info, dict):
                        devices.append(self._make_device(did, info, gmap))
            elif isinstance(data, list):
                for info in data:
                    did = info.get("deviceid", "")
                    devices.append(self._make_device(did, info, gmap))
            se_count = sum(1 for d in devices if d.model_type == "se")
            logger.info(f"获取到 {len(devices)} 台设备 (SE机型: {se_count})")
            return devices
        except Exception as e:
            logger.error(f"连接 iMouse 失败: {e}")
            return []

    def get_device_by_name(self, name):
        for dev in self.get_devices():
            if dev.name == name:
                return dev
        return None

    def get_online_devices(self):
        return self.get_devices()
