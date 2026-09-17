"""
iMouse 版本适配层 —— 统一 Pro 版 / XP 版 的接口差异

两个版本的差异（来自官方文档 iosautot.com 及本地 imouse_api*.py）：

                Pro 版                          XP 版
HTTP 端口       9912                            9911
成功判断        status == 0                     status == 200
设备ID字段      deviceid                        id
点击            fun=click                       fun=/mouse/click
滑动            fun=swipe, length               fun=/mouse/swipe, len
按键            fun=send_key                    fun=/key/sendkey
截图            fun=get_device_screenshot       fun=/pic/screenshot
设备列表        fun=get_device_list             fun=/device/get (data.list)
找图            fun=find_image                  fun=/pic/find-image (img_list, data.list[].centre)
OCR             fun=ocr                         fun=/pic/ocr
打开URL         fun=shortcut id=13              fun=/shortcut/exec/url
上传相册        fun=shortcut id=7               fun=/shortcut/album/upload
写剪贴板        fun=shortcut id=10 (hex)        fun=/shortcut/clipboard/set (明文)
读剪贴板        fun=shortcut id=11 (hex)        fun=/shortcut/clipboard/get

用法:
    backend = make_backend("127.0.0.1")            # 自动探测
    backend = make_backend("127.0.0.1", version="xp")
    backend.click(did, 100, 200)
"""
import json
import logging
import requests
from typing import Optional, Dict, Any, Tuple, List

logger = logging.getLogger("automation.backend")

PRO_PORT = 9912
XP_PORT  = 9911


# ─────────────────────────────── 版本探测 ───────────────────────────────

def detect_version(host: str = "127.0.0.1", timeout: float = 3.0) -> Tuple[Optional[str], int]:
    """探测 host 上跑的是哪个版本。返回 ("pro"|"xp"|None, port)。
    依据：Pro 的 HTTP 在 9912，XP 的 HTTP 在 9911。"""
    s = requests.Session()
    # 先试 Pro
    try:
        r = s.post(f"http://{host}:{PRO_PORT}/api",
                   json={"fun": "get_device_list", "data": {}, "msgid": 1},
                   timeout=timeout)
        j = r.json()
        if isinstance(j, dict) and "status" in j:
            return "pro", PRO_PORT
    except Exception:
        pass
    # 再试 XP
    try:
        r = s.post(f"http://{host}:{XP_PORT}/api",
                   json={"fun": "/device/get", "data": {}, "msgid": 1},
                   timeout=timeout)
        j = r.json()
        if isinstance(j, dict) and "status" in j:
            return "xp", XP_PORT
    except Exception:
        pass
    return None, 0


# ─────────────────────────────── 基类 ───────────────────────────────

class ImouseBackend:
    version = "?"
    default_port = 0

    def __init__(self, host: str = "127.0.0.1", port: Optional[int] = None):
        self.host = host
        self.port = port or self.default_port
        self.api_url = f"http://{host}:{self.port}/api"
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.host}:{self.port}>"

    # 底层
    def post(self, fun: str, data: Dict[str, Any], timeout: float = 30,
             quiet: bool = False) -> Optional[Dict[str, Any]]:
        try:
            r = self._session.post(self.api_url,
                                   json={"fun": fun, "data": data, "msgid": 0},
                                   timeout=timeout)
            return r.json()
        except Exception as e:
            if not quiet:
                logger.warning(f"[{self.version}] API调用失败 {fun}: {e}")
            return None

    def ok(self, resp) -> bool:
        raise NotImplementedError

    @staticmethod
    def _data(resp) -> Dict[str, Any]:
        d = (resp or {}).get("data")
        return d if isinstance(d, dict) else {}

    # ── 下面这些由子类实现 ──
    def device_list(self) -> Dict[str, Dict]: raise NotImplementedError
    def group_list(self) -> Dict[str, str]: raise NotImplementedError
    def click(self, did, x, y, button="left", hold=0): raise NotImplementedError
    def swipe(self, did, direction, length=0.5, sx=None, sy=None, ex=None, ey=None, button="left"): raise NotImplementedError
    def send_key(self, did, key="", fn_key=None): raise NotImplementedError
    def send_text(self, did, text): raise NotImplementedError
    def screenshot_b64(self, did) -> Optional[str]: raise NotImplementedError
    def find_image(self, did, img_b64, similarity=0.8, rect=None) -> Optional[Tuple[float, float, float]]: raise NotImplementedError
    def ocr(self, did, rect=None): raise NotImplementedError
    def open_url(self, did, url, outtime=30000): raise NotImplementedError
    def album_upload(self, did, files: List[str], album="Recents", outtime=60000): raise NotImplementedError
    def file_upload(self, did, files: List[str], path="/", outtime=60000): raise NotImplementedError
    def set_clipboard(self, did, text, outtime=15000): raise NotImplementedError
    def get_clipboard(self, did, outtime=15000) -> Optional[str]: raise NotImplementedError


# ─────────────────────────────── Pro 版 ───────────────────────────────

class ProBackend(ImouseBackend):
    version = "pro"
    default_port = PRO_PORT

    def ok(self, resp) -> bool:
        return bool(resp) and resp.get("status") == 0

    def device_list(self) -> Dict[str, Dict]:
        r = self.post("get_device_list", {}, timeout=10)
        if not self.ok(r):
            return {}
        data = r.get("data")
        out: Dict[str, Dict] = {}
        if isinstance(data, dict):
            for did, info in data.items():
                if isinstance(info, dict):
                    out[str(did)] = info
        elif isinstance(data, list):
            for info in data:
                did = str(info.get("deviceid") or info.get("id") or "")
                if did:
                    out[did] = info
        return out

    def group_list(self) -> Dict[str, str]:
        r = self.post("get_group_list", {}, timeout=8, quiet=True)
        gmap: Dict[str, str] = {}
        data = (r or {}).get("data")
        if isinstance(data, dict):
            for gid, g in data.items():
                gmap[str(gid)] = g.get("name", "") if isinstance(g, dict) else str(g)
        elif isinstance(data, list):
            for g in data:
                if isinstance(g, dict):
                    gmap[str(g.get("gid", g.get("id", "")))] = g.get("name", "")
        return gmap

    def click(self, did, x, y, button="left", hold=0):
        return self.post("click", {"deviceid": did, "button": button,
                                   "x": x, "y": y, "time": hold})

    def swipe(self, did, direction, length=0.5, sx=None, sy=None, ex=None, ey=None, button="left"):
        # 严格复刻两种已验证过的报文，不多不少：
        #   方向模式（养号用）: {deviceid, direction, length, sx, sy}      ← v2.0 工具实测可用
        #   全坐标模式:        {deviceid, direction, button, length, sx, sy, ex, ey, for:0}  ← 旧 device.py
        d = {"deviceid": did, "direction": direction, "length": length}
        if sx is not None: d["sx"] = sx
        if sy is not None: d["sy"] = sy
        if ex is not None or ey is not None:
            d["button"] = button
            d["ex"] = ex if ex is not None else 0
            d["ey"] = ey if ey is not None else 0
            d["for"] = 0
        return self.post("swipe", d)

    def send_key(self, did, key="", fn_key=None):
        d = {"deviceid": did, "key": key}
        if fn_key:
            d["fn_key"] = fn_key
        return self.post("send_key", d)

    def send_text(self, did, text):
        return self.post("send_text", {"deviceid": did, "key": text, "fn_key": None})

    def screenshot_b64(self, did) -> Optional[str]:
        r = self.post("get_device_screenshot",
                      {"deviceid": did, "isJpg": True, "gzip": False, "original": False},
                      quiet=True)
        if self.ok(r):
            d = self._data(r)
            return d.get("img") or d.get("screenshot")
        return None

    def find_image(self, did, img_b64, similarity=0.8, rect=None):
        d = {"deviceid": did, "img": img_b64, "similarity": similarity}
        if rect:
            d["rect"] = rect
        r = self.post("find_image", d, quiet=True)
        if r and r.get("status") in (0, 200):
            rd = self._data(r)
            res = rd.get("result")
            if res and len(res) >= 2:
                return (res[0], res[1], rd.get("confidence", 0))
        return None

    def ocr(self, did, rect=None):
        d = {"deviceid": did, "original": False}
        if rect:
            d["rect"] = rect
        r = self.post("ocr", d, quiet=True)
        return self._data(r) if self.ok(r) else None

    # ── 快捷指令（Pro 用数字 id）──
    def _shortcut(self, did, sid, parameter, outtime=30000, devlist=None, timeout=None, quiet=False):
        return self.post("shortcut", {
            "deviceid": did, "id": sid, "devlist": devlist or [],
            "parameter": parameter if isinstance(parameter, str) else json.dumps(parameter),
            "outtime": outtime,
        }, timeout=timeout or (outtime / 1000 + 15), quiet=quiet)

    def open_url(self, did, url, outtime=30000):
        return self._shortcut(did, 13, {"url": url}, outtime)

    def album_upload(self, did, files, album="Recents", outtime=60000):
        return self._shortcut(did, 7, {"name": album or "Recents", "list": files or []},
                              outtime, quiet=True)

    def file_upload(self, did, files, path="/", outtime=60000):
        """上传到手机文件系统（iOS 15+），shortcut id=8，与 V2.0 实战程序一致"""
        return self._shortcut(did, 8, {"path": path or "/", "list": files or []},
                              outtime, quiet=True)

    def set_clipboard(self, did, text, outtime=15000):
        return self._shortcut(did, 10, {"text": text.encode("utf-8").hex()},
                              outtime, devlist=[did])

    def get_clipboard(self, did, outtime=15000) -> Optional[str]:
        r = self._shortcut(did, 11, "{}", outtime, quiet=True)
        if self.ok(r):
            rd = r.get("retdata", {})
            if isinstance(rd, dict) and "text" in rd:
                try:
                    return bytes.fromhex(rd["text"]).decode("utf-8")
                except Exception:
                    return rd["text"]
        return None


# ─────────────────────────────── XP 版 ───────────────────────────────

class XpBackend(ImouseBackend):
    version = "xp"
    default_port = XP_PORT

    def ok(self, resp) -> bool:
        return bool(resp) and resp.get("status") == 200

    @staticmethod
    def _btn(button):
        if button == "left":  return 1
        if button == "right": return 2
        return int(button) if str(button).isdigit() else 1

    def device_list(self) -> Dict[str, Dict]:
        r = self.post("/device/get", {}, timeout=10)
        if not self.ok(r):
            return {}
        data = r.get("data")
        out: Dict[str, Dict] = {}
        items = None
        if isinstance(data, dict):
            if isinstance(data.get("list"), list):
                items = data["list"]
            else:                       # 也可能直接是 {id: info}
                for did, info in data.items():
                    if isinstance(info, dict):
                        out[str(did)] = info
                return out
        elif isinstance(data, list):
            items = data
        for info in items or []:
            if not isinstance(info, dict):
                continue
            did = str(info.get("id") or info.get("deviceid") or "")
            if did:
                out[did] = info
        return out

    def group_list(self) -> Dict[str, str]:
        r = self.post("/device/group/get", {}, timeout=8, quiet=True)
        gmap: Dict[str, str] = {}
        data = (r or {}).get("data")
        items = data.get("list") if isinstance(data, dict) and isinstance(data.get("list"), list) else data
        if isinstance(items, dict):
            for gid, g in items.items():
                gmap[str(gid)] = g.get("name", "") if isinstance(g, dict) else str(g)
        elif isinstance(items, list):
            for g in items:
                if isinstance(g, dict):
                    gmap[str(g.get("id", g.get("gid", "")))] = g.get("name", "")
        return gmap

    def click(self, did, x, y, button="left", hold=0):
        return self.post("/mouse/click", {"id": did, "button": self._btn(button),
                                          "x": x, "y": y, "time": hold})

    def swipe(self, did, direction, length=0.5, sx=None, sy=None, ex=None, ey=None, button="left"):
        # 官方文档：sx/sy/ex/ey 填 0 = 按 len 自动计算；brake=true 防止滑完误点
        d = {"id": did, "direction": direction, "button": self._btn(button), "len": length,
             "sx": sx if sx is not None else 0,
             "sy": sy if sy is not None else 0,
             "ex": ex if ex is not None else 0,
             "ey": ey if ey is not None else 0,
             "steping": 0, "brake": True}
        return self.post("/mouse/swipe", d)

    def send_key(self, did, key="", fn_key=None):
        d = {"id": did, "key": key}
        if fn_key:
            d["fn_key"] = fn_key
        return self.post("/key/sendkey", d)

    def send_text(self, did, text):
        return self.post("/key/sendkey", {"id": did, "key": text, "fn_key": None})

    def screenshot_b64(self, did) -> Optional[str]:
        r = self.post("/pic/screenshot", {"id": did, "binary": False, "jpg": True, "rect": []},
                      quiet=True)
        if self.ok(r):
            d = self._data(r)
            return d.get("img") or d.get("screenshot") or d.get("base64")
        return None

    def find_image(self, did, img_b64, similarity=0.8, rect=None):
        d = {"id": did, "img_list": [img_b64], "similarity": similarity}
        if rect:
            d["rect"] = rect
        r = self.post("/pic/find-image", d, quiet=True)
        if self.ok(r):
            lst = self._data(r).get("list") or []
            if lst and isinstance(lst, list):
                item = lst[0]
                c = item.get("centre") or item.get("center") or []
                if len(c) >= 2:
                    return (c[0], c[1], item.get("similarity", 0))
        return None

    def ocr(self, did, rect=None):
        d = {"id": did, "original": False}
        if rect:
            d["rect"] = rect
        r = self.post("/pic/ocr", d, quiet=True)
        if self.ok(r):
            data = self._data(r)
            return data.get("list") or data
        return None

    def open_url(self, did, url, outtime=30000):
        return self.post("/shortcut/exec/url", {"id": did, "url": url, "outtime": outtime},
                         timeout=outtime / 1000 + 15)

    def album_upload(self, did, files, album="Recents", outtime=60000):
        return self.post("/shortcut/album/upload",
                         {"id": did, "album_name": album or "", "zip": 0,
                          "files": files or [], "outtime": outtime},
                         timeout=outtime / 1000 + 15, quiet=True)

    def file_upload(self, did, files, path="/", outtime=60000):
        """上传到手机文件系统（iOS 15+）。字段按官方文档：path 默认根目录"""
        d = {"id": did, "zip": 0, "files": files or [], "outtime": outtime}
        if path and path != "/":
            d["path"] = path
        return self.post("/shortcut/file/upload", d,
                         timeout=outtime / 1000 + 15, quiet=True)

    def set_clipboard(self, did, text, outtime=15000):
        return self.post("/shortcut/clipboard/set",
                         {"id": did, "text": text, "sleep": 0, "outtime": outtime},
                         timeout=outtime / 1000 + 15)

    def get_clipboard(self, did, outtime=15000) -> Optional[str]:
        r = self.post("/shortcut/clipboard/get", {"id": did, "outtime": outtime},
                      timeout=outtime / 1000 + 15, quiet=True)
        if self.ok(r):
            rd = r.get("data", {})
            if isinstance(rd, dict):
                return rd.get("text", "")
            return rd or None
        return None


# ─────────────────────────────── 工厂 ───────────────────────────────

_BACKENDS = {"pro": ProBackend, "xp": XpBackend}


def make_backend(host: str = "127.0.0.1", port: Optional[int] = None,
                 version: str = "auto", timeout: float = 3.0) -> Optional[ImouseBackend]:
    """按 version 创建后端。version='auto' 时自动探测。
    port 传 None/0 表示用该版本的默认端口。探测失败返回 None。"""
    v = (version or "auto").lower()
    if v == "auto":
        v, detected_port = detect_version(host, timeout)
        if v is None:
            return None
        port = port or detected_port
    cls = _BACKENDS.get(v)
    if not cls:
        raise ValueError(f"未知的 iMouse 版本: {version}（只支持 pro / xp / auto）")
    return cls(host, port or None)


def version_label(v: Optional[str]) -> str:
    return {"pro": "专业版", "xp": "XP版"}.get((v or "").lower(), "未知")
