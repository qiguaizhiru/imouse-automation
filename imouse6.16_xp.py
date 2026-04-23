# iMouse XP 自动化工具 (adapted from Pro version)
# Port: 9911, XP API endpoints
# Reconstructed from imouse6.16.pyc (Python 3.12)
# iMouse Pro 自动化工具
import base64
import gzip
import io
import re
import json
import os
import sys
import time
import threading
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
import pandas as pd
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPixmap, QImage
from PyQt6.QtWidgets import QAbstractItemView, QGraphicsPixmapItem, QGraphicsScene, QApplication

import imouse_api_xp as imouse_api
from tiktok_form import Ui_MainWindow

# ═══════════════════════════════════════════════════════════════════════
# 投流码自动化模块常量与配置
# ═══════════════════════════════════════════════════════════════════════
FEISHU_APP_ID       = "cli_a99b14fa3b7d900d"
FEISHU_APP_SECRET   = "ZTawO0DxS1k06DTXYEiDAg8ACWaGCONz"
FEISHU_APP_TOKEN    = "NOulwz2X3i6Eg9kU9L0cnh8Qnyg"
ACCOUNT_TABLE_ID    = "tblqIhS037A7v99R"
ACCOUNT_VIEW_ID     = "vewlHYA0vk"
# 视频表"账号编号"字段关联的是旧账号表，写视频时仍需用旧表的record_id
OLD_ACCOUNT_TABLE_ID = "tblSQjP08dsoCoP9"
OLD_ACCOUNT_FIELD_ACCOUNT_ID = "账号id"  # 旧表是小写id
# 测试表（仅用于测试完播率流程，不影响正式表）
TEST_APP_TOKEN      = "Vt8IbKPMAahSyhs2m6fcNxVWn1c"
TEST_VIDEO_TABLE_ID = "tblkwoSrb1GkoM1J"
TEST_VIDEO_VIEW_ID  = "vew2Yve4BL"
VIDEO_TABLE_ID      = "tbld59fY7wCYtEsC"
VIDEO_VIEW_ID       = "vew2Yve4BL"
VIDEO_FIELDS = {
    "account_link": "账号编号", "video_link": "视频发布链接", "publish_date": "发布日期",
    "play_count": "T7 播放量", "like_count": "T7 点赞量", "ad_code": "投流码",
    "upload_time": "上传时间", "account_id": "账号id", "share_url": "分享链接",
    "publish_date_text": "发布日期-20260305", "vid": "vid",
    "completion_rate": "T7 完播率",
}
ACCOUNT_FIELDS = {"account_id": "账号ID", "account_name": "账号昵称", "status": "使用状态", "usage": "使用人"}
TIKHUB_BASE_URL = "https://api.tikhub.io"
TIKHUB_TOKEN = "5+UtWGJ7zHdyjAoejG6rpUMM9CsrpZPAvIpF4Dm/vkhx7xAXcu9C+AHsCA=="
IMOUSE_XP_PORT = 9911
PHASE2_DEFAULT_WORKERS = 20
T_APP_LAUNCH = 6.0; T_PAGE_LOAD = 3.5; T_CLICK = 1.5; T_SWIPE = 2.0
TIKTOK_SCHEME = "snssdk1233://"

# ── 自动更新配置 ──
LOCAL_VERSION = "2.3.0"
UPDATE_CHANNEL = "xp"  # "pro" 或 "xp"
UPDATE_URLS = [
    # GitHub raw 原生（始终最新，无CDN缓存问题）
    "https://raw.githubusercontent.com/qiguaizhiru/imouse-automation/main",
    # GitHub 反代（国内快）
    "https://ghfast.top/https://raw.githubusercontent.com/qiguaizhiru/imouse-automation/main",
    # jsDelivr 备用（有CDN缓存但速度快）
    "https://fastly.jsdelivr.net/gh/qiguaizhiru/imouse-automation@main",
    "https://gcore.jsdelivr.net/gh/qiguaizhiru/imouse-automation@main",
    "https://cdn.jsdmirror.com/gh/qiguaizhiru/imouse-automation@main",
    "https://cdn.jsdelivr.net/gh/qiguaizhiru/imouse-automation@main",
    # 更多反代
    "https://ghproxy.com/https://raw.githubusercontent.com/qiguaizhiru/imouse-automation/main",
    "https://mirror.ghproxy.com/https://raw.githubusercontent.com/qiguaizhiru/imouse-automation/main",
]

def _version_ge(v1, v2):
    """比较版本号: v1 >= v2 返回 True"""
    try:
        t1 = tuple(int(x) for x in v1.split('.'))
        t2 = tuple(int(x) for x in v2.split('.'))
        # 补齐长度
        maxlen = max(len(t1), len(t2))
        t1 = t1 + (0,) * (maxlen - len(t1))
        t2 = t2 + (0,) * (maxlen - len(t2))
        return t1 >= t2
    except Exception:
        return v1 == v2
VIDEO_GRID = {1:(90,540),2:(255,540),3:(410,550),4:(90,760),5:(255,760),6:(410,760)}
PX = {"profile_tab":(450,1000),"three_dots":(463,829),"ad_auth_toggle":(444,351),
      "authorize":(250,990),"save":(250,990),"manage":(420,560),"copy_code":(255,886),
      "back":(30,90),"allow_popup":(290,495),"always_allow":(191,719)}
SWIPE_ROW_Y=990; SWIPE_START_X=485; SWIPE_END_X=8
ICON_SIM=0.7; SKIP_POPUP_CHECK=True
AD_ICON_FILE="ad_settings_icon.png"; AD_SEARCH_RECT=[[0,900],[0,1020],[500,900],[500,1020]]
AD_FALLBACK_POSITIONS=[(280,957),(280,957)]
AD_AUTH_ON_ICON_FILE="ad_auth_on.png"; AD_AUTH_ON_ICON_SIM=0.75
AD_AUTH_ON_SEARCH_RECT=[[350,300],[350,400],[500,300],[500,400]]
COPY_LINK_ICON_FILE="copy_link_icon.png"; COPY_LINK_SEARCH_RECT=[[0,800],[0,1100],[500,800],[500,1100]]
COPY_LINK_FALLBACK=(100,960)
THREE_DOTS_ICON_FILE="icon/three_dots_icon.bmp"; THREE_DOTS_ICON_SIM=0.70
THREE_DOTS_SEARCH_RECT=[[300,600],[300,1100],[500,600],[500,1100]]
DONT_ALLOW_ICON_FILE="icon/dont_allow.bmp"; DONT_ALLOW_SIM=0.70
DONT_ALLOW_SEARCH_RECT=[[0,0],[0,1100],[500,0],[500,1100]]  # 全屏
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 投流码: HTTP API 客户端 (直连 iMouse XP 9911 端口) ──
class _IMouseXPClient:
    def __init__(self, server, port):
        self.base_url = f"http://{server}:{port}/api"
        self.session = _requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    def _post(self, fun, data, quiet=False):
        try:
            r = self.session.post(self.base_url, json={"fun":fun,"data":data}, timeout=30)
            return r.json()
        except: return None
    def get_devices(self):
        r = self._post("/device/get", {})
        if r and r.get("status")==200:
            d = r.get("data",{})
            if isinstance(d, dict):
                lst = d.get("list", [])
                if isinstance(lst, list): return lst
            return d if isinstance(d, list) else []
        return []
    def tap(self, did, x, y):
        return self._post("/mouse/click",{"id":did,"button":1,"x":x,"y":y,"time":0})
    def swipe(self, did, sx, sy, ex, ey):
        # 参照开发者工具实测: direction=right, 不传len, step_sleep=0, brake=False
        return self._post("/mouse/swipe",{"id":did,"direction":"right","button":1,
                                    "sx":sx,"sy":sy,"ex":ex,"ey":ey,
                                    "step_sleep":0})
    def press_home(self, did):
        return self._post("/key/sendkey",{"id":did,"key":"","fn_key":"WIN+h"})
    def open_url(self, did, url):
        return self._post("/shortcut/exec/url",{"id":did,"url":url})
    def get_clipboard(self, did):
        r = self._post("/shortcut/clipboard/get",{"id":did}, quiet=True)
        if r is None or r.get("status")!=200: return None
        rd = r.get("data",{})
        if isinstance(rd,dict): return rd.get("text","")
        return rd or None
    def find_image(self, did, img_b64, similarity=0.8, rect=None):
        # 优先用本地 cv2 模板匹配（截图+本地匹配，比iMouse原生识图精度高）
        scr = _get_screen_b64(self, did)
        if scr:
            r = _cv_find_image(scr, img_b64, similarity, rect)
            if r: return r
        # Fallback: iMouse 原生识图 API
        data = {"id":did,"img_list":[img_b64],"similarity":similarity}
        if rect: data["rect"]=rect
        r = self._post("/pic/find-image", data, quiet=True)
        if r and r.get("status")==200:
            rd=r.get("data",{}); lst=rd.get("list",[])
            if lst and isinstance(lst,list) and len(lst)>0:
                item=lst[0]; centre=item.get("centre",[0,0]); sim=item.get("similarity",0)
                if len(centre)>=2: return (centre[0],centre[1],sim)
        return None
    def ocr(self, did, rect=None):
        """OCR文字识别 - XP返回gdata.list"""
        data = {"id":did}
        r2 = self._conv_rect(rect, is_xywh=True)
        if r2: data["rect"] = r2
        r = self._post("/pic/ocr", data, quiet=True)
        if r and r.get("status")==200:
            d = r.get("data",{})
            lst = d.get("list",[]) if isinstance(d,dict) else []
            if isinstance(lst, list) and lst: return lst
            return d
        return None
    def drag(self, did, sx, sy, ex, ey, duration=500, steps=20):
        """拖拽操作: mouse_move定位 -> mouse_down -> 分步mouse_move -> mouse_up"""
        self._post("/mouse/move", {"id": did, "x": sx, "y": sy})
        time.sleep(0.1)
        self._post("/mouse/down", {"id": did, "button": 1})
        time.sleep(1.0)
        for i in range(1, steps + 1):
            mx = int(sx + (i / steps) * (ex - sx))
            my = int(sy + (i / steps) * (ey - sy))
            self._post("/mouse/move", {"id": did, "x": mx, "y": my})
            time.sleep(0.05)
        time.sleep(0.1)
        self._post("/mouse/up", {"id": did, "button": 1})
    def drag_to(self, did, sx, sy, ex, ey, steps=20):
        """按下并拖到终点但不松手，需手动调用 mouse_release"""
        self._post("/mouse/move", {"id": did, "x": sx, "y": sy})
        time.sleep(0.1)
        self._post("/mouse/down", {"id": did, "button": 1})
        time.sleep(1.0)
        for i in range(1, steps + 1):
            mx = int(sx + (i / steps) * (ex - sx))
            my = int(sy + (i / steps) * (ey - sy))
            self._post("/mouse/move", {"id": did, "x": mx, "y": my})
            time.sleep(0.05)
    def mouse_release(self, did, x, y):
        """松开鼠标"""
        self._post("/mouse/up", {"id": did, "button": 1})
    def swipe_vertical(self, did, start_y, end_y, x=200):
        """垂直滑动"""
        direction = "up" if end_y < start_y else "down"
        return self._post("/mouse/swipe",{"id":did,"direction":direction,"button":1,
                                    "sx":x,"sy":start_y,"ex":x,"ey":end_y,
                                    "step_sleep":0})
    def fix_landscape(self, did, log=None):
        """检测横屏并点击(834,39)返回个人页，返回True表示触发了横屏修正"""
        try:
            import base64 as _b64
            from io import BytesIO
            from PIL import Image as _PIL
            ss = self._post("/pic/screenshot", {"id": did, "jpg": True})
            if not ss or ss.get("status") != 200:
                return False
            _d = ss.get("data", {})
            img_b64 = _d.get("img") or _d.get("screenshot")
            if not img_b64:
                return False
            img = _PIL.open(BytesIO(_b64.b64decode(img_b64)))
            w, h = img.size
            if w > h:  # 横屏
                if log: log(f"  [{did}] 检测到横屏 ({w}x{h})，点击(834,39)返回个人页")
                self.tap(did, 834, 39)
                time.sleep(1.5)
                return True
        except Exception as _e:
            if log: log(f"  [{did}] 横屏检测异常: {_e}")
        return False

# ── 投流码: 飞书客户端 ──
class _FeishuClient:
    BASE_URL = "https://open.feishu.cn"
    def __init__(self, app_id, app_secret, app_token):
        self.app_id,self.app_secret,self.app_token = app_id,app_secret,app_token
        self._token=None; self._token_expiry=0; self._s=_requests.Session()
    def _get_token(self):
        now=time.time()
        if self._token and now<self._token_expiry-60: return self._token
        r=self._s.post(f"{self.BASE_URL}/open-apis/auth/v3/tenant_access_token/internal",
                       json={"app_id":self.app_id,"app_secret":self.app_secret},timeout=30).json()
        if r.get("code")!=0: raise RuntimeError(f"飞书token失败:{r}")
        self._token=r["tenant_access_token"]; self._token_expiry=now+r.get("expire",7200)
        return self._token
    def _headers(self):
        return {"Authorization":f"Bearer {self._get_token()}","Content-Type":"application/json"}
    def search_records(self, table_id, filter_obj=None, view_id=None):
        records=[]; page_token=None
        while True:
            params=[("page_size","500")]
            if page_token: params.append(("page_token",page_token))
            body={}
            if filter_obj: body["filter"]=filter_obj
            if view_id: body["view_id"]=view_id
            r=self._s.post(f"{self.BASE_URL}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/search",
                           headers=self._headers(),params=params,json=body,timeout=30).json()
            if r.get("code")!=0: raise RuntimeError(f"搜索失败:{r.get('msg')}")
            d=r.get("data",{}); records.extend(d.get("items") or [])
            page_token=d.get("page_token")
            if not page_token: break
        return records
    def batch_update_records(self, table_id, updates):
        if not updates: return 0
        for i in range(0,len(updates),500):
            self._s.post(f"{self.BASE_URL}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_update",
                         headers=self._headers(),json={"records":updates[i:i+500]},timeout=30)
        return len(updates)
    def batch_create_records(self, table_id, records):
        if not records: return []
        ids=[]
        for i in range(0,len(records),500):
            r=self._s.post(f"{self.BASE_URL}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_create",
                           headers=self._headers(),json={"records":[{"fields":rc} for rc in records[i:i+500]]},timeout=30).json()
            for rec in (r.get("data",{}).get("records") or []): ids.append(rec.get("record_id"))
        return ids

# ── 投流码: TikHub 客户端 (app/v3 优先，失败 fallback 到 web) ──
class _TikHubClient:
    def __init__(self):
        self._s=_requests.Session()
        self._s.headers.update({"Authorization":f"Bearer {TIKHUB_TOKEN}","accept":"application/json"})
    def _get(self, ep, params):
        """优化策略: 200立即返回, 400业务失败直接放弃让fallback接手, 429/网络异常才重试"""
        for i in range(3):
            try:
                r=self._s.get(f"{TIKHUB_BASE_URL}{ep}",params=params,timeout=20)
                if r.status_code==200: return r.json()
                if r.status_code==400: return None  # 业务失败，立即让上层 fallback
                if r.status_code==429: time.sleep(3); continue  # 限流，短等待
                if r.status_code>=500: time.sleep(1); continue  # 服务端错误，短等待
                return None  # 其他状态码不重试
            except Exception:
                if i<2: time.sleep(1)  # 网络异常，短等待重试
        return None
    def fetch_user_info(self, uid):
        """获取 secUid: 先 app/v3，失败 fallback web"""
        # app/v3
        d=self._get("/api/v1/tiktok/app/v3/get_user_id_and_sec_user_id_by_username",{"username":uid})
        if d:
            inner=d.get("data",{}); sec=inner.get("sec_user_id","")
            if sec: return {"sec_uid":sec,"source":"app_v3"}
        # fallback: web
        d=self._get("/api/v1/tiktok/web/fetch_user_profile",{"uniqueId":uid})
        if d:
            user_info=d.get("data",{}).get("userInfo",d.get("data",{}))
            user=user_info.get("user",user_info)
            sec=user.get("secUid","")
            if sec: return {"sec_uid":sec,"source":"web"}
        return None
    def fetch_user_videos(self, sec_uid, max_count=30, publish_after=None, unique_id=None):
        """获取用户视频: V3 → V2 → V1 → Web 四层 fallback

        前三个 app/v3 接口优先用 unique_id（省一次 sec_uid 查询）
        """
        # 1) V3 (最快)
        videos = self._fetch_videos_appv3(sec_uid, max_count, publish_after, ep="fetch_user_post_videos_v3", unique_id=unique_id)
        if videos: return videos
        # 2) V2
        videos = self._fetch_videos_appv3(sec_uid, max_count, publish_after, ep="fetch_user_post_videos_v2", unique_id=unique_id)
        if videos: return videos
        # 3) V1
        videos = self._fetch_videos_appv3(sec_uid, max_count, publish_after, ep="fetch_user_post_videos", unique_id=unique_id)
        if videos: return videos
        # 4) Web (需要 sec_uid)
        if not sec_uid: return []
        return self._fetch_videos_web(sec_uid, max_count, publish_after)
    def _fetch_videos_appv3(self, sec_uid, max_count, publish_after, ep="fetch_user_post_videos_v3", unique_id=None):
        """V1/V2/V3 通用: 优先用 unique_id, 没有就用 sec_user_id"""
        videos=[]; cursor=0
        while len(videos)<max_count:
            params = {"count": min(30, max_count-len(videos)), "max_cursor": cursor, "sort_type": 0}
            if unique_id:
                params["unique_id"] = unique_id
            elif sec_uid:
                params["sec_user_id"] = sec_uid
            else:
                return []
            d=self._get(f"/api/v1/tiktok/app/v3/{ep}", params)
            if not d: return []
            inner=d.get("data",{})
            aweme_list = inner.get("aweme_list") or []
            if not aweme_list and cursor == 0: return []  # 第一页空，直接返回
            for a in aweme_list:
                aid=str(a.get("aweme_id") or a.get("id") or "")
                if not aid: continue
                ct=int(a.get("create_time") or 0)
                if publish_after and ct<publish_after: continue
                si=a.get("share_info") or {}
                videos.append({"aweme_id":aid,"create_time":ct,
                    "play_count":int((a.get("statistics") or {}).get("play_count") or 0),
                    "digg_count":int((a.get("statistics") or {}).get("digg_count") or 0),
                    "share_url":a.get("share_url") or si.get("share_url") or "",
                    "is_pinned":bool(a.get("is_top"))})
            if not inner.get("has_more"): break
            cursor=inner.get("max_cursor",0); time.sleep(0.5)
        return videos
    def _fetch_videos_web(self, sec_uid, max_count, publish_after):
        videos=[]; cursor=0
        while len(videos)<max_count:
            d=self._get("/api/v1/tiktok/web/fetch_user_post",
                        {"secUid":sec_uid,"count":min(20,max_count-len(videos)),"cursor":cursor})
            if not d: return []
            inner=d.get("data",{})
            items = inner.get("itemList") or inner.get("items") or []
            if not items and cursor == 0: return []
            for a in items:
                aid=str(a.get("id") or a.get("aweme_id") or "")
                if not aid: continue
                ct=int(a.get("createTime") or 0)
                if publish_after and ct<publish_after: continue
                stats=a.get("stats") or a.get("statistics") or {}
                videos.append({"aweme_id":aid,"create_time":ct,
                    "play_count":int(stats.get("playCount") or stats.get("play_count") or 0),
                    "digg_count":int(stats.get("diggCount") or stats.get("digg_count") or 0),
                    "share_url":f"https://www.tiktok.com/@{a.get('author',{}).get('uniqueId','')}/video/{aid}",
                    "is_pinned":bool(a.get("isPinnedItem") or a.get("is_top"))})
            if not inner.get("hasMore"): break
            cursor=inner.get("cursor",0); time.sleep(0.5)
        return videos
    def resolve_share_url(self, url):
        m=re.search(r'/video/(\d+)',url)
        if m: return m.group(1)
        # app/v3
        d=self._get("/api/v1/tiktok/app/v3/fetch_one_video_by_share_url",{"share_url":url})
        if d:
            a=d.get("data",{}).get("aweme_detail") or d.get("data",{})
            aid=str(a.get("aweme_id") or a.get("id") or "")
            if aid: return aid
        return None
    def fetch_video_stats(self, share_url):
        """获取视频统计: 先 app/v3，失败 fallback web"""
        # app/v3
        d=self._get("/api/v1/tiktok/app/v3/fetch_one_video_by_share_url",{"share_url":share_url})
        if d:
            a=d.get("data",{}).get("aweme_detail") or d.get("data",{})
            stats=a.get("statistics") or {}
            aid=str(a.get("aweme_id") or a.get("id") or "")
            if aid:
                return {"aweme_id":aid,
                    "play_count":int(stats.get("play_count") or 0),
                    "digg_count":int(stats.get("digg_count") or 0),
                    "comment_count":int(stats.get("comment_count") or 0),
                    "share_count":int(stats.get("share_count") or 0)}
        # fallback: web
        item_id=None
        m=re.search(r'/video/(\d+)',share_url)
        if m: item_id=m.group(1)
        if not item_id: return None
        d=self._get("/api/v1/tiktok/web/fetch_post_detail",{"itemId":item_id})
        if d:
            a=d.get("data",{}).get("itemInfo",{}).get("itemStruct",d.get("data",{}))
            stats=a.get("stats") or {}
            return {"aweme_id":str(a.get("id") or ""),
                "play_count":int(stats.get("playCount") or stats.get("play_count") or 0),
                "digg_count":int(stats.get("diggCount") or stats.get("digg_count") or 0),
                "comment_count":int(stats.get("commentCount") or 0),
                "share_count":int(stats.get("shareCount") or 0)}
        return None

# ── 投流码: 工具函数 ──
_ICON_B64_CACHE = {}
def _load_icon(fn):
    if fn in _ICON_B64_CACHE: return _ICON_B64_CACHE[fn]
    p=os.path.join(SCRIPT_DIR,fn)
    if not os.path.exists(p): _ICON_B64_CACHE[fn]=None; return None
    with open(p,"rb") as f: v=base64.b64encode(f.read()).decode()
    _ICON_B64_CACHE[fn]=v; return v

# 本地 OpenCV 模板匹配（比 iMouse 原生识图更稳）
_CV_AVAILABLE = None
def _cv_find_image(screen_b64, tpl_b64, similarity=0.8, rect=None):
    """本地模板匹配，返回 (center_x, center_y, confidence) 或 None
    screen_b64: 截图的 base64 字符串
    tpl_b64: 模板图的 base64 字符串
    rect: 搜索区域。支持两种格式:
        - 4角点 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        - 边界框 [lx, ty, rx, by] 或 [x, y, w, h]（自动识别）
    """
    global _CV_AVAILABLE
    if _CV_AVAILABLE is False: return None
    try:
        if _CV_AVAILABLE is None:
            import cv2 as _cv2, numpy as _np
            _CV_AVAILABLE = True
        else:
            import cv2 as _cv2, numpy as _np
        screen_bytes = base64.b64decode(screen_b64) if isinstance(screen_b64, str) else screen_b64
        tpl_bytes = base64.b64decode(tpl_b64) if isinstance(tpl_b64, str) else tpl_b64
        screen_arr = _np.frombuffer(screen_bytes, _np.uint8)
        screen_img = _cv2.imdecode(screen_arr, _cv2.IMREAD_COLOR)
        tpl_arr = _np.frombuffer(tpl_bytes, _np.uint8)
        tpl_img = _cv2.imdecode(tpl_arr, _cv2.IMREAD_COLOR)
        if screen_img is None or tpl_img is None: return None
        h_scr, w_scr = screen_img.shape[:2]
        h_tpl, w_tpl = tpl_img.shape[:2]
        # 裁搜索区
        ox, oy = 0, 0
        if rect:
            try:
                if len(rect) == 4 and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in rect):
                    # 4 角点
                    xs = [p[0] for p in rect]; ys = [p[1] for p in rect]
                    lx, ty, rx, by = min(xs), min(ys), max(xs), max(ys)
                elif len(rect) == 4:
                    # [lx, ty, rx, by] 或 [x,y,w,h] - 启发式识别
                    a, b, c, d = rect
                    if c > a and d > b and c <= w_scr and d <= h_scr:
                        lx, ty, rx, by = a, b, c, d  # [lx,ty,rx,by]
                    else:
                        lx, ty, rx, by = a, b, a+c, b+d  # [x,y,w,h]
                else:
                    lx, ty, rx, by = 0, 0, w_scr, h_scr
                lx = max(0, min(lx, w_scr)); rx = max(0, min(rx, w_scr))
                ty = max(0, min(ty, h_scr)); by = max(0, min(by, h_scr))
                if rx - lx < w_tpl or by - ty < h_tpl:
                    return None  # 搜索区比模板小，模板匹配会失败
                screen_img = screen_img[ty:by, lx:rx]
                ox, oy = lx, ty
            except Exception: pass
        # 模板匹配
        result = _cv2.matchTemplate(screen_img, tpl_img, _cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = _cv2.minMaxLoc(result)
        if max_val < similarity: return None
        cx = max_loc[0] + w_tpl // 2 + ox
        cy = max_loc[1] + h_tpl // 2 + oy
        return (int(cx), int(cy), float(max_val))
    except ImportError:
        _CV_AVAILABLE = False
        return None
    except Exception:
        return None

def _get_screen_b64(c, did):
    """获取设备截图的base64字符串，兼容Pro和XP"""
    # 先尝试 XP 风格
    try:
        ss = c._post("/pic/screenshot", {"id": did, "jpg": True})
        if ss and ss.get("status") == 200:
            d = ss.get("data", {})
            img = d.get("img") or d.get("screenshot") or d.get("base64")
            if img: return img
    except Exception: pass
    # 再尝试 Pro 风格
    try:
        ss = c._post("/pic/screenshot", {"id": did, "jpg": True})
        if ss and ss.get("status") == 0:
            d = ss.get("data", {})
            img = d.get("img") or d.get("screenshot")
            if img: return img
    except Exception: pass
    return None

def _normalize_account_id(raw):
    if not raw: return ""
    raw=raw.strip()
    m=re.search(r'tiktok\.com/@([\w.]+)',raw)
    return m.group(1) if m else raw.lstrip("@").strip()

def _normalize_text(v):
    if v is None: return ""
    if isinstance(v,str): return v.strip()
    if isinstance(v,list) and v: return _normalize_text(v[0])
    if isinstance(v,dict):
        for k in ("text","name","value","link"):
            if v.get(k): return _normalize_text(v[k])
    return str(v).strip()

def _extract_aweme_id(url):
    if not url: return None
    m=re.search(r'/video/(\d{15,25})',url)
    return m.group(1) if m else None

def _extract_tiktok_url(text):
    if not text: return ""
    for p in [r'https?://vm\.tiktok\.com/\S+',r'https?://vt\.tiktok\.com/\S+',
              r'https?://www\.tiktok\.com/t/\S+',r'https?://www\.tiktok\.com/@[\w.]+/video/\d+\S*']:
        m=re.search(p,text)
        if m: return m.group(0).rstrip('/').rstrip('!')
    return text.strip()

# ── 投流码: Phase2 自动化辅助 ──
def _find_click_three_dots(c,did):
    ib=_load_icon(THREE_DOTS_ICON_FILE)
    if ib:
        r=c.find_image(did,ib,THREE_DOTS_ICON_SIM,THREE_DOTS_SEARCH_RECT)
        if r: c.tap(did,r[0],r[1]); return True
    c.tap(did,PX["three_dots"][0],PX["three_dots"][1]); return True

def _find_click_copy_link(c,did):
    ib=_load_icon(COPY_LINK_ICON_FILE)
    if ib:
        r=c.find_image(did,ib,ICON_SIM,COPY_LINK_SEARCH_RECT)
        if r: c.tap(did,r[0],r[1]); return True
    c.tap(did,COPY_LINK_FALLBACK[0],COPY_LINK_FALLBACK[1]); return True

def _dismiss_popup(c, did):
    """检测并关闭 Find contacts 等弹窗（3秒检测窗口）"""
    ib = _load_icon(DONT_ALLOW_ICON_FILE)
    if not ib:
        return False
    # 3秒内反复检测
    deadline = time.time() + 3.0
    while time.time() < deadline:
        r = c.find_image(did, ib, DONT_ALLOW_SIM, DONT_ALLOW_SEARCH_RECT)
        if r:
            c.tap(did, r[0], r[1])
            time.sleep(0.5)
            return True
        time.sleep(0.3)
    return False

def _get_share_link(c,did):
    _find_click_three_dots(c,did); time.sleep(2.0)
    # 点copy link前检测弹窗
    _dismiss_popup(c, did)
    _find_click_copy_link(c,did); time.sleep(1.0)
    # 点copy link后检测弹窗
    _dismiss_popup(c, did)
    time.sleep(1.5)
    for attempt in range(3):
        r=c.get_clipboard(did)
        if r: return _extract_tiktok_url(r)
        time.sleep(1.5)
    return None

def _match_video(share_url, videos, tikhub=None):
    if not share_url or not videos: return None
    aid=_extract_aweme_id(share_url)
    if aid:
        for v in videos:
            if v.get("aweme_id")==aid: return v
    if not aid and tikhub:
        aid=tikhub.resolve_share_url(share_url)
        if aid:
            for v in videos:
                if v.get("aweme_id")==aid: return v
    return None

def _do_ad_auth_flow(c,did,is_first=False,log_fn=None,stop_check=None,slow=False,tag=""):
    """slow=True: 测试模式，每步加更长等待便于观察
    tag: 日志前缀（如设备名），便于并发时区分
    """
    _tag = f"[{tag}]" if tag else ""
    def _log(msg):
        if log_fn: log_fn(msg)
    def _should_stop():
        return stop_check and stop_check()
    def click(name,sleep=T_CLICK):
        x,y=PX[name]; _log(f"    {_tag}点击 {name} ({x},{y})"); c.tap(did,x,y); time.sleep(sleep + (1.5 if slow else 0))
    # 测试模式下所有 sleep 都加长
    _sf = 2.0 if slow else 1.0
    if _should_stop(): _log(f"    {_tag}[推流码] 收到停止信号，退出"); return None
    _log(f"    {_tag}[推流码] 步骤1: 点三个点")
    _find_click_three_dots(c,did); time.sleep(1.0 * _sf)
    if _should_stop(): _log(f"    {_tag}[推流码] 收到停止信号，退出"); return None
    _log(f"    {_tag}[推流码] 步骤2: 检测弹窗")
    _dismiss_popup(c, did)
    time.sleep(1.0 * _sf)
    if _should_stop(): _log(f"    {_tag}[推流码] 收到停止信号，退出"); return None
    _log(f"    {_tag}[推流码] 步骤3: 滑动 ({SWIPE_START_X},{SWIPE_ROW_Y}) -> ({SWIPE_END_X},{SWIPE_ROW_Y})")
    r_swipe = c.swipe(did,SWIPE_START_X,SWIPE_ROW_Y,SWIPE_END_X,SWIPE_ROW_Y)
    _log(f"    {_tag}[推流码] 滑动结果: {r_swipe}")
    time.sleep(T_SWIPE * _sf)
    if _should_stop(): _log(f"    {_tag}[推流码] 收到停止信号，退出"); return None
    # Ad settings
    _log(f"    {_tag}[推流码] 步骤4: 找 Ad settings")
    ib=_load_icon(AD_ICON_FILE)
    if ib:
        r=c.find_image(did,ib,ICON_SIM,AD_SEARCH_RECT)
        if r:
            _log(f"    {_tag}[推流码] 识图找到 Ad settings ({r[0]},{r[1]})")
            c.tap(did,r[0],r[1])
        else:
            _log(f"    {_tag}[推流码] 识图未找到，用兜底坐标 {AD_FALLBACK_POSITIONS[0]}")
            c.tap(did,AD_FALLBACK_POSITIONS[0][0],AD_FALLBACK_POSITIONS[0][1])
    else:
        _log(f"    {_tag}[推流码] 图标文件 {AD_ICON_FILE} 不存在，用兜底坐标 {AD_FALLBACK_POSITIONS[0]}")
        c.tap(did,AD_FALLBACK_POSITIONS[0][0],AD_FALLBACK_POSITIONS[0][1])
    _wait_after_adsettings = (10.0 if is_first else 4.5) * (1.5 if slow else 1.0)
    _log(f"    {_tag}[推流码] 等待 Ad settings 加载 {_wait_after_adsettings}s")
    time.sleep(_wait_after_adsettings)
    if _should_stop(): _log(f"    {_tag}[推流码] 收到停止信号，退出"); return None
    # Check toggle
    _log(f"    {_tag}[推流码] 步骤5: 检测授权开关")
    already_on=False
    ib2=_load_icon(AD_AUTH_ON_ICON_FILE)
    if ib2:
        r=c.find_image(did,ib2,AD_AUTH_ON_ICON_SIM,AD_AUTH_ON_SEARCH_RECT)
        if r: already_on=True
    _log(f"    {_tag}[推流码] 授权开关已开: {already_on}")
    if already_on:
        click("manage",sleep=4.0)
    else:
        click("ad_auth_toggle",sleep=1.0); click("authorize"); click("save",sleep=2.0)
        time.sleep(5 * _sf); click("manage",sleep=4.0)
    if _should_stop(): _log(f"    {_tag}[推流码] 收到停止信号，退出"); return None
    _log(f"    {_tag}[推流码] 步骤6: 复制推流码")
    click("copy_code",sleep=2.0)
    _log(f"    {_tag}[推流码] 步骤7: 读取剪贴板")
    for attempt in range(3):
        if _should_stop(): _log(f"    {_tag}[推流码] 收到停止信号，退出"); return None
        r=c.get_clipboard(did)
        if r:
            r=r.strip()
            if r.startswith("#"):
                _log(f"    {_tag}[推流码] ✓ 剪贴板第{attempt+1}次读到: {r}")
                return r
            _log(f"    {_tag}[推流码] 剪贴板第{attempt+1}次非推流码: {r[:50]}")
        else:
            _log(f"    {_tag}[推流码] 剪贴板第{attempt+1}次为空")
        time.sleep(2.0 * _sf)
    return None

def _process_device_videos(c,feishu,did,remaining,video_nums=None,tikhub=None):
    results=[]; max_pos=max(VIDEO_GRID.keys())
    positions=video_nums if video_nums else list(range(2,max_pos+1))
    is_first=True
    for pos in positions:
        if not remaining: break
        if pos not in VIDEO_GRID: continue
        vx,vy=VIDEO_GRID[pos]; c.tap(did,vx,vy); time.sleep(T_PAGE_LOAD)
        share_url=_get_share_link(c,did)
        if not share_url:
            c.tap(did,PX["back"][0],PX["back"][1]); time.sleep(2.0)
            results.append({"pos":pos,"status":"no_share_url"}); continue
        matched=_match_video(share_url,remaining,tikhub=tikhub)
        if not matched:
            c.tap(did,PX["back"][0],PX["back"][1]); time.sleep(2.0)
            results.append({"pos":pos,"status":"no_match"}); continue
        # 如果匹配到的视频已有推流码，跳过
        if matched.get("ad_code"):
            c.tap(did,PX["back"][0],PX["back"][1]); time.sleep(2.0)
            results.append({"pos":pos,"status":"ok","ad_code":matched["ad_code"]})
            if matched in remaining: remaining.remove(matched)
            continue
        ad_code=_do_ad_auth_flow(c,did,is_first=is_first,log_fn=log_fn)
        is_first=False
        if ad_code and matched.get("record_id") and VIDEO_TABLE_ID:
            try: feishu.batch_update_records(VIDEO_TABLE_ID,[{"record_id":matched["record_id"],"fields":{VIDEO_FIELDS["ad_code"]:ad_code}}])
            except: pass
        c.tap(did,PX["back"][0],PX["back"][1]); time.sleep(2.5)
        c.tap(did,PX["back"][0],PX["back"][1]); time.sleep(1.5)
        results.append({"pos":pos,"status":"ok" if ad_code else "code_failed","ad_code":ad_code})
        if matched in remaining: remaining.remove(matched)
        time.sleep(1.0)
    return results

# ── 投流码: 完整流程入口 ──
def run_adcode_full(phase="all", port=9911, workers=20, days=1, videos_str="", match_mode="name", log_fn=print):
    if not HAS_REQUESTS: log_fn("[ERROR] 缺少requests"); return
    video_nums=[]
    if videos_str.strip():
        try: video_nums=[int(v.strip()) for v in videos_str.split(",")]
        except: return
    log_fn(f"投流码自动化启动 (模式: {'按名字' if match_mode=='name' else '按分组'})")

    # Phase 1
    video_data={}
    if phase in ("all","1"):
        log_fn("Phase 1: 拉取飞书数据...")
        feishu=_FeishuClient(FEISHU_APP_ID,FEISHU_APP_SECRET,FEISHU_APP_TOKEN)
        tikhub=_TikHubClient()
        # 获取账号
        recs=feishu.search_records(ACCOUNT_TABLE_ID, view_id=ACCOUNT_VIEW_ID,
            filter_obj={"conjunction":"and","conditions":[{"field_name":ACCOUNT_FIELDS["status"],"operator":"is","value":["更新中"]}]})
        accounts=[]
        for rec in recs:
            f=rec.get("fields") or {}
            uid=_normalize_account_id(_normalize_text(f.get(ACCOUNT_FIELDS["account_id"])))
            if uid: accounts.append({"unique_id":uid,"name":_normalize_text(f.get(ACCOUNT_FIELDS["account_name"])),"record_id":rec.get("record_id","")})
        log_fn(f"  找到 {len(accounts)} 个账号")
        if not accounts: return
        # 拉取视频 (5并发, 每个3次重试)
        today_utc=datetime.now(tz=timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
        pub_after=int(today_utc.timestamp()) if days<=1 else int((datetime.now(tz=timezone.utc)-timedelta(days=days)).timestamp())

        def _fetch_one_account(acc):
            uid=acc["unique_id"]
            MAX_RETRIES=2
            for attempt in range(1, MAX_RETRIES+1):
                try:
                    th=_TikHubClient()
                    # 直接用 unique_id 调 app/v3 (V3→V2→V1)；失败时查 sec_uid 再用 web
                    vids=th.fetch_user_videos(None, 30, pub_after, unique_id=uid)
                    if not vids:
                        # fallback: 查 sec_uid 再用 web
                        ui=th.fetch_user_info(uid)
                        if ui:
                            vids=th.fetch_user_videos(ui["sec_uid"], 30, pub_after)
                    non_pinned=[v for v in vids if not v.get("is_pinned")]
                    log_fn(f"  {uid}: {len(non_pinned)} 个视频")
                    return uid, non_pinned
                except Exception as e:
                    log_fn(f"  {uid}: 第{attempt}次异常: {e}")
                    if attempt<MAX_RETRIES: time.sleep(1)
            return uid, []

        log_fn(f"  并发拉取 {len(accounts)} 个账号视频 (10并发, 2次重试)...")
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures={pool.submit(_fetch_one_account, acc): acc for acc in accounts}
            for fut in as_completed(futures):
                uid, vids = fut.result()
                if vids: video_data[uid]=vids
        # ── 写入飞书 ──
        log_fn("写入飞书视频管理表...")
        existing=feishu.search_records(VIDEO_TABLE_ID,view_id=VIDEO_VIEW_ID)
        existing_vids=set()
        vid_to_rec={}
        for rec in existing:
            f=rec.get("fields") or {}
            vid=_normalize_text(f.get(VIDEO_FIELDS["vid"]))
            # 从视频链接中也提取 aweme_id 做双重去重
            link_val=f.get(VIDEO_FIELDS["video_link"])
            link_url=""
            if isinstance(link_val,dict): link_url=link_val.get("link","") or link_val.get("text","")
            elif isinstance(link_val,str): link_url=link_val
            link_id=""
            if link_url:
                m=re.search(r'/(?:photo|video)/(\d+)',link_url)
                if m: link_id=m.group(1)
            ad_code=_normalize_text(f.get(VIDEO_FIELDS["ad_code"]))
            rid=rec.get("record_id","")
            has_account_link=bool(f.get(VIDEO_FIELDS["account_link"]))
            has_publish_date=f.get(VIDEO_FIELDS["publish_date"]) is not None
            has_play_count=f.get(VIDEO_FIELDS["play_count"]) is not None
            has_like_count=bool(_normalize_text(f.get(VIDEO_FIELDS["like_count"])))
            has_video_link=bool(link_url)
            has_upload_time=f.get(VIDEO_FIELDS["upload_time"]) is not None
            has_account_id=bool(_normalize_text(f.get(VIDEO_FIELDS["account_id"])))
            has_pub_text=bool(_normalize_text(f.get(VIDEO_FIELDS.get("publish_date_text",""))))
            rec_info={"record_id":rid,"ad_code":ad_code or None,
                "has_account_link":has_account_link,"has_publish_date":has_publish_date,
                "has_play_count":has_play_count,"has_like_count":has_like_count,
                "has_video_link":has_video_link,"has_upload_time":has_upload_time,
                "has_account_id":has_account_id,"has_pub_text":has_pub_text}
            for aweme_id in (vid, link_id):
                if aweme_id:
                    existing_vids.add(aweme_id)
                    vid_to_rec[aweme_id]=rec_info
        log_fn(f"  表中已有 {len(existing_vids)} 个视频")

        # 从旧账号表查询 account_id → record_id 映射（视频表"账号编号"字段关联到旧表）
        log_fn("  从旧账号表获取 record_id 映射...")
        try:
            old_recs = feishu.search_records(OLD_ACCOUNT_TABLE_ID)
            uid_to_rid = {}
            for r in old_recs:
                rf = r.get("fields") or {}
                u = _normalize_account_id(_normalize_text(rf.get(OLD_ACCOUNT_FIELD_ACCOUNT_ID)))
                if u and r.get("record_id"): uid_to_rid[u] = r["record_id"]
            log_fn(f"  旧账号表映射 {len(uid_to_rid)} 条")
        except Exception as e:
            log_fn(f"  查询旧账号表失败: {e}")
            uid_to_rid = {a["unique_id"]:a["record_id"] for a in accounts if a.get("record_id")}
        new_recs=[]; rec_to_acc=[]; updates_to_apply=[]
        for uid,vids in video_data.items():
            arid=uid_to_rid.get(uid)
            for v in vids:
                aid=v["aweme_id"]
                if aid in existing_vids:
                    ei=vid_to_rec.get(aid,{})
                    v["record_id"]=ei.get("record_id"); v["ad_code"]=ei.get("ad_code")
                    # 补全已有记录缺失字段
                    rid=ei.get("record_id")
                    if rid:
                        uf={}
                        if not ei.get("has_account_link") and arid: uf[VIDEO_FIELDS["account_link"]]=[arid]
                        if not ei.get("has_publish_date") and v.get("create_time"): uf[VIDEO_FIELDS["publish_date"]]=int(v["create_time"])*1000
                        if not ei.get("has_play_count") and v.get("play_count") is not None: uf[VIDEO_FIELDS["play_count"]]=v["play_count"]
                        if not ei.get("has_like_count") and v.get("digg_count") is not None: uf[VIDEO_FIELDS["like_count"]]=str(v["digg_count"])
                        if not ei.get("has_video_link"):
                            raw=v.get("share_url","")
                            cu=raw.split("?")[0] if raw.startswith("http") else f"https://www.tiktok.com/@{uid}/video/{aid}"
                            uf[VIDEO_FIELDS["video_link"]]={"link":cu,"text":cu}
                        if not ei.get("has_upload_time"): uf[VIDEO_FIELDS["upload_time"]]=int(time.time()*1000)
                        if not ei.get("has_account_id") and uid: uf[VIDEO_FIELDS["account_id"]]=uid
                        if "publish_date_text" in VIDEO_FIELDS and not ei.get("has_pub_text") and v.get("create_time"):
                            uf[VIDEO_FIELDS["publish_date_text"]]=datetime.fromtimestamp(int(v["create_time"]),tz=timezone.utc).strftime("%Y%m%d")
                        if uf: updates_to_apply.append({"record_id":rid,"fields":uf})
                    continue
                clean_url=f"https://www.tiktok.com/@{uid}/video/{aid}"
                rec={VIDEO_FIELDS["video_link"]:{"link":clean_url,"text":clean_url},
                     VIDEO_FIELDS["play_count"]:v["play_count"],VIDEO_FIELDS["like_count"]:str(v["digg_count"]),
                     VIDEO_FIELDS["upload_time"]:int(time.time()*1000),VIDEO_FIELDS["account_id"]:uid}
                if v.get("create_time"):
                    rec[VIDEO_FIELDS["publish_date"]]=int(v["create_time"])*1000
                    if "publish_date_text" in VIDEO_FIELDS:
                        rec[VIDEO_FIELDS["publish_date_text"]]=datetime.fromtimestamp(int(v["create_time"]),tz=timezone.utc).strftime("%Y%m%d")
                if arid: rec[VIDEO_FIELDS["account_link"]]=[arid]
                rec={k:vv for k,vv in rec.items() if vv is not None and vv!=""}
                new_recs.append(rec); rec_to_acc.append((uid,v))

        # 补全已有记录缺失字段
        if updates_to_apply:
            log_fn(f"  补全数据: {len(updates_to_apply)} 条已有记录...")
            try: feishu.batch_update_records(VIDEO_TABLE_ID,updates_to_apply)
            except Exception as e: log_fn(f"  补全失败: {e}")

        if new_recs:
            log_fn(f"  待写入: {len(new_recs)} 条新记录")
            try:
                ids=feishu.batch_create_records(VIDEO_TABLE_ID,new_recs)
            except RuntimeError:
                log_fn("  批量写入失败，改为逐条...")
                ids=[]
                for idx,r in enumerate(new_recs):
                    try: ids.extend(feishu.batch_create_records(VIDEO_TABLE_ID,[r]))
                    except: ids.append(None); log_fn(f"  第{idx+1}条失败")
            for i,rid in enumerate(ids):
                if rid and i<len(rec_to_acc):
                    uid,v=rec_to_acc[i]; v["record_id"]=rid; v["ad_code"]=None
        else:
            log_fn("  无新记录需要写入")

        # 重建 video_data 包含 record_id
        for uid,vids in list(video_data.items()):
            video_data[uid]=[v for v in vids if v.get("record_id")]
        total=sum(len(v) for v in video_data.values())
        need=sum(1 for vl in video_data.values() for v in vl if not v.get("ad_code"))
        already=total-need
        log_fn(f"Phase 1 完成: {len(video_data)} 账号, {total} 视频")
        if new_recs: log_fn(f"  新写入飞书: {len(new_recs)} 条")
        dup_count=sum(1 for uid,vids in video_data.items() for v in vids if v.get("aweme_id") in existing_vids)
        if dup_count: log_fn(f"  已存在跳过(含补全): {dup_count} 条")
        if already: log_fn(f"  已有推流码: {already} 条 (Phase2跳过)")
        log_fn(f"  待获取推流码: {need} 条")
        if phase=="1": return

    # Phase 2
    if phase in ("all","2"):
        if not video_data:
            log_fn("从飞书补充数据...")
            feishu=_FeishuClient(FEISHU_APP_ID,FEISHU_APP_SECRET,FEISHU_APP_TOKEN)
            recs=feishu.search_records(VIDEO_TABLE_ID,
                filter_obj={"conjunction":"and","conditions":[{"field_name":VIDEO_FIELDS["publish_date"],"operator":"is","value":["Today"]}]},
                view_id=VIDEO_VIEW_ID)
            for rec in recs:
                f=rec.get("fields") or {}
                uid=_normalize_text(f.get(VIDEO_FIELDS["account_id"]))
                aid=_normalize_text(f.get(VIDEO_FIELDS["vid"]))
                ad_code=_normalize_text(f.get(VIDEO_FIELDS["ad_code"]))
                if uid and aid:
                    video_data.setdefault(uid,[]).append({"aweme_id":aid,"record_id":rec.get("record_id"),"ad_code":ad_code or None,"share_url":""})
        log_fn(f"Phase 2: iMouse自动化 (模式: {match_mode})")
        ic=_IMouseXPClient("127.0.0.1",port)
        devices=ic.get_devices()
        online=[d for d in devices if d.get("state",0)!=0]
        if not online: log_fn("没有在线设备"); return
        log_fn(f"在线设备: {len(online)}")
        # 匹配设备: name=自定义名, username=设备名
        matched=[]
        for dev in online:
            if match_mode=="username":
                dn=(dev.get("username") or dev.get("name") or "").strip()
            else:
                dn=(dev.get("name") or dev.get("username") or "").strip()
            uid=_normalize_account_id(dn)
            if uid in video_data:
                all_vids=video_data[uid]
                need=[v for v in all_vids if not v.get("ad_code")]
                skipped=len(all_vids)-len(need)
                if need:
                    matched.append((dev,uid,need))
                    skip_msg=f", 跳过{skipped}个已有推流码" if skipped else ""
                    log_fn(f"  匹配: {dn} -> {uid} ({len(need)}个待处理{skip_msg})")
                elif skipped:
                    log_fn(f"  跳过: {dn} -> {uid} (全部{skipped}个已有推流码)")
        if not matched: log_fn("没有需要处理的设备"); return
        # 执行
        w=min(workers,len(matched))
        log_fn(f"处理 {len(matched)} 台设备 (workers={w})")
        fcfg={"app_id":FEISHU_APP_ID,"app_secret":FEISHU_APP_SECRET,"app_token":FEISHU_APP_TOKEN}
        def _run_one(idx,item):
            dev,uid,vnc=item; did=dev.get("deviceid",dev.get("mac",""))
            name=dev.get("name") or "?"
            c2=_IMouseXPClient("127.0.0.1",port)
            fc=_FeishuClient(fcfg["app_id"],fcfg["app_secret"],fcfg["app_token"])
            tc=_TikHubClient()
            remaining=list(vnc)
            log_fn(f"设备 [{idx+1}/{len(matched)}]: {name} (账号:{uid}, 待处理:{len(remaining)})")
            c2.press_home(did); time.sleep(1.5)
            c2.open_url(did,TIKTOK_SCHEME); time.sleep(T_APP_LAUNCH+3)
            c2.tap(did,PX["profile_tab"][0],PX["profile_tab"][1]); time.sleep(T_PAGE_LOAD+1.5)
            dr=_process_device_videos(c2,fc,did,remaining,video_nums,tc)
            ok=sum(1 for r in dr if r.get("status")=="ok")
            # remaining 里剩下的就是未成功匹配/获取的视频
            failed_links=[]
            for v in remaining:
                aid=v.get("aweme_id","")
                link=f"https://www.tiktok.com/@{uid}/video/{aid}" if aid else ""
                if link: failed_links.append(link)
            # 加上匹配到但推流码获取失败的
            code_failed=sum(1 for r in dr if r.get("status")=="code_failed")
            log_fn(f"设备 {name} 完成: {ok}/{len(vnc)} (匹配失败:{len(remaining)}, 推流码失败:{code_failed})")
            return {"name":name,"uid":uid,"ok":ok,"total":len(vnc),"failed_links":failed_links}
        results=[]
        if w==1:
            for i,item in enumerate(matched):
                try: results.append(_run_one(i,item))
                except Exception as e: log_fn(f"设备异常: {e}")
        else:
            with ThreadPoolExecutor(max_workers=w) as ex:
                futs={ex.submit(_run_one,i,item):(i,item) for i,item in enumerate(matched)}
                for f in as_completed(futs):
                    try: results.append(f.result())
                    except Exception as e: log_fn(f"设备异常: {e}")
        tok=sum(r["ok"] for r in results); ttl=sum(r["total"] for r in results)
        log_fn(f"全部完成: {tok}/{ttl}")
        # 返回结果供弹窗使用
        return {"results": results, "video_data": video_data, "match_mode": match_mode}


def base64_to_bmp(data: dict):
    if 'data' not in data or 'img' not in data['data']:
        return None
    image_base64 = data['data']['img']
    is_gzip = data['data']['gzip']
    imgdata = base64.b64decode(image_base64)
    if is_gzip:
        with gzip.GzipFile(fileobj=io.BytesIO(imgdata)) as f:
            imgdata = f.read()
    return imgdata


class MyApp(QtWidgets.QMainWindow):
    _signal_binaryEvent = pyqtSignal(bytes)
    _signal_msgEvent = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.api = imouse_api.WsApi('127.0.0.1', on_message=self._on_message,
                                     on_binary=self._on_binary, QApplication=QApplication)
        self._signal_binaryEvent.connect(self._binaryEvent)
        self._signal_msgEvent.connect(self._msgEvent)
        self._img = QImage()
        self.api.start()
        self.device_list = {}
        self.get_devicemodel_list = {}
        self.usb_list = {}

        self.scheduled_tasks = []
        self.active_tasks = {}
        self.task_timer = QTimer(self)
        self.task_timer.timeout.connect(self.check_scheduled_tasks)

        self.excel_data = []
        self.excel_file_path = 'tiktok_data.xlsx'

        self.__ui = Ui_MainWindow()
        self.__ui.setupUi(self)
        self.devlist_tv = self.__ui.tableView_devlist
        self.devlist_tv.verticalHeader().hide()
        self.devlist_tv.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.devlist_tv.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.devlist_tv.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.devlist_model = QStandardItemModel(0, 8)
        self.devlist_model.setHorizontalHeaderLabels(
            ['名称', '设备名', 'deviceid地址', '投屏名称', '绑定硬件', '设备型号', '系统版本', '状态'])
        self.devlist_tv.setModel(self.devlist_model)

        # 按钮绑定
        self.__ui.button_get_device_list.clicked.connect(lambda: self._button_click('get_device_list'))
        self.__ui.button_get_devicemodel_list.clicked.connect(lambda: self._button_click('get_devicemodel_list'))
        self.__ui.button_get_usb_list.clicked.connect(lambda: self._button_click('get_usb_list'))
        self.__ui.button_get_device_screenshot.clicked.connect(lambda: self._button_click('get_device_screenshot'))
        self.__ui.button_loop_device_screenshot.clicked.connect(lambda: self._button_click('loop_device_screenshot'))
        self.__ui.button_stop_screenshot.clicked.connect(lambda: self._button_click('loop_stop_screenshot'))
        self.__ui.button_set_dev_usb_id.clicked.connect(lambda: self._button_click('set_dev_usb_id'))
        self.__ui.button_del_dev.clicked.connect(lambda: self._button_click('del_dev'))
        self.__ui.button_set_dev_name.clicked.connect(lambda: self._button_click('set_dev_name'))
        self.__ui.button_send_key.clicked.connect(lambda: self._button_click('send_key'))
        self.__ui.button_mouse_events.clicked.connect(lambda: self._button_click('mouse_events'))

        self.__ui.button_open_tiktok.clicked.connect(lambda: self._button_click('open_tiktok_batch'))

        self.__ui.button_select_upload_folder.clicked.connect(self._select_upload_folder)
        self.__ui.button_select_upload_video_folder.clicked.connect(self._select_upload_video_folder)
        self.__ui.button_batch_upload.clicked.connect(lambda: self._button_click('batch_upload'))
        self.__ui.button_batch_upload_video.clicked.connect(lambda: self._button_click('batch_upload_video'))
        self.__ui.button_delete_album.clicked.connect(lambda: self._button_click('delete_album'))
        self.__ui.button_switch_account_all.clicked.connect(lambda: self._button_click('switch_account_all'))
        self.__ui.button_switch_account_selected.clicked.connect(lambda: self._button_click('switch_account_selected'))
        self.__ui.button_fetch_video_data.clicked.connect(lambda: self._button_click('fetch_video_data'))
        self.__ui.button_adcode_by_name.clicked.connect(lambda: self._button_click('adcode_by_name'))
        self.__ui.button_adcode_by_group.clicked.connect(lambda: self._button_click('adcode_by_group'))
        self.__ui.button_gen_fail_report.clicked.connect(self._gen_fail_report)
        self.__ui.button_check_update.clicked.connect(self._check_update)
        self.__ui.label_version.setText(f"v{LOCAL_VERSION}")
        self.__ui.button_fetch_video_selected.clicked.connect(lambda: self._button_click('fetch_video_selected'))
        self.__ui.button_adcode_selected_name.clicked.connect(lambda: self._button_click('adcode_selected_name'))
        self.__ui.button_adcode_selected_devname.clicked.connect(lambda: self._button_click('adcode_selected_devname'))

        # Tab 4: 完播率分析
        self.__ui.button_select_analytics_excel.clicked.connect(self._select_analytics_excel)
        self.__ui.button_fetch_stats.clicked.connect(lambda: self._button_click('fetch_stats'))
        self.__ui.button_fetch_completion_rate.clicked.connect(lambda: self._button_click('fetch_completion_rate'))

        # Tab 5: 飞书完播率
        self.__ui.spinBox_year.valueChanged.connect(self._update_calendar)
        self.__ui.spinBox_month.valueChanged.connect(self._update_calendar)
        self.__ui.button_select_all_days.clicked.connect(self._select_all_days)
        self.__ui.button_clear_days.clicked.connect(self._clear_all_days)
        self.__ui.button_feishu_rate_by_name.clicked.connect(lambda: self._button_click('feishu_rate_by_name'))
        self.__ui.button_feishu_rate_by_group.clicked.connect(lambda: self._button_click('feishu_rate_by_group'))
        # 测试Tab按钮（防御性绑定，避免 tiktok_form.py 未更新导致启动崩溃）
        if hasattr(self.__ui, 'button_test_completion_rate'):
            self.__ui.button_test_completion_rate.clicked.connect(lambda: self._button_click('test_completion_rate'))
        if hasattr(self.__ui, 'button_test_adcode'):
            self.__ui.button_test_adcode.clicked.connect(lambda: self._button_click('test_adcode'))
        if hasattr(self.__ui, 'button_test_stop'):
            self.__ui.button_test_stop.clicked.connect(self._test_stop)
        # 停止事件（测试功能共享）
        if not hasattr(self, '_test_stop_event'):
            self._test_stop_event = threading.Event()
        for btn in self.__ui.day_buttons:
            btn.clicked.connect(self._update_selected_dates_label)
        self._update_calendar()

        self.__ui.comboBox_4.addItems(['左键', '右键'])
        self.__ui.comboBox_5.addItems(['左滑', '右滑', '上滑', '下滑'])

        self._load_excel_data()

    def _load_excel_data(self):
        try:
            self.df = pd.read_excel(self.excel_file_path)
            required = ['devices', 'file', 'type', 'url', 'title', 'description']
            missing = [c for c in required if c not in self.df.columns]
            if missing:
                raise ValueError(f"Excel 缺少必要列: {missing}")
            if 'scheduled_time' not in self.df.columns:
                self.df['scheduled_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'status' not in self.df.columns:
                self.df['status'] = 'Pending'
            self.df['scheduled_time'] = pd.to_datetime(self.df['scheduled_time'])
            self.excel_data = self.df.to_dict('records')
            self.load_scheduled_tasks()
            self._debug(f"成功加载 Excel，共 {len(self.excel_data)} 条数据， {len(self.scheduled_tasks)} 条定时任务")
        except Exception as e:
            self._debug(f"加载 Excel 失败: {e}")
            self._create_sample_excel()

    def _create_sample_excel(self):
        try:
            now = datetime.now()
            data = {
                'devices': ['pictureA', 'videoB', 'pictureC'],
                'file': ['pictureA', 'videoB', 'pictureC'],
                'type': ['picture', 'video', 'picture'],
                'url': [
                    'https://www.tiktok.com/music/original-sound-7335534285989481248',
                    '',
                    'https://www.tiktok.com/music/original-sound-7335534285989481248'
                ],
                'title': ['sample title 1', '', 'sample title 3'],
                'description': ['#sample description 1', '#sample description 2', '#sample description 3'],
                'status': ['Pending', 'Pending', 'Pending'],
                'scheduled_time': [
                    now.strftime('%Y-%m-%d %H:%M:%S'),
                    (now + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    (now + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                ],
            }
            self.df = pd.DataFrame(data)
            self.df.to_excel(self.excel_file_path, index=False)
            self.excel_data = self.df.to_dict('records')
            self.load_scheduled_tasks()
            self._debug(f"已创建示例 Excel: {self.excel_file_path}")
        except Exception as e:
            self._debug(f"创建示例Excel文件时出现错误: {e}")

    def load_scheduled_tasks(self):
        self.scheduled_tasks = []
        if not hasattr(self, 'df') or self.df.empty:
            return
        for idx, row in self.df.iterrows():
            status = str(row.get('status', '')).strip().lower()
            if status == 'pending':
                task = {
                    'index': idx,
                    'device_name': str(row.get('devices', '')).strip(),
                    'scheduled_time': row.get('scheduled_time'),
                    'data': row.to_dict(),
                }
                self.scheduled_tasks.append(task)
        self._debug(f"已加载 {len(self.scheduled_tasks)} 条待处理任务")

    def check_scheduled_tasks(self):
        current_time = datetime.now()
        tasks_to_run = [t for t in self.scheduled_tasks if t['scheduled_time'] <= current_time]
        if not tasks_to_run:
            return
        for task in tasks_to_run:
            self._debug(f"{task['device_name']} 准备执行任务")
            deviceid = self.find_device_by_name(task['device_name'])
            if not deviceid:
                self._debug(f"{task['device_name']} 未连接，跳过任务")
                self.update_task_status(task, 'Failed', '设备未连接')
                if task in self.scheduled_tasks:
                    self.scheduled_tasks.remove(task)
                continue
            if deviceid in self.active_tasks:
                self._debug(f"{task['device_name']} 正在执行其他任务，等待下次")
                continue
            self.active_tasks[deviceid] = task
            if task in self.scheduled_tasks:
                self.scheduled_tasks.remove(task)
            self.execute_task(deviceid, task)

    def find_device_by_name(self, device_name):
        for deviceid, info in self.device_list.items():
            if str(info.get('name', '')).strip() == device_name:
                return deviceid
        return None

    def execute_task(self, deviceid, task):
        try:
            self._debug(f"开始执行任务: 设备 {task.get('device_name')}, 类型 {task['data'].get('type')}")
            row_data = task['data']
            media_type = str(row_data.get('type', 'picture')).strip().lower()
            base_dir = r'D:\iMousePro\Shortcut\Media'
            device_dir = os.path.join(base_dir, task['device_name'])

            if media_type == 'picture':
                file_name = str(row_data.get('file', '')).strip()
                img_path = None
                for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                    candidate = os.path.join(device_dir, file_name + ext)
                    if os.path.exists(candidate):
                        img_path = candidate
                        break
                if not img_path:
                    raise FileNotFoundError(f"找不到模板文件: {file_name}")

                img = Image.open(img_path)
                w, h = img.size
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                img = img.crop((left, top, left + side, top + side))
                img = img.resize((135, 135), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                template_img_bytes = buf.getvalue()
                self._open_tiktok_app_with_data(deviceid, row_data, template_img_bytes)

            elif media_type == 'video':
                file_name = str(row_data.get('file', '')).strip()
                video_path = os.path.join(device_dir, file_name + '.mov')
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"找不到视频文件: {video_path}")
                img_bytes = self._extract_video_thumbnail(video_path)
                if not img_bytes:
                    raise RuntimeError("无法获取视频缩略")
                self._open_tiktok_app_with_video(deviceid, row_data, img_bytes)

            else:
                raise ValueError(f"未知的媒体类型: {media_type}")

            self.update_task_status(task, 'Success')
        except Exception as e:
            self._debug(f"任务执行失败: {e}")
            self.update_task_status(task, 'Failed', str(e))
        finally:
            if deviceid in self.active_tasks:
                del self.active_tasks[deviceid]

    def update_task_status(self, task, status, message=None):
        try:
            idx = task['index']
            self.df.at[idx, 'status'] = status
            if message:
                self.df.at[idx, 'message'] = message
            self.df.to_excel(self.excel_file_path, index=False)
            self._debug(f"任务状态更新: {status}")
        except Exception as e:
            self._debug(f"更新任务状态失败: {e}")

    def _button_click(self, fun):
        # 不需要选设备的命令
        if fun in ('get_device_list', 'get_devicemodel_list', 'get_usb_list'):
            if fun == 'get_device_list':
                self.api.get_device_list(sync=False)
                return
            elif fun == 'get_devicemodel_list':
                self.api.get_devicemodel_list(sync=False)
                return
            elif fun == 'get_usb_list':
                self.api.get_usb_list(sync=False)
                return

        # 不需要选中设备的批量操作
        if fun == 'delete_album':
            self._delete_all_albums()
            return
        elif fun == 'batch_upload':
            self._batch_upload_photos()
            return
        elif fun == 'batch_upload_video':
            self._batch_upload_videos()
            return
        elif fun == 'switch_account_all':
            self._switch_account(selected_only=False)
            return
        elif fun == 'switch_account_selected':
            self._switch_account(selected_only=True)
            return
        elif fun == 'fetch_stats':
            self._fetch_video_stats_from_excel()
            return
        elif fun == 'fetch_completion_rate':
            self._fetch_completion_rate()
            return
        elif fun == 'feishu_rate_by_name':
            self._feishu_completion_rate(match_mode='name')
            return
        elif fun == 'feishu_rate_by_group':
            self._feishu_completion_rate(match_mode='username')
            return
        elif fun == 'test_completion_rate':
            self._test_completion_rate()
            return
        elif fun == 'test_adcode':
            self._test_adcode()
            return
        elif fun == 'fetch_video_data':
            self._fetch_video_data()
            return
        elif fun == 'fetch_video_selected':
            self._fetch_video_data_selected()
            return
        elif fun == 'adcode_selected_name':
            self._adcode_selected(match_mode='name')
            return
        elif fun == 'adcode_selected_devname':
            self._adcode_selected(match_mode='username')
            return
        elif fun == 'adcode_by_name':
            self._run_adcode('name')
            return
        elif fun == 'adcode_by_group':
            self._run_adcode('username')
            return

        deviceid = self._get_selected_deviceid()
        if deviceid == '':
            return

        if fun == 'get_device_screenshot':
            gzip_val = self.__ui.checkBox_gzip.checkState().value
            sync = self.__ui.checkBox_sync.checkState().value
            binary = self.__ui.checkBox_binary.checkState().value
            ret = self.api.get_device_screenshot(deviceid, gzip_val, sync, binary)
            if 'data' not in ret:
                self._debug('异步调用' + ret['fun'])
                return
            self._debug('同步调用' + ret['fun'])
            img_data = base64_to_bmp(ret)
            if img_data is None:
                return
            self._show_img(img_data)
            return

        elif fun == 'loop_device_screenshot':
            delayed = self.__ui.spinBox_delayed.value()
            self.api.loop_device_screenshot(deviceid=deviceid, time=delayed, stop=False, sync=False)
            return

        elif fun == 'loop_stop_screenshot':
            self.api.loop_device_screenshot(deviceid=deviceid, time=100, stop=True, sync=False)
            return

        elif fun == 'set_dev_usb_id':
            comboBox3_index = self.__ui.comboBox_3.currentIndex()
            vid = ''
            pid = ''
            if comboBox3_index < len(self.usb_list):
                vid = list(self.usb_list.values())[comboBox3_index].get('vid', '')
                pid = list(self.usb_list.values())[comboBox3_index].get('pid', '')
            self.api.change_dev_usb_id(deviceid=deviceid, vid=vid, pid=pid, sync=False)
            return

        elif fun == 'del_dev':
            self.api.del_dev(deviceid=deviceid, sync=False)
            return

        elif fun == 'set_dev_name':
            self.api.change_dev_name(deviceid=deviceid, name=self.__ui.lineEdit.text(), sync=False)
            return

        elif fun == 'send_key':
            self.api.send_key(deviceid=deviceid, key=self.__ui.lineEdit_2.text(), sync=False)
            return

        elif fun == 'mouse_events':
            button = 'left' if self.__ui.comboBox_4.currentIndex() == 0 else 'right'
            try:
                x = int(self.__ui.lineEdit_3.text())
                y = int(self.__ui.lineEdit_4.text())
            except:
                x = 0
                y = 0

            idx5 = self.__ui.comboBox_5.currentIndex()
            if idx5 == 0:
                direction = 'left'
            elif idx5 == 1:
                direction = 'right'
            elif idx5 == 2:
                direction = 'up'
            elif idx5 == 3:
                direction = 'down'
            else:
                direction = 'left'

            if self.__ui.radioButton_1.isChecked():
                self.api.click(deviceid=deviceid, x=x, y=y, button=button, sync=False)
                return
            elif self.__ui.radioButton_2.isChecked():
                self.api.swipe(deviceid=deviceid, direction=direction, button=button, sync=False)
                return
            elif self.__ui.radioButton_3.isChecked():
                self.api.mouse_down(deviceid=deviceid, button=button, sync=False)
                return
            elif self.__ui.radioButton_4.isChecked():
                self.api.mouse_up(deviceid=deviceid, button=button, sync=False)
                return
            elif self.__ui.radioButton_5.isChecked():
                self.api.mouse_move(deviceid=deviceid, x=x, y=y, sync=False)
                return
            elif self.__ui.radioButton_6.isChecked():
                self.api.mouse_reset_pos(deviceid=deviceid, sync=False)
                return

        elif fun == 'open_tiktok_batch':
            current_device_info = self.device_list.get(deviceid)
            if not current_device_info:
                self._debug(f"未在 device_list 中找到设备 {deviceid} 信息，无法执行")
                return
            current_device_name = str(current_device_info.get('name', '')).strip()
            if not current_device_name:
                self._debug(f"设备 {deviceid} 未设置名称，无法执行")
                return

            self._load_excel_data()
            self._debug(f"已加载设备 {current_device_name} 的定时任务")

            if not self.task_timer.isActive():
                self.task_timer.start(1000)
                self._debug("定时任务系统已启动")

            self.execute_device_tasks(current_device_name)
            return

        elif fun == 'transfer_files':
            self._transfer_media_files(deviceid)
            return

    def execute_device_tasks(self, device_name):
        device_tasks = [t for t in self.scheduled_tasks if t['device_name'] == device_name]
        if not device_tasks:
            self._debug(f"设备 {device_name} 没有待处理的定时任务")
            return

        device_tasks.sort(key=lambda x: x['scheduled_time'])
        current_time = datetime.now()

        for task in list(device_tasks):
            if task['scheduled_time'] > current_time:
                self._debug(f"定时任务: 执行时间 {task['scheduled_time']}，还未到预定时间")
                continue

            deviceid = self.find_device_by_name(device_name)
            if not deviceid:
                self._debug(f"{device_name} 未连接，跳过任务")
                self.update_task_status(task, 'Failed', '设备未连接')
                if task in self.scheduled_tasks:
                    self.scheduled_tasks.remove(task)
                continue

            # 等待设备空闲
            while deviceid in self.active_tasks:
                self._debug(f"{device_name} 正在执行其他任务，等待中...")
                QApplication.processEvents()
                time.sleep(1)

            self.active_tasks[deviceid] = task
            if task in self.scheduled_tasks:
                self.scheduled_tasks.remove(task)

            self.execute_task(deviceid, task)
            time.sleep(5)

    def _extract_video_thumbnail(self, video_path):
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self._debug(f"无法打开视频文件: {video_path}")
                return None
            ret, frame = cap.read()
            cap.release()
            if not ret:
                self._debug(f"无法读取视频第一帧: {video_path}")
                return None
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            img = img.resize((135, 135), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            self._debug(f"成功提取视频缩略并裁切到尺寸=135×135，大小=({len(buf.getvalue())})")
            return buf.getvalue()
        except Exception as e:
            self._debug(f"提取视频缩略失败: {e}")
            return None

    def _update_status(self, idx, status):
        try:
            self.df.at[idx, 'status'] = status
            self.df.to_excel(self.excel_file_path, index=False)
            self._debug(f" 将状态写入 Excel: {status}")
        except Exception as e:
            self._debug(f"写入 Excel 失败: {e}")

    def _open_tiktok_app_with_data(self, deviceid, row_data, template_img_bytes):
        """使用指定数据执行TikTok发布 (图片模式)"""
        url = row_data.get('url', '')
        title = row_data.get('title', 'testtesttest')
        description = row_data.get('description', '')
        if not url:
            self._debug("URL为空，跳过此条任务")
            return False

        self._debug("正在尝试打 TikTok 应用...")
        self.api.send_key(deviceid=deviceid, fn_key='HOME', sync=True)
        time.sleep(2)
        self._debug("已发送HOME键，返回主屏幕")

        if not self._find_and_click_image(deviceid, 'icon/tiktok.bmp'):
            self._debug("打TikTok应用失败，尝试备选方案")
            self._fallback_click_tiktok(deviceid)

        # 打开 URL (use sound)
        try:
            self._debug(f"正在通过 iMouse 打开 URL: {url}")
            ret = self.api.shortcut_open_url(deviceid=deviceid, url=url, devlist=[deviceid], outtime=30000)
            if ret and ret.get('status', -1) != 0:
                self._debug(f"URL 打开失败，原因: {ret.get('message', '未知错误')}")
                return False
            self._debug("URL 打开成功")
        except Exception as e:
            self._debug(f"打开 URL 操作中发生异常: {e}")
            return False

        time.sleep(10)

        if not self._find_and_click_image(deviceid, 'icon/usesound.bmp'):
            self._debug("找Use sound失败，尝试备选方案")
            return False

        # 查找并点击模板图片
        self._debug("正在查找图片...")
        try:
            ret = self.api.find_image(deviceid, template_img_bytes, None, False, 0.7)
            if ret and ret.get('status', -1) in (0, 200):
                data = ret.get('data', {})
                if data.get('code', -1) == 0:
                    result = data.get('result', [])
                    if result and len(result) >= 2:
                        cx, cy = result[0], result[1]
                        self._debug(f"找到图片，点击图片 ({cx}, {cy})")
                        self.api.click(deviceid=deviceid, x=cx, y=cy, button='left', sync=True)
                        time.sleep(3)
                    else:
                        self._debug("未找到图片，跳过此条任务")
                        return False
                else:
                    self._debug("未找到图片，跳过此条任务")
                    return False
        except Exception as e:
            self._debug(f"查图异常: {e}")
            return False

        # 点击 next (两次)
        for i in range(2):
            if not self._find_and_click_image(deviceid, 'icon/next.bmp', required=False):
                self._debug(f"第{i+1}次点击 next 未找到，不影响后续流程")
            time.sleep(5)

        # 输入 title
        try:
            if os.path.exists('icon/Add a catchy title.bmp'):
                with open('icon/Add a catchy title.bmp', 'rb') as f:
                    icon_bytes = f.read()
                ret = self.api.find_image(deviceid, icon_bytes, None, False, 0.7)
                if ret and ret.get('status', -1) in (0, 200):
                    data = ret.get('data', {})
                    if data.get('code', -1) == 0:
                        result = data.get('result', [])
                        if result and len(result) >= 2:
                            cx, cy = result[0], result[1]
                            self._debug(f"找到title，点击位置 ({cx}, {cy})")
                            self.api.click(deviceid=deviceid, x=cx, y=cy, button='left', sync=True)
                            time.sleep(1)
                            self._input_text(deviceid, title)
                            time.sleep(2)
                            # 点击title下方输入description
                            self._debug(f"点击title下方位置 ({cx}, {cy + 50})")
                            self.api.click(deviceid=deviceid, x=cx, y=cy + 50, button='left', sync=True)
                            time.sleep(1)
                            self._input_text(deviceid, description)
                        else:
                            self._debug("未找到title")
                    else:
                        self._debug("未找到title")
            else:
                self._debug(f"查图用的文件不存在: icon/Add a catchy title.bmp")
                return False
        except Exception as e:
            self._debug(f"输入title异常: {e}")

        # 点击 post
        if not self._find_and_click_image(deviceid, 'icon/post.bmp'):
            self._debug("找post失败，尝试备选方案")
            return False

        return True

    def _open_tiktok_app_with_video(self, deviceid, row_data, template_img_bytes):
        """使用指定数据执行TikTok发布 (视频模式)"""
        description = row_data.get('description', 'testtesttest')

        self._debug("正在尝试打开 TikTok 应用...")
        self.api.send_key(deviceid=deviceid, fn_key='HOME', sync=True)
        time.sleep(2)
        self._debug("已发送HOME键，返回主屏幕")

        if not self._find_and_click_image(deviceid, 'icon/tiktok.bmp'):
            self._debug("打开TikTok应用失败，尝试备选方案")
            self._fallback_click_tiktok(deviceid)

        # 点击 + 按钮
        if not self._find_and_click_image(deviceid, 'icon/+white.bmp', required=False):
            if not self._find_and_click_image(deviceid, 'icon/+black.bmp'):
                self._debug("找 + 失败，尝试备选方案")
                return False

        # 查找并点击视频缩略图
        self._debug("正在查找视频...")
        try:
            ret = self.api.find_image(deviceid, template_img_bytes, None, False, 0.7)
            if ret and ret.get('status', -1) in (0, 200):
                data = ret.get('data', {})
                if data.get('code', -1) == 0:
                    result = data.get('result', [])
                    if result and len(result) >= 2:
                        cx, cy = result[0], result[1]
                        self._debug(f"找到视频，点击视频 ({cx}, {cy})")
                        self.api.click(deviceid=deviceid, x=cx, y=cy, button='left', sync=True)
                        time.sleep(3)
                    else:
                        self._debug("未找到视频，跳过此条任务")
                        return False
                else:
                    self._debug("未找到视频，跳过此条任务")
                    return False
        except Exception as e:
            self._debug(f"查视频异常: {e}")
            return False

        # 点击 next (两次)
        for i in range(2):
            if not self._find_and_click_image(deviceid, 'icon/next.bmp', required=False):
                self._debug(f"第{i+1}次点击 next 未找到，不影响后续流程")
            time.sleep(5)

        # 输入 description
        try:
            if os.path.exists('icon/Add description.bmp'):
                with open('icon/Add description.bmp', 'rb') as f:
                    icon_bytes = f.read()
                ret = self.api.find_image(deviceid, icon_bytes, None, False, 0.7)
                if ret and ret.get('status', -1) in (0, 200):
                    data = ret.get('data', {})
                    if data.get('code', -1) == 0:
                        result = data.get('result', [])
                        if result and len(result) >= 2:
                            cx, cy = result[0], result[1]
                            self._debug(f"找到Add description，点击位置 ({cx}, {cy})")
                            self.api.click(deviceid=deviceid, x=cx, y=cy, button='left', sync=True)
                            time.sleep(1)
                            self._input_text(deviceid, description)
                        else:
                            self._debug("未找到title")
                    else:
                        self._debug("找title失败，尝试备选方案")
                        return False
            else:
                self._debug(f"查图用的文件不存在: icon/Add description.bmp")
                return False
        except Exception as e:
            self._debug(f"输入Add description异常: {e}")

        # 点击 post
        if not self._find_and_click_image(deviceid, 'icon/post.bmp'):
            self._debug("找post失败，尝试备选方案")
            return False

        return True

    def _find_and_click_image(self, deviceid, image_path, offset_x=0, offset_y=0, threshold=0.7, required=True):
        """查找图像并点击的通用方法"""
        if not os.path.exists(image_path):
            self._debug(f"查图用的文件不存在: {image_path}")
            return not required

        self._debug(f"正在查找图像: {image_path}")
        try:
            with open(image_path, 'rb') as f:
                img_bytes = f.read()
            ret = self.api.find_image(deviceid, img_bytes, None, False, threshold)
            if ret and ret.get('status', -1) in (0, 200):
                data = ret.get('data', {})
                if data.get('code', -1) == 0:
                    result = data.get('result', [])
                    if result and len(result) >= 2:
                        click_x = result[0] + offset_x
                        click_y = result[1] + offset_y
                        self._debug(f"找到图像，点击位置 ({click_x}, {click_y})")
                        self.api.click(deviceid=deviceid, x=click_x, y=click_y, button='left', sync=True)
                        time.sleep(3)
                        return True
            self._debug(f"未找到图像: {image_path}")
            return False
        except Exception as e:
            self._debug(f"查找图像异常 {image_path}: {e}")
            return not required

    def _input_text(self, deviceid, text):
        """输入文本的通用方法"""
        try:
            self._debug(f"开始输入批量字符: {text}")
            self.api.send_text(deviceid=deviceid, text=text, sync=True)
            time.sleep(1)
            self._debug("输入批量字符完成")
            return True
        except Exception as e:
            self._debug(f"批量输入字符过程中发生异常: {e}")
            return False

    def _fallback_click_tiktok(self, deviceid):
        """直接打开备选"""
        self._debug("直接打开备选")
        time.sleep(3)
        return True

    def closeEvent(self, event):
        self.api.stop()

    def _show_img(self, img_data):
        self._img.loadFromData(img_data)
        pixmap = QPixmap.fromImage(self._img)
        item = QGraphicsPixmapItem(pixmap)
        scene = QGraphicsScene()
        scene.addItem(item)
        self.__ui.graphicsView.setScene(scene)
        self.__ui.graphicsView.fitInView(item)

    def _stop_screenshot_click(self):
        deviceid = self._get_selected_deviceid()
        self.api.loop_device_screenshot(deviceid=deviceid, time=100, stop=True, sync=False)

    def _add_device_list(self, data: dict, is_update: bool = False):
        if is_update:
            self.device_list.update(data)
        else:
            self.device_list = data

        for i in range(self.devlist_model.rowCount()):
            row_deviceid = self.devlist_model.index(i, 2).data()
            if row_deviceid and row_deviceid not in self.device_list:
                self.devlist_model.removeRow(i)

        for deviceid, info in self.device_list.items():
            # 查找是否已存在
            found_row = -1
            for i in range(self.devlist_model.rowCount()):
                if self.devlist_model.index(i, 2).data() == deviceid:
                    found_row = i
                    break

            name = info.get('name', '')
            username = info.get('user_name', '') or info.get('username', '')
            srvname = info.get('srv_name', '') or info.get('srvname', '')
            vid_pid = f"{info.get('vid', '')}|{info.get('pid', '')}" if info.get('vid') else ''
            device_name = info.get('device_name', '')
            version = info.get('version', '')
            state = '在线' if info.get('state', 0) != 0 else '离线'

            row_data = [name, username, deviceid, srvname, vid_pid, device_name, version, state]

            if found_row >= 0:
                for col, val in enumerate(row_data):
                    self.devlist_model.setItem(found_row, col, QStandardItem(str(val)))
            else:
                row_idx = self.devlist_model.rowCount()
                for col, val in enumerate(row_data):
                    self.devlist_model.setItem(row_idx, col, QStandardItem(str(val)))

        # 设置列宽
        widths = [100, 100, 130, 60, 80, 120, 60, 60]
        for i, w in enumerate(widths):
            self.devlist_tv.setColumnWidth(i, w)
        self.devlist_tv.horizontalHeader().setStretchLastSection(True)

    def _add_usb_list(self, data: dict):
        self.usb_list = data
        self.__ui.comboBox_3.clear()
        for key in self.usb_list.keys():
            self.__ui.comboBox_3.addItem(key)
        self.__ui.comboBox_3.addItem('取消绑定')

    def _get_selected_deviceid(self):
        if len(self.__ui.tableView_devlist.selectedIndexes()) == 0:
            self._debug("请先选择要操作的设备")
            return ''
        row = self.__ui.tableView_devlist.selectionModel().currentIndex().row()
        return self.devlist_model.index(row, 2).data()

    def _debug(self, log: str):
        self.__ui.textEdit_log.append(
            str('{} {}').format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), log)
        )

    def _binaryEvent(self, data: bytes):
        deviceid = data[:261].decode('utf-8').split('\x00')[0]
        isjpg = int.from_bytes(data[261:265], 'little')
        img_data = data[265:]
        print("收到设备{}的屏幕数据".format(deviceid))
        self._show_img(img_data)

    def _msgEvent(self, data: dict):
        fun = data.get('fun', '')
        status = data.get('status', 0)

        # 内部日志信号
        if fun == '_log':
            self._debug(data.get('message', ''))
            return

        # 推流码结果弹窗
        if fun == '_show_adcode_result':
            self._show_adcode_result_dialog(data.get('adcode_result', {}))
            return

        # 通用结果弹窗
        if fun == '_show_result_dialog':
            self._show_generic_result_dialog(data.get('title', '结果'), data.get('text', ''))
            return

        # 更新就绪弹窗
        if fun == '_show_update_ready':
            self._show_update_ready_dialog(data)
            return

        if status not in (0, 200):
            self._debug("调用 {} 接口失败，原因:{}".format(fun, data.get('message', '')))
            return

        self._debug("调用 {} 接口成功".format(fun))

        if fun == 'connect':
            self._debug("连接成功")
            self.api.get_device_list(sync=False)
            self.api.get_devicemodel_list(sync=False)
            self.api.get_usb_list(sync=False)
        elif fun == 'connect_disconnect':
            self._debug("连接断开")
        elif fun == 'im_connect':
            self._debug("内核已连接")
            self.api.get_device_list(sync=False)
            self.api.get_devicemodel_list(sync=False)
            self.api.get_usb_list(sync=False)
        elif fun == 'user_info':
            pass
        elif fun == 'dev_connect':
            _dev_data = data.get('data', {})
            _dev_list = []
            if isinstance(_dev_data, dict):
                _dev_list = _dev_data.get('list', [])
                if not isinstance(_dev_list, list): _dev_list = []
            for _d in _dev_list:
                if not isinstance(_d, dict): continue
                _did = _d.get('deviceid') or _d.get('mac') or _d.get('id', '')
                if _did:
                    self._debug("有设备连接 {}".format(_did))
                    self._add_device_list({_did: _d}, True)
        elif fun == 'dev_disconnect':
            _dev_data = data.get('data', {})
            _dev_list = []
            if isinstance(_dev_data, dict):
                _dev_list = _dev_data.get('list', [])
                if not isinstance(_dev_list, list): _dev_list = []
            for _d in _dev_list:
                if not isinstance(_d, dict): continue
                _did = _d.get('deviceid') or _d.get('mac') or _d.get('id', '')
                if _did:
                    self._debug("有设备断开连接 {}".format(_did))
                    self._add_device_list({_did: _d}, True)
        elif fun == 'dev_rotate':
            self._debug("设备屏幕方向发生变化 {}".format(data))
        elif fun == 'mouse_collection_cfg_ret':
            self._debug("鼠标坐标采集配置 {}".format(data))
        elif fun == 'collection':
            self._debug("手机打开采集页面回调 {}".format(data))
        elif fun in ('dev_change', 'set_dev', '/device/set'):
            _dev_data = data.get('data', {})
            _dev_list = []
            if isinstance(_dev_data, dict):
                _dev_list = _dev_data.get('list', [])
                if not isinstance(_dev_list, list): _dev_list = []
            for _d in _dev_list:
                if not isinstance(_d, dict): continue
                _did = _d.get('deviceid') or _d.get('mac') or _d.get('id', '')
                if _did:
                    self._debug("设备配置改变 {}".format(_did))
                    self._add_device_list({_did: _d}, True)
        elif fun in ('get_device_list', '/device/get'):
            self._debug("获取设备列表成功")
            _raw = data.get('data', {})
            if isinstance(_raw, dict):
                _lst = _raw.get('list', [])
                if isinstance(_lst, list):
                    _devdict = {}
                    for _dev in _lst:
                        if isinstance(_dev, dict):
                            _key = _dev.get('deviceid') or _dev.get('mac') or _dev.get('id', '')
                            if _key: _devdict[_key] = _dev
                    _raw = _devdict
            self._add_device_list(_raw)
        elif fun in ('get_devicemodel_list', '/config/devicemodel/get'):
            self._debug("获取支持型号列表成功")
            self.get_devicemodel_list = data.get('data', {})
        elif fun in ('get_usb_list', '/config/usb/get'):
            self._debug("获取usb硬件列表成功")
            self._add_usb_list(data.get('data', {}))
        elif fun in ('del_dev', '/device/del'):
            self._debug("删除设备成功")
            self.api.get_device_list(sync=False)

        if fun in ('get_device_screenshot', '/pic/screenshot'):
            img_data = base64_to_bmp(data)
            if img_data:
                self._show_img(img_data)

    def _on_message(self, data: dict):
        if data.get('fun') != 'get_device_screenshot':
            print("收到回调消息{}".format(data))
        self._signal_msgEvent.emit(data)

    def _on_binary(self, data: bytes):
        print("收到二进制消息")
        self._signal_binaryEvent.emit(data)

    # ═══════════════════════════ 一键删除所有设备相册 ═══════════════════════════

    def _delete_all_albums(self):
        """一键删除所有在线设备的相册图片（每次获取列表再逐批删除）"""
        if not self.device_list:
            self._debug("没有在线设备，无法执行删除")
            return

        online = {did: info for did, info in self.device_list.items()
                  if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备")
            return

        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.warning(self, "确认删除",
            f"确认要删除所有 {len(online)} 台在线设备的相册图片吗？\n\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._debug(f"开始删除 {len(online)} 台设备的相册...")
        threading.Thread(target=self._delete_all_albums_thread, args=(online,), daemon=True).start()

    def _delete_all_albums_thread(self, online_devices):
        """删除线程 - 先获取全部照片列表，再批量删除，3次重试"""
        success = 0
        fail = 0
        total = len(online_devices)
        MAX_RETRIES = 3
        BATCH_SIZE = 20  # 每次获取20张

        for idx, (deviceid, info) in enumerate(online_devices.items()):
            name = info.get('name', deviceid)
            self._debug_safe(f"[{idx+1}/{total}] 设备 {name}: 获取照片列表...")
            total_deleted = 0

            try:
                # 循环: 获取列表 → 删除 → 再获取，直到空
                round_num = 0
                while True:
                    round_num += 1

                    # 1. 获取照片列表（带重试）
                    ret = None
                    for retry in range(1, MAX_RETRIES + 1):
                        try:
                            ret = self.api.shortcut_photo_list(
                                deviceid=deviceid, num=BATCH_SIZE, date='', outtime=60000)
                            if ret is not None:
                                break
                        except Exception as e:
                            self._debug_safe(f"  {name}: 获取列表第{retry}次失败: {e}")
                            if retry < MAX_RETRIES:
                                time.sleep(3)

                    # 解析文件名
                    file_names = []
                    if ret and isinstance(ret, list):
                        for item in ret:
                            if isinstance(item, dict):
                                fn = item.get('name', '')
                                if fn:
                                    file_names.append(fn)
                            elif isinstance(item, str):
                                file_names.append(item)

                    if not file_names:
                        if total_deleted > 0:
                            self._debug_safe(f"  [OK] {name}: 相册已清空，共删除 {total_deleted} 张")
                        else:
                            self._debug_safe(f"  {name}: 相册为空")
                        success += 1
                        break

                    self._debug_safe(f"  {name}: 找到 {len(file_names)} 张照片，正在删除...")

                    # 2. 删除（带重试）+ 并行检测 Delete 确认弹窗
                    del_ok = False
                    for retry in range(1, MAX_RETRIES + 1):
                        try:
                            # 启动后台线程并行检测弹窗（在删除API调用期间）
                            confirm_thread = threading.Thread(
                                target=self._check_and_click_delete_confirm,
                                args=(deviceid, name), daemon=True)
                            confirm_thread.start()

                            del_ret = self.api.shortcut_del_photo(
                                deviceid=deviceid,
                                files=file_names,
                                devlist=[],
                                outtime=60000  # 1分钟超时
                            )

                            confirm_thread.join(timeout=5)

                            if del_ret and del_ret.get('status', -1) in (0, 200):
                                total_deleted += len(file_names)
                                self._debug_safe(f"  {name}: 删除 {len(file_names)} 张成功 (累计 {total_deleted})")
                                del_ok = True
                                break
                            else:
                                msg = del_ret.get('message', '未知错误') if del_ret else '无响应'
                                self._debug_safe(f"  {name}: 删除第{retry}次失败 - {msg}")
                                if retry < MAX_RETRIES:
                                    time.sleep(5)
                        except Exception as e:
                            self._debug_safe(f"  {name}: 删除第{retry}次异常: {e}")
                            if retry < MAX_RETRIES:
                                time.sleep(5)

                    if not del_ok:
                        self._debug_safe(f"  [FAIL] {name}: 删除3次重试均失败")
                        fail += 1
                        break

                    time.sleep(2)  # 删除间隔

            except Exception as e:
                self._debug_safe(f"  [ERROR] {name}: {e}")
                fail += 1

            time.sleep(1)

        self._debug_safe(f"删除完成: 成功 {success} / 失败 {fail} / 总计 {total}")

    def _check_and_click_delete_confirm(self, deviceid, name):
        """并行检测并点击 Delete 确认弹窗（OCR检测，45秒窗口，处理多次弹窗）"""
        try:
            c = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
            clicked_count = 0
            # 45秒内循环检测，每1.5秒一次
            for _ in range(30):
                time.sleep(1.5)
                try:
                    # 用OCR检测屏幕文字
                    ocr_result = c.ocr(deviceid)
                    if not ocr_result:
                        continue
                    texts = ocr_result if isinstance(ocr_result, list) else ocr_result.get("texts", ocr_result.get("result", []))
                    if not isinstance(texts, list):
                        continue

                    # 查找 "Delete" 按钮（红色按钮，不是 "Don't Delete"）
                    for item in texts:
                        if not isinstance(item, dict):
                            continue
                        text = item.get("text", "").strip()
                        # 匹配 "Delete" 但排除 "Don't Delete"
                        if text == "Delete":
                            # 获取坐标
                            x = item.get("x", 0)
                            y = item.get("y", 0)
                            if x > 0 and y > 0:
                                c.tap(deviceid, x, y)
                                clicked_count += 1
                                self._debug_safe(f"  {name}: OCR检测到 Delete 弹窗，已点击 ({x},{y}) [第{clicked_count}次]")
                                time.sleep(2)
                                break  # 跳出内层for，继续外层循环检测下一次弹窗
                except Exception:
                    continue
        except Exception:
            pass

    def _debug_safe(self, msg):
        """线程安全的日志输出"""
        if threading.current_thread() is threading.main_thread():
            self._debug(msg)
        else:
            # 从非主线程通过信号发送
            self._signal_msgEvent.emit({"fun": "_log", "status": 0, "message": msg})

    # ═══════════════════════════ 获取当天视频数据 ═══════════════════════════

    def _fetch_video_data(self):
        """单独执行 Phase 1: 从 TikHub 拉取当天视频数据并写入飞书"""
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块，请安装: pip install requests")
            return
        self._debug("开始获取当天视频数据...")
        threading.Thread(target=self._fetch_video_data_thread, daemon=True).start()

    def _fetch_video_data_thread(self):
        """Phase 1 线程: 拉取视频数据"""
        try:
            run_adcode_full(
                phase="1", port=IMOUSE_XP_PORT, workers=PHASE2_DEFAULT_WORKERS,
                days=1, videos_str="", match_mode="name", log_fn=self._debug_safe)
        except Exception as e:
            self._debug_safe(f"获取视频数据异常: {e}")

    # ═══════════════════════════ 选定日期: 获取视频数据 ═══════════════════════════

    def _pick_date_dialog(self):
        """弹出日期选择对话框，返回 ['YYYYMMDD'] 或 None"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QCalendarWidget, QPushButton, QHBoxLayout
        from PyQt6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle("选择日期")
        dlg.resize(350, 300)
        layout = QVBoxLayout(dlg)
        cal = QCalendarWidget()
        cal.setSelectedDate(QDate.currentDate().addDays(-1))
        layout.addWidget(cal)
        btn_row = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_ok.setStyleSheet("QPushButton{background:#1976D2;color:white;padding:8px 20px;border:none;border-radius:4px;font-weight:bold;}")
        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet("QPushButton{background:#757575;color:white;padding:8px 20px;border:none;border-radius:4px;}")
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = cal.selectedDate()
            return [f"{d.year()}{d.month():02d}{d.day():02d}"]
        return None

    def _fetch_video_data_selected(self):
        """获取选定日期的视频数据（只拉在线设备对应的账号）"""
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块"); return
        dates = self._pick_date_dialog()
        if not dates:
            self._debug("已取消"); return
        if not self.device_list:
            self._debug("没有设备，请先刷新设备列表"); return
        online = {did: info for did, info in self.device_list.items() if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备"); return
        # 收集在线设备的自定义名和设备名作为合法账号id
        valid_ids = set()
        for did, info in online.items():
            n = info.get('name', '').strip()
            u = info.get('username', '').strip()
            if n: valid_ids.add(_normalize_account_id(n))
            if u: valid_ids.add(_normalize_account_id(u))
        self._debug(f"选定日期视频数据: 日期={dates}, 在线设备={len(online)}台, 合法账号数={len(valid_ids)}")
        threading.Thread(target=self._fetch_video_selected_thread, args=(dates, valid_ids), daemon=True).start()

    def _fetch_video_selected_thread(self, dates, valid_ids):
        """选定日期视频数据线程"""
        try:
            feishu = _FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN)
            tikhub = _TikHubClient()

            # 获取飞书账号表中「更新中」的账号
            recs = feishu.search_records(ACCOUNT_TABLE_ID, view_id=ACCOUNT_VIEW_ID,
                filter_obj={"conjunction":"and","conditions":[{"field_name":ACCOUNT_FIELDS["status"],"operator":"is","value":["更新中"]}]})
            all_accounts = []
            for rec in recs:
                f = rec.get("fields") or {}
                uid = _normalize_account_id(_normalize_text(f.get(ACCOUNT_FIELDS["account_id"])))
                if uid:
                    all_accounts.append({
                        "unique_id": uid,
                        "name": _normalize_text(f.get(ACCOUNT_FIELDS["account_name"])),
                        "record_id": rec.get("record_id", "")
                    })
            self._debug_safe(f"  飞书账号表共 {len(all_accounts)} 个更新中账号")

            # 只保留在线设备对应的账号
            accounts = [a for a in all_accounts if a["unique_id"] in valid_ids]
            self._debug_safe(f"  匹配在线设备: {len(accounts)} 个账号")
            if not accounts:
                self._debug_safe("没有匹配到在线设备的账号"); return

            # 计算日期范围
            date_strs = sorted(dates)
            earliest = datetime.strptime(date_strs[0], "%Y%m%d").replace(tzinfo=timezone.utc)
            pub_after = int(earliest.timestamp())

            def _fetch_one(acc):
                uid = acc["unique_id"]
                for attempt in range(1, 3):
                    try:
                        th = _TikHubClient()
                        # 直接用 unique_id 调 app/v3 V3→V2→V1
                        vids = th.fetch_user_videos(None, 30, pub_after, unique_id=uid)
                        if not vids:
                            # fallback: 查 sec_uid 再用 web
                            ui = th.fetch_user_info(uid)
                            if ui:
                                vids = th.fetch_user_videos(ui["sec_uid"], 30, pub_after)
                        # 过滤选定日期
                        filtered = []
                        for v in vids:
                            if v.get("is_pinned"): continue
                            ct = v.get("create_time")
                            if ct:
                                d = datetime.fromtimestamp(int(ct), tz=timezone.utc).strftime("%Y%m%d")
                                if d in set(dates):
                                    filtered.append(v)
                        self._debug_safe(f"  {uid}: {len(filtered)} 个视频 (选定日期)")
                        return uid, filtered
                    except Exception as e:
                        self._debug_safe(f"  {uid}: 第{attempt}次异常: {e}")
                        if attempt < 2: time.sleep(1)
                return uid, []

            self._debug_safe(f"  并发拉取 {len(accounts)} 个账号 (10并发)...")
            video_data = {}
            with ThreadPoolExecutor(max_workers=10) as pool:
                futs = {pool.submit(_fetch_one, acc): acc for acc in accounts}
                for fut in as_completed(futs):
                    uid, vids = fut.result()
                    if vids: video_data[uid] = vids

            if not video_data:
                self._debug_safe("未拉取到任何视频数据"); return

            # ── 写入飞书（和 Phase 1 逻辑一样） ──
            self._debug_safe(f"写入飞书视频管理表...")
            existing = feishu.search_records(VIDEO_TABLE_ID, view_id=VIDEO_VIEW_ID)
            existing_vids = set()
            vid_to_rec = {}
            for rec in existing:
                f = rec.get("fields") or {}
                vid = _normalize_text(f.get(VIDEO_FIELDS["vid"]))
                link_val = f.get(VIDEO_FIELDS["video_link"])
                link_url = ""
                if isinstance(link_val, dict): link_url = link_val.get("link","") or link_val.get("text","")
                elif isinstance(link_val, str): link_url = link_val
                link_id = ""
                if link_url:
                    m = re.search(r'/(?:photo|video)/(\d+)', link_url)
                    if m: link_id = m.group(1)
                ad_code = _normalize_text(f.get(VIDEO_FIELDS["ad_code"]))
                rid = rec.get("record_id", "")
                rec_info = {"record_id": rid, "ad_code": ad_code or None}
                for aweme_id in (vid, link_id):
                    if aweme_id:
                        existing_vids.add(aweme_id)
                        vid_to_rec[aweme_id] = rec_info

            # 从旧账号表查询 account_id → record_id 映射（视频表"账号编号"字段关联到旧表）
            self._debug_safe("  从旧账号表获取 record_id 映射...")
            try:
                old_recs = feishu.search_records(OLD_ACCOUNT_TABLE_ID)
                uid_to_rid = {}
                for rec in old_recs:
                    f = rec.get("fields") or {}
                    uid = _normalize_account_id(_normalize_text(f.get(OLD_ACCOUNT_FIELD_ACCOUNT_ID)))
                    if uid and rec.get("record_id"):
                        uid_to_rid[uid] = rec["record_id"]
                self._debug_safe(f"  旧账号表映射 {len(uid_to_rid)} 条")
            except Exception as e:
                self._debug_safe(f"  查询旧账号表失败: {e}")
                uid_to_rid = {}

            new_recs = []
            unlinked_count = 0
            for uid, vids in video_data.items():
                arid = uid_to_rid.get(uid)
                if not arid:
                    unlinked_count += len(vids)
                for v in vids:
                    aid = v["aweme_id"]
                    if aid in existing_vids: continue
                    clean_url = f"https://www.tiktok.com/@{uid}/video/{aid}"
                    rec = {
                        VIDEO_FIELDS["video_link"]: {"link": clean_url, "text": clean_url},
                        VIDEO_FIELDS["play_count"]: v.get("play_count", 0),
                        VIDEO_FIELDS["like_count"]: str(v.get("digg_count", 0)),
                        VIDEO_FIELDS["upload_time"]: int(time.time() * 1000),
                        VIDEO_FIELDS["account_id"]: uid,
                        VIDEO_FIELDS["vid"]: aid,
                    }
                    if v.get("create_time"):
                        rec[VIDEO_FIELDS["publish_date"]] = int(v["create_time"]) * 1000
                        if "publish_date_text" in VIDEO_FIELDS:
                            rec[VIDEO_FIELDS["publish_date_text"]] = datetime.fromtimestamp(int(v["create_time"]), tz=timezone.utc).strftime("%Y%m%d")
                    if arid:
                        rec[VIDEO_FIELDS["account_link"]] = [arid]
                    new_recs.append(rec)
            if unlinked_count:
                self._debug_safe(f"  警告: {unlinked_count} 个视频在旧账号表中找不到对应账号，账号编号字段会为空")

            if new_recs:
                self._debug_safe(f"  新增 {len(new_recs)} 条记录到飞书...")
                try:
                    feishu.batch_create_records(VIDEO_TABLE_ID, [{"fields": r} for r in new_recs])
                    self._debug_safe(f"  写入成功")
                except Exception as e:
                    self._debug_safe(f"  写入失败: {e}")
            else:
                self._debug_safe("  无新记录需要写入")

            total_vids = sum(len(v) for v in video_data.values())
            self._debug_safe(f"选定日期视频数据完成: {len(video_data)} 个账号, {total_vids} 个视频, 新增 {len(new_recs)} 条")

        except Exception as e:
            self._debug_safe(f"选定日期视频数据异常: {e}")
            import traceback
            self._debug_safe(traceback.format_exc())

    # ═══════════════════════════ 选定日期: 获取推流码 ═══════════════════════════

    def _adcode_selected(self, match_mode='name'):
        """选定日期推流码: 从飞书读该日期视频 → 直接在对应设备上打开链接获取推流码"""
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块"); return
        dates = self._pick_date_dialog()
        if not dates:
            self._debug("已取消"); return
        if not self.device_list:
            self._debug("没有设备，请先刷新设备列表"); return
        online = {did: info for did, info in self.device_list.items() if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备"); return

        mode_label = "自定义名" if match_mode == 'name' else "设备名"
        self._debug(f"选定日期推流码 (匹配: {mode_label}, 日期: {dates})")
        threading.Thread(target=self._adcode_selected_thread,
                         args=(dates, online, match_mode), daemon=True).start()

    def _adcode_selected_thread(self, dates, online_devices, match_mode):
        """选定日期推流码线程 match_mode='name'(自定义名) 或 'username'(设备名)"""
        try:
            feishu = _FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN)

            # 1. 从飞书读取选定日期的视频
            self._debug_safe("步骤1: 从飞书读取选定日期视频...")
            all_records = feishu.search_records(VIDEO_TABLE_ID, view_id=VIDEO_VIEW_ID)
            date_set = set(dates)
            filtered = []
            for rec in all_records:
                f = rec.get("fields") or {}
                pub_text = _normalize_text(f.get(VIDEO_FIELDS.get("publish_date_text", "")))
                if pub_text not in date_set: continue
                ad_code = _normalize_text(f.get(VIDEO_FIELDS.get("ad_code", "")))
                if ad_code: continue  # 已有推流码，跳过
                acc_id = _normalize_text(f.get(VIDEO_FIELDS["account_id"]))
                link_val = f.get(VIDEO_FIELDS["video_link"])
                link_url = ""
                if isinstance(link_val, dict):
                    link_url = link_val.get("link", "") or link_val.get("text", "")
                elif isinstance(link_val, str):
                    link_url = link_val
                if not link_url: continue
                filtered.append({
                    "record_id": rec.get("record_id"),
                    "account_id": acc_id,
                    "link": link_url,
                })
            self._debug_safe(f"  需获取推流码: {len(filtered)} 条视频")
            if not filtered:
                self._debug_safe("没有需要获取推流码的视频（全部已有或无匹配日期）"); return

            # 2. 建立设备映射: name=自定义名(info['name']), group=设备名(info['username'])
            dev_map = {}
            dev_map_lower = {}
            for did, info in online_devices.items():
                key = (info.get('name', '') if match_mode == 'name' else info.get('user_name', info.get('username', ''))).strip()
                if key:
                    dev_map[key] = did
                    dev_map_lower[key.lower()] = did
            self._debug_safe(f"  在线设备映射({len(dev_map)}台): {list(dev_map.keys())}")

            # 3. 将视频分配到对应设备
            from collections import defaultdict
            device_tasks = defaultdict(list)
            unmatched_count = 0
            for rec in filtered:
                acc_id = rec.get("account_id", "").strip()
                _did = dev_map.get(acc_id) or dev_map_lower.get(acc_id.lower())
                if _did:
                    device_tasks[_did].append(rec)
                else:
                    unmatched_count += 1

            matched_count = sum(len(v) for v in device_tasks.values())
            self._debug_safe(f"  匹配成功: {matched_count} 条, 未匹配: {unmatched_count} 条")
            for _did, _recs in device_tasks.items():
                _info = online_devices.get(_did, {})
                _dname = _info.get('name', _did)
                self._debug_safe(f"    {_dname}: {len(_recs)} 个视频")
            if not device_tasks:
                self._debug_safe("没有匹配到任何设备"); return

            # 4. 并发执行推流码获取
            self._debug_safe(f"步骤2: 开始获取推流码 ({len(device_tasks)} 台设备并发)...")
            results_lock = threading.Lock()
            results = {"success": [], "fail": []}

            def _process_adcode_device(did, dev_recs):
                dinfo = online_devices.get(did, {})
                name = dinfo.get('name', did)
                c = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
                self._debug_safe(f"  设备 {name}: {len(dev_recs)} 个视频")

                for ti, rec in enumerate(dev_recs):
                    link = rec.get("link", "")
                    record_id = rec.get("record_id")
                    self._debug_safe(f"  [{name}] {ti+1}/{len(dev_recs)}: 打开视频...")

                    try:
                        # 直接打开视频链接
                        c.open_url(did, link)
                        time.sleep(T_APP_LAUNCH + 2)
                        c.fix_landscape(did, log=self._debug_safe)
                        # 关闭可能弹出的弹窗
                        _dismiss_popup(c, did)
                        time.sleep(1.0)

                        # 推流码流程（_do_ad_auth_flow 内部会先点三个点）
                        ad_code = _do_ad_auth_flow(c, did, is_first=(ti == 0), log_fn=self._debug_safe)

                        if ad_code:
                            self._debug_safe(f"  [{name}] 推流码: {ad_code}")
                            # 写回飞书
                            if record_id:
                                try:
                                    _fs = _FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN)
                                    _fs.batch_update_records(VIDEO_TABLE_ID, [{
                                        "record_id": record_id,
                                        "fields": {VIDEO_FIELDS["ad_code"]: ad_code}
                                    }])
                                    self._debug_safe(f"  [{name}] 飞书写入成功")
                                except Exception as _fe:
                                    self._debug_safe(f"  [{name}] 飞书写入失败: {_fe}")
                            with results_lock:
                                results["success"].append({"name": name, "link": link, "code": ad_code})
                        else:
                            self._debug_safe(f"  [{name}] 推流码获取失败")
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "推流码获取失败"})

                        # 返回视频页
                        c.tap(did, PX["back"][0], PX["back"][1]); time.sleep(2)
                        c.tap(did, PX["back"][0], PX["back"][1]); time.sleep(1.5)

                    except Exception as e:
                        self._debug_safe(f"  [{name}] 异常: {e}")
                        with results_lock:
                            results["fail"].append({"name": name, "link": link, "reason": str(e)})

                return name

            workers = min(4, len(device_tasks))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = {pool.submit(_process_adcode_device, did, recs): did
                        for did, recs in device_tasks.items()}
                for fut in as_completed(futs):
                    try:
                        name = fut.result()
                        self._debug_safe(f"  设备 {name} 处理完成")
                    except Exception as e:
                        self._debug_safe(f"  设备处理异常: {e}")

            # 5. 弹窗结果
            total_should = matched_count
            total_success = len(results["success"])
            total_fail = len(results["fail"])
            lines = [
                f"应获取: {total_should} 个推流码",
                f"实际成功: {total_success} 个",
                f"未成功: {total_fail} 个",
            ]
            if results["fail"]:
                lines.append("")
                lines.append("═══ 未成功明细 ═══")
                for r in results["fail"]:
                    lines.append(f"  {r['name']}  →  {r['reason']}")
            if results["success"]:
                lines.append("")
                lines.append("═══ 成功明细 ═══")
                for r in results["success"]:
                    lines.append(f"  {r['name']}  →  {r['code']}")

            self._signal_msgEvent.emit({
                "fun": "_show_result_dialog", "status": 0,
                "title": f"选定日期推流码  ✓{total_success}/{total_should}",
                "text": "\n".join(lines)
            })

        except Exception as e:
            self._debug_safe(f"选定日期推流码异常: {e}")
            import traceback
            self._debug_safe(traceback.format_exc())

    # ═══════════════════════════ 获取推流码 ═══════════════════════════

    def _run_adcode(self, match_mode):
        """启动推流码获取 (仅 Phase 2，直接读飞书数据) match_mode='name'(自定义名) 或 'username'(设备名)"""
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块，请安装: pip install requests")
            return
        if not self.device_list:
            self._debug("没有在线设备")
            return

        mode_label = "按名字" if match_mode == "name" else "按分组"
        self._debug(f"启动推流码获取 ({mode_label})，从飞书读取已有数据...")
        threading.Thread(target=self._adcode_thread, args=(match_mode,), daemon=True).start()

    def _adcode_thread(self, match_mode):
        """推流码获取线程 (仅 Phase 2，不再重新抓视频数据)"""
        try:
            result = run_adcode_full(
                phase="2", port=IMOUSE_XP_PORT, workers=PHASE2_DEFAULT_WORKERS,
                days=1, videos_str="", match_mode=match_mode, log_fn=self._debug_safe)
            if result and result.get("results"):
                # 通过信号在主线程弹窗
                self._signal_msgEvent.emit({
                    "fun": "_show_adcode_result",
                    "status": 0,
                    "adcode_result": result
                })
        except Exception as e:
            self._debug_safe(f"推流码异常: {e}")

    # ═══════════════════════════ 自动更新 ═══════════════════════════

    def _check_update(self):
        """检查更新：从 GitHub 拉取 version.json，对比文件哈希"""
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块"); return
        self._debug(f"检查更新中... 当前版本: {LOCAL_VERSION}")
        threading.Thread(target=self._check_update_thread, daemon=True).start()

    def _check_update_thread(self):
        import hashlib, subprocess
        try:
            # 1. 查询多个源的 version.json，取最新版本（避免CDN缓存降级）
            best_remote = None
            best_version = ""
            best_url = ""
            for base_url in UPDATE_URLS:
                try:
                    r = _requests.get(f"{base_url}/version.json?t={int(time.time())}", timeout=6)
                    if r.status_code == 200:
                        data = r.json()
                        v = data.get(UPDATE_CHANNEL, {}).get("version", "")
                        if v and (not best_version or _version_ge(v, best_version)) and v != best_version:
                            best_remote = data
                            best_version = v
                            best_url = base_url
                        elif not best_remote and v:
                            best_remote = data; best_version = v; best_url = base_url
                        # GitHub raw 原生总是最新，拿到就停止查询
                        if 'raw.githubusercontent' in base_url:
                            break
                except Exception as e:
                    self._debug_safe(f"  源失败 {base_url}: {str(e)[:80]}")
                    continue
            if not best_remote:
                self._debug_safe("检查更新失败: 所有源都无法访问"); return
            self._debug_safe(f"  使用源: {best_url}")
            remote_data = best_remote

            channel_data = remote_data.get(UPDATE_CHANNEL, {})
            remote_version = channel_data.get("version", "")
            remote_files = channel_data.get("files", {})
            changelog = channel_data.get("changelog", "")

            if not remote_files:
                self._debug_safe(f"版本信息格式错误"); return

            self._debug_safe(f"  远程版本: {remote_version}")
            if changelog:
                self._debug_safe(f"  更新说明: {changelog}")

            # 2. 对比版本号：本地 >= 远程 则不更新（防止CDN缓存旧version.json导致降级）
            if _version_ge(LOCAL_VERSION, remote_version):
                self._debug_safe(f"  本地 {LOCAL_VERSION} >= 远程 {remote_version}，无需更新")
                self._signal_msgEvent.emit({
                    "fun": "_show_result_dialog", "status": 0,
                    "title": "检查更新", "text": f"已是最新版本 {LOCAL_VERSION}（远程: {remote_version}）"
                })
                return

            # 需要更新的文件列表
            changed = list(remote_files.keys())
            self._debug_safe(f"  需更新 {len(changed)} 个文件: {remote_version}")

            # 3. 下载到临时目录
            tmp_dir = os.path.join(SCRIPT_DIR, ".update_tmp")
            if os.path.exists(tmp_dir):
                import shutil as _sh; _sh.rmtree(tmp_dir, ignore_errors=True)
            os.makedirs(tmp_dir, exist_ok=True)

            download_ok = True
            # 下载URL加 ?v=版本号 作为缓存破坏参数
            _cache_buster = f"?v={remote_version}"
            for fn in changed:
                self._debug_safe(f"  下载: {fn}")
                downloaded = False
                for base_url in UPDATE_URLS:
                    try:
                        r = _requests.get(f"{base_url}/{fn}{_cache_buster}", timeout=60)
                        if r.status_code == 200 and len(r.content) > 100:
                            # 确保子目录存在
                            out_path = os.path.join(tmp_dir, fn)
                            os.makedirs(os.path.dirname(out_path), exist_ok=True)
                            with open(out_path, 'wb') as f:
                                f.write(r.content)
                            downloaded = True
                            self._debug_safe(f"    OK ({len(r.content)} bytes)")
                            break
                    except Exception as e:
                        self._debug_safe(f"    源失败: {e}")
                if not downloaded:
                    self._debug_safe(f"  下载失败: {fn}")
                    download_ok = False
                    break

            if not download_ok:
                self._debug_safe("更新中断"); return

            # 4. 生成更新批处理脚本
            bat_path = os.path.join(SCRIPT_DIR, "_do_update.bat")
            lines = [
                "@echo off",
                "chcp 65001 > nul",
                "title iMouse 更新中",
                "echo 等待程序退出...",
                "timeout /t 3 /nobreak > nul",
            ]
            for fn in changed:
                # 处理子目录
                sub = os.path.dirname(fn)
                if sub:
                    lines.append(f'if not exist "{sub}" mkdir "{sub}"')
                lines.append(f'copy /Y ".update_tmp\\{fn}" "{fn}" > nul')
                lines.append(f'echo 已更新: {fn}')
            lines.extend([
                'rd /s /q .update_tmp',
                'echo 更新完成，正在重启...',
                'timeout /t 1 /nobreak > nul',
                'start "" run.bat',
                'del "%~f0"',
            ])
            with open(bat_path, 'w', encoding='gbk', errors='replace') as f:
                f.write("\r\n".join(lines))

            # 5. 弹窗提示用户重启
            self._signal_msgEvent.emit({
                "fun": "_show_update_ready", "status": 0,
                "remote_version": remote_version,
                "changelog": changelog,
                "files": changed,
                "bat_path": bat_path,
            })
        except Exception as e:
            import traceback
            self._debug_safe(f"检查更新异常: {e}")
            self._debug_safe(traceback.format_exc())

    def _show_update_ready_dialog(self, data):
        """更新就绪弹窗 - 用户点确定后执行更新"""
        from PyQt6.QtWidgets import QMessageBox
        import subprocess
        remote_version = data.get("remote_version", "")
        changelog = data.get("changelog", "")
        files = data.get("files", [])
        bat_path = data.get("bat_path", "")

        msg = f"发现新版本: {remote_version}\n"
        if changelog: msg += f"更新说明: {changelog}\n"
        msg += f"\n已下载 {len(files)} 个文件:\n" + "\n".join(f"  - {fn}" for fn in files)
        msg += "\n\n点击 OK 后程序将自动重启以应用更新。"

        ret = QMessageBox.information(self, "更新就绪", msg, QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if ret == QMessageBox.StandardButton.Ok:
            subprocess.Popen(['cmd', '/c', 'start', '', bat_path], shell=False, cwd=SCRIPT_DIR)
            QApplication.quit()

    def _gen_fail_report(self):
        """生成未成功信息：对比在线设备与飞书表，列出当天无推流码的视频"""
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块"); return
        if not self.device_list:
            self._debug("没有设备，请先刷新设备列表"); return
        online = {did: info for did, info in self.device_list.items()
                  if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备"); return
        self._debug("生成未成功信息...")
        threading.Thread(target=self._gen_fail_report_thread, args=(online,), daemon=True).start()

    def _gen_fail_report_thread(self, online_devices):
        try:
            feishu = _FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN)

            # 收集在线设备的名字和分组名
            dev_names = set()
            dev_groups = set()
            for did, info in online_devices.items():
                name = info.get('name', '').strip()
                group = info.get('group', info.get('groupname', '')).strip()
                if name: dev_names.add(name)
                if group: dev_groups.add(group)
            self._debug_safe(f"在线设备: {len(dev_names)} 个名字, {len(dev_groups)} 个分组")

            # 读取飞书当天视频
            recs = feishu.search_records(VIDEO_TABLE_ID,
                filter_obj={"conjunction": "and", "conditions": [
                    {"field_name": VIDEO_FIELDS["publish_date"], "operator": "is", "value": ["Today"]}
                ]}, view_id=VIDEO_VIEW_ID)
            self._debug_safe(f"飞书当天视频: {len(recs)} 条")

            # 过滤：账号id匹配在线设备名或分组名 且 无推流码
            fail_list = []
            for rec in recs:
                f = rec.get("fields") or {}
                acc_id = _normalize_text(f.get(VIDEO_FIELDS["account_id"]))
                ad_code = _normalize_text(f.get(VIDEO_FIELDS.get("ad_code", "")))
                if ad_code: continue  # 已有推流码，跳过

                # 匹配设备名或分组名
                if acc_id not in dev_names and acc_id not in dev_groups:
                    continue

                link_val = f.get(VIDEO_FIELDS["video_link"])
                link_url = ""
                if isinstance(link_val, dict):
                    link_url = link_val.get("link", "") or link_val.get("text", "")
                elif isinstance(link_val, str):
                    link_url = link_val

                fail_list.append(f"{acc_id}  - {link_url}")

            self._debug_safe(f"未成功: {len(fail_list)} 条")

            if not fail_list:
                text = "当前在线设备对应的当天视频全部已有推流码，无未成功记录。"
            else:
                text = "\n".join(fail_list)

            self._signal_msgEvent.emit({
                "fun": "_show_result_dialog",
                "status": 0,
                "title": f"未成功信息 ({len(fail_list)} 条)",
                "text": text
            })

        except Exception as e:
            self._debug_safe(f"生成未成功信息异常: {e}")
            import traceback
            self._debug_safe(traceback.format_exc())

    def _show_adcode_result_dialog(self, result_data):
        """推流码完成后显示结果弹窗"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel
        from PyQt6.QtCore import Qt

        results = result_data.get("results", [])
        match_mode = result_data.get("match_mode", "name")
        mode_label = "名字" if match_mode == "name" else "分组"

        # 分类成功/失败
        success_list = []
        fail_list = []
        all_failed_links = []

        for r in results:
            display_name = r.get("name", r.get("uid", "?"))
            uid = r.get("uid", "")
            ok = r.get("ok", 0)
            total = r.get("total", 0)
            failed_links = r.get("failed_links", [])

            if ok == total and total > 0:
                success_list.append(f"{display_name} ({uid}): {ok}/{total} 全部成功")
            elif ok > 0:
                success_list.append(f"{display_name} ({uid}): {ok}/{total} 部分成功")
                for link in failed_links:
                    all_failed_links.append(f"  [{display_name}] {link}")
            else:
                fail_list.append(f"{display_name} ({uid}): 0/{total} 全部失败")
                for link in failed_links:
                    all_failed_links.append(f"  [{display_name}] {link}")

        # 构建显示文本
        lines = []
        lines.append(f"═══ 推流码获取结果 (按{mode_label}) ═══")
        lines.append("")

        total_ok = sum(r.get("ok", 0) for r in results)
        total_all = sum(r.get("total", 0) for r in results)
        lines.append(f"总计: {total_ok}/{total_all} 个视频获取推流码成功")
        lines.append("")

        if success_list:
            lines.append(f"✓ 成功设备 ({len(success_list)}):")
            for s in success_list:
                lines.append(f"  {s}")
            lines.append("")

        if fail_list:
            lines.append(f"✗ 失败设备 ({len(fail_list)}):")
            for f in fail_list:
                lines.append(f"  {f}")
            lines.append("")

        if all_failed_links:
            lines.append(f"未获取推流码的视频链接 ({len(all_failed_links)}):")
            for link in all_failed_links:
                lines.append(link)

        text = "\n".join(lines)

        # 创建弹窗
        dlg = QDialog(self)
        dlg.setWindowTitle(f"推流码结果 - 按{mode_label}")
        dlg.resize(650, 500)
        dlg.setStyleSheet("""
            QDialog { background: white; }
            QTextEdit { border: 1px solid #CCC; font-family: Consolas, monospace; font-size: 13px;
                        background: #FAFAFA; color: #333333; padding: 8px; }
            QPushButton { padding: 8px 20px; border-radius: 4px; font-weight: bold; }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)

        # 标题
        title_lbl = QLabel(f"推流码获取完成 — 成功 {total_ok}/{total_all}")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1565C0; padding: 4px 0;")
        layout.addWidget(title_lbl)

        # 内容
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        layout.addWidget(text_edit)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_copy = QPushButton("复制内容")
        btn_copy.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border: none; }"
            "QPushButton:hover { background-color: #1565C0; }")
        btn_copy.clicked.connect(lambda: (
            QApplication.clipboard().setText(text),
            btn_copy.setText("已复制 ✓"),
        ))
        btn_layout.addWidget(btn_copy)

        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(
            "QPushButton { background-color: #757575; color: white; border: none; }"
            "QPushButton:hover { background-color: #616161; }")
        btn_close.clicked.connect(dlg.close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)
        dlg.exec()

    def _show_generic_result_dialog(self, title, text):
        """通用结果弹窗（带复制按钮）"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(600, 400)
        dlg.setStyleSheet("""
            QDialog { background: white; }
            QTextEdit { border: 1px solid #CCC; font-family: Consolas, monospace; font-size: 13px;
                        background: #FAFAFA; color: #333333; padding: 8px; }
            QPushButton { padding: 8px 20px; border-radius: 4px; font-weight: bold; }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1565C0; padding: 4px 0;")
        layout.addWidget(title_lbl)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_copy = QPushButton("复制内容")
        btn_copy.setStyleSheet("QPushButton { background-color: #1976D2; color: white; border: none; }")
        btn_copy.clicked.connect(lambda: (
            QApplication.clipboard().setText(text),
            btn_copy.setText("已复制 ✓"),
        ))
        btn_layout.addWidget(btn_copy)
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet("QPushButton { background-color: #757575; color: white; border: none; }")
        btn_close.clicked.connect(dlg.close)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        dlg.exec()

    # ═══════════════════════════ 飞书完播率 (Tab5) ═══════════════════════════

    def _update_calendar(self):
        """更新日历网格"""
        import calendar
        year = self.__ui.spinBox_year.value()
        month = self.__ui.spinBox_month.value()
        cal = calendar.Calendar(firstweekday=6)  # 周日开始
        days = list(cal.itermonthdays(year, month))

        for i, btn in enumerate(self.__ui.day_buttons):
            if i < len(days) and days[i] != 0:
                btn.setText(str(days[i]))
                btn.setVisible(True)
                btn.setChecked(False)
            else:
                btn.setText("")
                btn.setVisible(False)
                btn.setChecked(False)
        self._update_selected_dates_label()

    def _select_all_days(self):
        """选取当月全部日"""
        for btn in self.__ui.day_buttons:
            if btn.isVisible() and btn.text():
                btn.setChecked(True)
        self._update_selected_dates_label()

    def _clear_all_days(self):
        """清空选择"""
        for btn in self.__ui.day_buttons:
            btn.setChecked(False)
        self._update_selected_dates_label()

    def _update_selected_dates_label(self):
        """更新已选日期显示"""
        dates = self._get_selected_dates()
        if dates:
            self.__ui.label_selected_dates.setText(f"已选: {', '.join(dates)}")
        else:
            self.__ui.label_selected_dates.setText("已选: 无")

    def _get_selected_dates(self):
        """获取选中的日期列表 (格式: ['20260301', '20260302', ...])"""
        year = self.__ui.spinBox_year.value()
        month = self.__ui.spinBox_month.value()
        dates = []
        for btn in self.__ui.day_buttons:
            if btn.isChecked() and btn.text():
                day = int(btn.text())
                dates.append(f"{year}{month:02d}{day:02d}")
        return sorted(dates)

    def _feishu_completion_rate(self, match_mode='name'):
        """飞书完播率: 选日期 → 飞书读视频 → TikHub更新 → 设备获取完播率"""
        dates = self._get_selected_dates()
        if not dates:
            self._debug("请先选择日期"); return
        if not self.device_list:
            self._debug("没有设备，请先刷新设备列表"); return
        online = {did: info for did, info in self.device_list.items()
                  if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备"); return
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块"); return

        mode_str = "自定义名" if match_mode == 'name' else "设备名"
        self._debug(f"飞书完播率 (匹配: {mode_str}, 日期: {len(dates)}天)")
        threading.Thread(
            target=self._feishu_completion_rate_thread,
            args=(dates, online, match_mode), daemon=True).start()

    def _feishu_completion_rate_thread(self, dates, online_devices, match_mode='name'):
        """飞书完播率线程"""
        try:
            feishu = _FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN)
            tikhub = _TikHubClient()

            # 1. 从飞书读取选定日期的视频
            self._debug_safe(f"步骤1: 从飞书读取视频...")
            all_records = feishu.search_records(VIDEO_TABLE_ID, view_id=VIDEO_VIEW_ID)
            self._debug_safe(f"  飞书表共 {len(all_records)} 条记录")

            # 按日期过滤
            date_set = set(dates)
            filtered = []
            for rec in all_records:
                f = rec.get("fields") or {}
                pub_text = _normalize_text(f.get(VIDEO_FIELDS.get("publish_date_text", "")))
                if pub_text in date_set:
                    vid = _normalize_text(f.get(VIDEO_FIELDS["vid"]))
                    acc_id = _normalize_text(f.get(VIDEO_FIELDS["account_id"]))
                    link_val = f.get(VIDEO_FIELDS["video_link"])
                    link_url = ""
                    if isinstance(link_val, dict):
                        link_url = link_val.get("link", "") or link_val.get("text", "")
                    elif isinstance(link_val, str):
                        link_url = link_val
                    ad_code = _normalize_text(f.get(VIDEO_FIELDS.get("ad_code", "")))
                    play_count = f.get(VIDEO_FIELDS["play_count"])
                    like_count = f.get(VIDEO_FIELDS["like_count"])
                    filtered.append({
                        "record_id": rec.get("record_id"),
                        "vid": vid, "account_id": acc_id,
                        "link": link_url, "ad_code": ad_code,
                        "play_count": play_count, "like_count": like_count,
                        "pub_date": pub_text,
                    })

            self._debug_safe(f"  选定日期匹配: {len(filtered)} 条视频")
            if not filtered:
                self._debug_safe("没有匹配的视频"); return

            # 2. TikHub 更新播放量/点赞量（始终拉取最新数据）
            self._debug_safe(f"步骤2: TikHub 更新播放量/点赞量（共 {len(filtered)} 条）...")
            needs_stats = [r for r in filtered if r.get("link")]
            if needs_stats:
                updates = []

                def _fetch_stats(rec):
                    link = rec["link"]
                    th = _TikHubClient()
                    stats = th.fetch_video_stats(link)
                    return rec, stats

                with ThreadPoolExecutor(max_workers=5) as pool:
                    futs = {pool.submit(_fetch_stats, r): r for r in needs_stats}
                    done = 0
                    for fut in as_completed(futs):
                        done += 1
                        rec, stats = fut.result()
                        if stats:
                            rec["play_count"] = stats.get("play_count", 0)
                            rec["like_count"] = stats.get("digg_count", 0)
                            updates.append({
                                "record_id": rec["record_id"],
                                "fields": {
                                    VIDEO_FIELDS["play_count"]: stats.get("play_count", 0),
                                    VIDEO_FIELDS["like_count"]: str(stats.get("digg_count", 0)),
                                }
                            })
                        if done % 10 == 0 or done == len(needs_stats):
                            self._debug_safe(f"  TikHub进度: {done}/{len(needs_stats)}, 已获取: {len(updates)} 条")

                if updates:
                    try:
                        feishu.batch_update_records(VIDEO_TABLE_ID, updates)
                        self._debug_safe(f"  播放量/点赞量已更新 {len(updates)} 条到飞书")
                    except Exception as e:
                        self._debug_safe(f"  更新飞书失败: {e}")
                else:
                    self._debug_safe("  TikHub未获取到任何数据")

            # 3. 匹配设备
            mode_label = "自定义名" if match_mode == 'name' else "设备名"
            self._debug_safe(f"步骤3: 匹配设备 ({mode_label})...")
            sorted_devices = sorted(online_devices.items(), key=lambda x: x[1].get('name', ''))

            # 大小写不敏感的映射
            dev_map = {}        # 原始key → did
            dev_map_lower = {}  # lower key → did
            for did, info in sorted_devices:
                # 自定义名: info['name']；设备名: info['username']
                key = (info.get('name', '') if match_mode == 'name' else info.get('user_name', info.get('username', ''))).strip()
                if key:
                    dev_map[key] = did
                    dev_map_lower[key.lower()] = did

            # 打印在线设备名供对照
            _dev_names = list(dev_map.keys())
            self._debug_safe(f"  在线设备({len(_dev_names)}台): {_dev_names}")

            # 按设备分组任务（先精确匹配，再大小写不敏感匹配）
            from collections import defaultdict
            device_tasks = defaultdict(list)
            unmatched = []
            for rec in filtered:
                acc_id = rec.get("account_id", "").strip()
                if acc_id in dev_map:
                    device_tasks[dev_map[acc_id]].append(rec)
                elif acc_id.lower() in dev_map_lower:
                    device_tasks[dev_map_lower[acc_id.lower()]].append(rec)
                else:
                    unmatched.append(rec)

            matched_count = sum(len(v) for v in device_tasks.values())
            self._debug_safe(f"  匹配成功: {matched_count} 条, 未匹配在线设备: {len(dev_map) - len(device_tasks)} 台")
            for _did, _recs in device_tasks.items():
                _info = online_devices.get(_did, {})
                _dname = _info.get('name', _did) if match_mode == 'name' else _info.get('username', _did)
                self._debug_safe(f"    {_dname}: {len(_recs)} 个视频")
            # 显示在线但没有匹配到视频的设备
            _no_video_devs = []
            for _did, _did_val in dev_map.items():
                if _did_val not in device_tasks:
                    _no_video_devs.append(_did)
            if _no_video_devs:
                self._debug_safe(f"  在线但无视频的设备: {_no_video_devs}")
            if not device_tasks:
                self._debug_safe("没有匹配到任何设备"); return

            # 4. 获取完播率
            self._debug_safe(f"步骤4: 开始获取完播率 ({len(device_tasks)} 台设备并发)...")
            ic = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
            results_lock = threading.Lock()
            results = {"success": [], "fail": []}

            def _process_device_rate(did, dev_recs):
                dinfo = online_devices.get(did, {})
                name = dinfo.get('name', did)
                c = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
                self._debug_safe(f"  设备 {name}: {len(dev_recs)} 个视频")

                for ti, rec in enumerate(dev_recs):
                    link = rec.get("link", "")
                    if not link:
                        continue
                    self._debug_safe(f"  [{name}] {ti+1}/{len(dev_recs)}: 打开视频...")

                    try:
                        # 打开视频
                        c.open_url(did, link)
                        time.sleep(4)

                        # 横屏检测
                        c.fix_landscape(did, log=self._debug_safe)

                        # 点三个点
                        _find_click_three_dots(c, did)
                        time.sleep(1.5)

                        # 点击 Analytics
                        analytics_icon = _load_icon("icon/analytics.bmp")
                        if not analytics_icon:
                            self._debug_safe(f"  [{name}] 缺少 icon/analytics.bmp")
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "缺少analytics.bmp图标"})
                            continue
                        pos = c.find_image(did, analytics_icon, 0.75)
                        if not pos:
                            self._debug_safe(f"  [{name}] 未找到Analytics按钮")
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "未找到Analytics按钮"})
                            continue
                        c.tap(did, pos[0], pos[1])
                        time.sleep(2)

                        # 往下滑到中间
                        c.swipe_vertical(did, 600, 300, x=200)
                        time.sleep(1.5)

                        # 全屏OCR查找 "Traffic sources" 定位白色球体
                        def _ocr_find_traffic_y(_c, _did, _name, _log):
                            raw = _c.ocr(_did)
                            if not raw:
                                _log(f"  [{_name}] OCR返回空")
                                return None
                            # 兼容多种结构
                            items = raw
                            if isinstance(raw, dict):
                                for k in ("texts", "result", "items"):
                                    v = raw.get(k)
                                    if isinstance(v, list): items = v; break
                                    if isinstance(v, dict):
                                        for k2 in ("texts", "result", "items"):
                                            v2 = v.get(k2)
                                            if isinstance(v2, list): items = v2; break
                            if not isinstance(items, list):
                                _log(f"  [{_name}] OCR结构未知: {type(raw)}")
                                return None
                            all_texts = []
                            found_y = None
                            for it in items:
                                if not isinstance(it, dict): continue
                                t = it.get("text","")
                                all_texts.append(t)
                                if "traffic" in t.lower() or "sources" in t.lower():
                                    y = it.get("y") or it.get("top") or it.get("cy")
                                    rect = it.get("rect") or it.get("box")
                                    if y is None and isinstance(rect,(list,tuple)) and len(rect)>=2:
                                        y = rect[1]
                                    if y and int(y) > 0:
                                        found_y = int(y)
                                        _log(f"  [{_name}] OCR找到'{t}' y={y}")
                                        break
                            _log(f"  [{_name}] OCR全屏文字: {all_texts}")
                            return found_y

                        ball_pos = None
                        # 先在当前滚动位置尝试，再微调往上/往下各滚一次
                        _scroll_offsets = [0, -100, 100]
                        for _soff in _scroll_offsets:
                            if _soff != 0:
                                c.swipe_vertical(did, 300 + _soff, 300, x=200)
                                time.sleep(1)
                            for _ in range(2):
                                _ty = _ocr_find_traffic_y(c, did, name, self._debug_safe)
                                if _ty:
                                    ball_pos = (35, _ty - 90)
                                    self._debug_safe(f"  [{name}] 球体定位 {ball_pos}")
                                    break
                                time.sleep(1)
                            if ball_pos: break

                        if not ball_pos:
                            self._debug_safe(f"  [{name}] OCR未找到Traffic sources，尝试全屏识图")
                            _ball_icon = _load_icon("icon/white_ball.bmp")
                            if _ball_icon:
                                for _sim in (0.65, 0.55, 0.45):
                                    for _ in range(2):
                                        _bp = c.find_image(did, _ball_icon, _sim)
                                        if _bp and 150 < _bp[1] < 800 and 10 < _bp[0] < 400:
                                            ball_pos = _bp; break
                                        elif _bp:
                                            self._debug_safe(f"  [{name}] 识图坐标不合理 sim={_sim} {_bp}，忽略")
                                        time.sleep(1)
                                    if ball_pos:
                                        self._debug_safe(f"  [{name}] 识图找到球体 sim={_sim} {ball_pos}")
                                        break

                        if not ball_pos:
                            self._debug_safe(f"  [{name}] 未找到白色球体，跳过")
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "未找到球体"})
                            continue

                        # 长按住球体，步进拖到 x=355，保持按住
                        c.drag_to(did, ball_pos[0], ball_pos[1], 355, ball_pos[1])
                        time.sleep(1.5)  # 等气泡出现，此时仍按住

                        def _grab_rate(_c, _did, _by, _name, _log):
                            """按住时截图，裁左侧+增强后pytesseract读数，过滤50/100"""
                            try:
                                import base64 as _b64
                                from io import BytesIO
                                from PIL import Image as _PIL, ImageEnhance as _IE
                                ss = _c._post("/pic/screenshot",
                                              {"id": _did, "jpg": True})
                                if not ss or ss.get("status") != 200:
                                    _log(f"  [{_name}] 截图失败: {ss}")
                                    return None
                                _d = ss.get("data", {})
                                img_b64 = _d.get("img") or _d.get("screenshot")
                                if not img_b64:
                                    _log(f"  [{_name}] 截图数据空, keys={list(_d.keys())}")
                                    return None
                                full_img = _PIL.open(BytesIO(_b64.b64decode(img_b64))).convert("RGB")
                                _log(f"  [{_name}] 截图尺寸: {full_img.size}")
                                # x<330排除右侧轴标签，y取球体上方
                                crop = full_img.crop((0, max(0, _by-150), 330, min(full_img.height, _by+50)))
                                # 放大3倍+灰度+对比度增强，提升OCR准确率
                                w, h = crop.size
                                crop = crop.resize((w*3, h*3), _PIL.LANCZOS)
                                crop = crop.convert("L")
                                crop = _IE.Contrast(crop).enhance(3.0)
                                crop = _IE.Sharpness(crop).enhance(2.0)
                                try:
                                    import pytesseract
                                    import os as _os
                                    for _tpath in [
                                        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                                        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                                    ]:
                                        if _os.path.exists(_tpath):
                                            pytesseract.pytesseract.tesseract_cmd = _tpath
                                            break
                                    text = pytesseract.image_to_string(
                                        crop, config="--psm 6 -c tessedit_char_whitelist=0123456789.%")
                                    _log(f"  [{_name}] 截图OCR原文: {text.strip()!r}")
                                    for _m in re.finditer(r'(\d*\.\d+)\s*%?', text):
                                        val = float(_m.group(1))
                                        if not (abs(val - 50) < 0.5 or abs(val - 100) < 0.5):
                                            return val
                                except ImportError:
                                    _log(f"  [{_name}] pytesseract未安装")
                                except Exception as _te:
                                    _log(f"  [{_name}] pytesseract异常: {_te}")
                            except Exception as _e:
                                _log(f"  [{_name}] 截图处理异常: {_e}")
                            return None

                        # 按住时截图读数，读完再松手
                        completion_rate = _grab_rate(c, did, ball_pos[1], name, self._debug_safe)
                        c.mouse_release(did, 355, ball_pos[1])

                        # 兜底：松手后设备OCR，过滤50/100
                        if completion_rate is None:
                            time.sleep(1)
                            for _rect in [[0, ball_pos[1]-150, 330, 100], [0, ball_pos[1]-150, 330, 200]]:
                                _raw = c.ocr(did, rect=_rect)
                                if not _raw: continue
                                _items = _raw if isinstance(_raw, list) else _raw.get("texts", _raw.get("result", []))
                                _texts = [i.get("text","") if isinstance(i,dict) else str(i) for i in (_items if isinstance(_items,list) else [])]
                                self._debug_safe(f"  [{name}] 设备OCR: {_texts}")
                                _full = " ".join(_texts)
                                for _m in re.finditer(r'(\d*\.\d+)\s*%?', _full):
                                    _v = float(_m.group(1))
                                    if not (abs(_v - 50) < 0.5 or abs(_v - 100) < 0.5):
                                        completion_rate = _v; break
                                if completion_rate is not None: break

                        if completion_rate is not None:
                            self._debug_safe(f"  [{name}] 完播率: {completion_rate}%")
                            # 写回飞书
                            _rec_id = rec.get("record_id")
                            if not _rec_id:
                                self._debug_safe(f"  [{name}] 无record_id，跳过飞书写入")
                            else:
                                try:
                                    _fs = _FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN)
                                    _resp = _fs._s.post(
                                        f"{_fs.BASE_URL}/open-apis/bitable/v1/apps/{_fs.app_token}/tables/{VIDEO_TABLE_ID}/records/batch_update",
                                        headers=_fs._headers(),
                                        json={"records": [{"record_id": _rec_id, "fields": {VIDEO_FIELDS["completion_rate"]: completion_rate}}]},
                                        timeout=30
                                    ).json()
                                    if _resp.get("code") == 0:
                                        self._debug_safe(f"  [{name}] 飞书写入成功")
                                    else:
                                        self._debug_safe(f"  [{name}] 飞书写入失败: code={_resp.get('code')} msg={_resp.get('msg')}")
                                except Exception as _fe:
                                    self._debug_safe(f"  [{name}] 飞书写入异常: {_fe}")
                            with results_lock:
                                results["success"].append({"name": name, "link": link, "rate": completion_rate})
                        else:
                            self._debug_safe(f"  [{name}] 无法读取完播率")
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "OCR失败"})

                    except Exception as e:
                        self._debug_safe(f"  [{name}] 异常: {e}")
                        with results_lock:
                            results["fail"].append({"name": name, "link": link, "reason": str(e)})

                return name

            workers = min(4, len(device_tasks))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = {pool.submit(_process_device_rate, did, recs): did
                        for did, recs in device_tasks.items()}
                for fut in as_completed(futs):
                    try:
                        name = fut.result()
                        self._debug_safe(f"  设备 {name} 处理完成")
                    except Exception as e:
                        self._debug_safe(f"  设备处理异常: {e}")

            # 5. 弹窗显示结果
            total_should = matched_count
            total_success = len(results["success"])
            total_fail = len(results["fail"])
            lines = [
                f"应抓取: {total_should} 个视频",
                f"实际成功: {total_success} 个",
                f"未成功: {total_fail} 个",
            ]
            if results["fail"]:
                lines.append("")
                lines.append("═══ 未成功明细 ═══")
                for r in results["fail"]:
                    _link_short = r['link'].split('/')[-1] if r['link'] else '-'
                    lines.append(f"  {r['name']}  →  {r['reason']}  ({_link_short})")
            if results["success"]:
                lines.append("")
                lines.append("═══ 成功明细 ═══")
                for r in results["success"]:
                    _link_short = r['link'].split('/')[-1] if r['link'] else '-'
                    lines.append(f"  {r['name']}  →  {r['rate']}%  ({_link_short})")

            self._signal_msgEvent.emit({
                "fun": "_show_result_dialog",
                "status": 0,
                "title": f"飞书完播率完成  ✓{total_success}/{total_should}",
                "text": "\n".join(lines)
            })

        except Exception as e:
            self._debug_safe(f"飞书完播率异常: {e}")
            import traceback
            self._debug_safe(traceback.format_exc())

    # ═══════════════════════════ 测试完播率 (Tab6 测试) ═══════════════════════════

    def _test_completion_rate(self):
        """测试完播率: 读测试表 → 按自定义名匹配设备 → 抓完播率 → 写回测试表"""
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块"); return
        if not self.device_list:
            self._debug("没有设备，请先刷新设备列表"); return
        online = {did: info for did, info in self.device_list.items()
                  if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备"); return
        if getattr(self, '_test_running', False):
            self._debug("[测试完播率] 已有测试在运行，请先停止或等待完成")
            return
        self._test_stop_event.clear()
        self._test_running = True
        self._debug(f"[测试] 开始测试完播率流程（使用测试表，不影响正式表）")
        self._debug(f"[测试] 点 ⏹ 停止测试 可中止")
        threading.Thread(target=self._test_completion_rate_thread,
                         args=(online,), daemon=True).start()

    def _test_completion_rate_thread(self, online_devices):
        """测试完播率线程：从测试表读视频 → 抓完播率 → 写回测试表"""
        try:
            # 1. 从测试表读视频（测试表app_token不同）
            self._debug_safe("[测试] 步骤1: 从测试表读取视频...")
            test_fs = _FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET, TEST_APP_TOKEN)
            all_records = test_fs.search_records(TEST_VIDEO_TABLE_ID, view_id=TEST_VIDEO_VIEW_ID)
            self._debug_safe(f"  测试表共 {len(all_records)} 条记录")

            filtered = []
            for rec in all_records:
                f = rec.get("fields") or {}
                link_val = f.get("视频发布链接")
                link_url = ""
                if isinstance(link_val, dict):
                    link_url = link_val.get("link", "") or link_val.get("text", "")
                elif isinstance(link_val, str):
                    link_url = link_val
                if not link_url: continue
                # 从链接提取账号id (@xxx/video/...)
                m = re.search(r'tiktok\.com/@([\w.]+)/', link_url)
                acc_id = m.group(1) if m else ""
                # 跳过已有完播率的
                existing_rate = f.get("T7 完播率")
                if existing_rate is not None and existing_rate != "":
                    continue
                filtered.append({
                    "record_id": rec.get("record_id"),
                    "account_id": acc_id,
                    "link": link_url,
                })
            self._debug_safe(f"  待测试: {len(filtered)} 条（跳过已有完播率的）")
            if not filtered:
                self._debug_safe("[测试] 测试表没有需要抓的视频"); return

            # 2. 按自定义名匹配设备
            dev_map = {}
            dev_map_lower = {}
            for did, info in online_devices.items():
                key = info.get('name', '').strip()
                if key:
                    dev_map[key] = did
                    dev_map_lower[key.lower()] = did
            self._debug_safe(f"  在线设备映射({len(dev_map)}台): {list(dev_map.keys())[:10]}...")

            from collections import defaultdict
            device_tasks = defaultdict(list)
            unmatched = 0
            for rec in filtered:
                acc_id = rec["account_id"].strip()
                _did = dev_map.get(acc_id) or dev_map_lower.get(acc_id.lower())
                if _did:
                    device_tasks[_did].append(rec)
                else:
                    unmatched += 1

            matched_count = sum(len(v) for v in device_tasks.values())
            self._debug_safe(f"  匹配成功: {matched_count} 条, 未匹配: {unmatched} 条")
            for _did, _recs in device_tasks.items():
                _dname = online_devices.get(_did, {}).get('name', _did)
                self._debug_safe(f"    {_dname}: {len(_recs)} 个视频")
            if not device_tasks:
                self._debug_safe("[测试] 没有匹配到任何设备"); return

            # 3. 抓完播率
            self._debug_safe(f"[测试] 步骤2: 开始抓取完播率 ({len(device_tasks)} 台设备并发)...")
            results_lock = threading.Lock()
            results = {"success": [], "fail": []}

            def _test_process_device(did, dev_recs):
                dinfo = online_devices.get(did, {})
                name = dinfo.get('name', did)
                c = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
                self._debug_safe(f"  [{name}] 开始: {len(dev_recs)} 个视频")

                for ti, rec in enumerate(dev_recs):
                    if self._test_stop_event.is_set():
                        self._debug_safe(f"  [{name}] 收到停止信号，退出"); return name
                    link = rec["link"]
                    record_id = rec["record_id"]
                    self._debug_safe(f"  [{name}] {ti+1}/{len(dev_recs)}: 打开视频...")
                    try:
                        c.open_url(did, link)
                        time.sleep(4)
                        c.fix_landscape(did, log=self._debug_safe)
                        _find_click_three_dots(c, did); time.sleep(1.5)

                        # Analytics
                        analytics_icon = _load_icon("icon/analytics.bmp")
                        if not analytics_icon:
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "缺少analytics.bmp"})
                            continue
                        pos = c.find_image(did, analytics_icon, 0.75)
                        if not pos:
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "未找到Analytics按钮"})
                            continue
                        c.tap(did, pos[0], pos[1]); time.sleep(2)
                        c.swipe_vertical(did, 600, 300, x=200); time.sleep(1.5)

                        # 找Traffic sources定位白球
                        def _ocr_find_y(_c, _did):
                            raw = _c.ocr(_did)
                            if not raw: return None
                            items = raw if isinstance(raw, list) else raw.get("texts", raw.get("result", []))
                            for it in items:
                                if not isinstance(it, dict): continue
                                t = it.get("text", "")
                                if "traffic" in t.lower() or "sources" in t.lower():
                                    y = it.get("y") or it.get("top") or it.get("cy")
                                    rect = it.get("rect") or it.get("box")
                                    if y is None and isinstance(rect, (list, tuple)) and len(rect) >= 2:
                                        y = rect[1]
                                    if y and int(y) > 0: return int(y)
                            return None

                        ball_pos = None
                        for _soff in [0, -100, 100]:
                            if _soff != 0:
                                c.swipe_vertical(did, 300 + _soff, 300, x=200); time.sleep(1)
                            for _ in range(2):
                                _ty = _ocr_find_y(c, did)
                                if _ty:
                                    ball_pos = (35, _ty - 90); break
                                time.sleep(1)
                            if ball_pos: break

                        if not ball_pos:
                            _ball_icon = _load_icon("icon/white_ball.bmp")
                            if _ball_icon:
                                for _sim in (0.65, 0.55, 0.45):
                                    _bp = c.find_image(did, _ball_icon, _sim)
                                    if _bp and 150 < _bp[1] < 800 and 10 < _bp[0] < 400:
                                        ball_pos = _bp; break

                        if not ball_pos:
                            self._debug_safe(f"  [{name}] 未找到白球")
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "未找到球体"})
                            continue

                        # 拖拽+截图读完播率
                        c.drag_to(did, ball_pos[0], ball_pos[1], 355, ball_pos[1])
                        time.sleep(1.5)

                        completion_rate = None
                        try:
                            import base64 as _b64
                            from io import BytesIO
                            from PIL import Image as _PIL, ImageEnhance as _IE
                            ss = c._post("get_device_screenshot",
                                         {"deviceid": did, "isJpg": True, "gzip": False, "original": False})
                            if ss and ss.get("status") == 0:
                                _d = ss.get("data", {})
                                img_b64 = _d.get("img") or _d.get("screenshot")
                                if img_b64:
                                    full_img = _PIL.open(BytesIO(_b64.b64decode(img_b64))).convert("RGB")
                                    _by = ball_pos[1]
                                    crop = full_img.crop((0, max(0, _by-150), 330, min(full_img.height, _by+50)))
                                    w, h = crop.size
                                    crop = crop.resize((w*3, h*3), _PIL.LANCZOS).convert("L")
                                    crop = _IE.Contrast(crop).enhance(3.0)
                                    crop = _IE.Sharpness(crop).enhance(2.0)
                                    try:
                                        import pytesseract
                                        import os as _os
                                        for _tp in [r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                                                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
                                            if _os.path.exists(_tp):
                                                pytesseract.pytesseract.tesseract_cmd = _tp; break
                                        text = pytesseract.image_to_string(
                                            crop, config="--psm 6 -c tessedit_char_whitelist=0123456789.%")
                                        for _m in re.finditer(r'(\d*\.\d+)\s*%?', text):
                                            val = float(_m.group(1))
                                            if not (abs(val-50)<0.5 or abs(val-100)<0.5):
                                                completion_rate = val; break
                                    except: pass
                        except Exception as e:
                            self._debug_safe(f"  [{name}] 截图异常: {e}")

                        c.mouse_release(did, 355, ball_pos[1])

                        if completion_rate is not None:
                            self._debug_safe(f"  [{name}] 完播率: {completion_rate}%")
                            # 写回测试表
                            try:
                                resp = test_fs._s.post(
                                    f"{test_fs.BASE_URL}/open-apis/bitable/v1/apps/{TEST_APP_TOKEN}/tables/{TEST_VIDEO_TABLE_ID}/records/batch_update",
                                    headers=test_fs._headers(),
                                    json={"records": [{"record_id": record_id, "fields": {"T7 完播率": completion_rate}}]},
                                    timeout=30).json()
                                if resp.get("code") == 0:
                                    self._debug_safe(f"  [{name}] 测试表写入成功")
                                else:
                                    self._debug_safe(f"  [{name}] 测试表写入失败: code={resp.get('code')} msg={resp.get('msg')}")
                            except Exception as e:
                                self._debug_safe(f"  [{name}] 测试表写入异常: {e}")
                            with results_lock:
                                results["success"].append({"name": name, "link": link, "rate": completion_rate})
                        else:
                            self._debug_safe(f"  [{name}] 完播率读取失败")
                            with results_lock:
                                results["fail"].append({"name": name, "link": link, "reason": "OCR失败"})
                    except Exception as e:
                        self._debug_safe(f"  [{name}] 异常: {e}")
                        with results_lock:
                            results["fail"].append({"name": name, "link": link, "reason": str(e)})
                return name

            workers = min(4, len(device_tasks))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = {pool.submit(_test_process_device, did, recs): did
                        for did, recs in device_tasks.items()}
                for fut in as_completed(futs):
                    try:
                        name = fut.result()
                        self._debug_safe(f"  设备 {name} 完成")
                    except Exception as e:
                        self._debug_safe(f"  设备异常: {e}")

            # 弹窗
            ts = matched_count
            ok = len(results["success"])
            fl = len(results["fail"])
            lines = [
                f"[测试完播率] 应抓: {ts}, 成功: {ok}, 失败: {fl}",
                "",
                f"测试表: {TEST_VIDEO_TABLE_ID}",
                f"已把成功的完播率写入测试表的「T7 完播率」字段",
            ]
            if results["fail"]:
                lines.append(""); lines.append("═══ 失败明细 ═══")
                for r in results["fail"]:
                    _ls = r['link'].split('/')[-1] if r['link'] else '-'
                    lines.append(f"  {r['name']} → {r['reason']} ({_ls})")
            if results["success"]:
                lines.append(""); lines.append("═══ 成功明细 ═══")
                for r in results["success"]:
                    _ls = r['link'].split('/')[-1] if r['link'] else '-'
                    lines.append(f"  {r['name']} → {r['rate']}% ({_ls})")

            self._signal_msgEvent.emit({
                "fun": "_show_result_dialog", "status": 0,
                "title": f"测试完播率完成  ✓{ok}/{ts}",
                "text": "\n".join(lines)
            })
        except Exception as e:
            self._debug_safe(f"[测试] 异常: {e}")
            import traceback
            self._debug_safe(traceback.format_exc())
        finally:
            self._test_stop_event.clear()
            self._test_running = False

    # ═══════════════════════════ 测试抓取推流码 ═══════════════════════════

    def _test_stop(self):
        """点击停止按钮：设置 stop event，让测试线程尽快退出"""
        if hasattr(self, '_test_stop_event'):
            self._test_stop_event.set()
            self._debug("[停止测试] 已发送停止信号，当前步骤完成后退出")
        else:
            self._debug("[停止测试] 没有正在运行的测试")

    def _test_adcode(self):
        """测试抓取推流码：不读表、不匹配，对所有在线设备直接执行抓取流程"""
        if not self.device_list:
            self._debug("没有设备，请先刷新设备列表"); return
        online = {did: info for did, info in self.device_list.items()
                  if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备"); return
        # 并发防护: 检查是否已有测试在跑
        if getattr(self, '_test_running', False):
            self._debug("[测试推流码] 已有测试在运行，请先停止或等待完成")
            return
        # 重置停止事件
        self._test_stop_event.clear()
        self._test_running = True
        self._debug(f"[测试推流码] 对 {len(online)} 台在线设备顺序执行抓取流程（慢速模式方便观察）")
        self._debug(f"[测试推流码] 前提: 手机当前已打开TikTok视频。点 ⏹ 停止测试 可中止")
        threading.Thread(target=self._test_adcode_thread, args=(online,), daemon=True).start()

    def _test_adcode_thread(self, online_devices):
        """测试推流码抓取线程 - 串行执行，慢速模式，支持中途停止"""
        try:
            results = {"success": [], "fail": [], "skipped": []}
            stop_cb = lambda: self._test_stop_event.is_set()

            # 按自定义名排序，串行执行
            sorted_devs = sorted(online_devices.items(), key=lambda x: x[1].get('name', ''))
            total = len(sorted_devs)

            for idx, (did, info) in enumerate(sorted_devs):
                name = info.get('name', did)
                if stop_cb():
                    self._debug_safe(f"[测试推流码] 已停止，剩余 {total - idx} 台设备未执行")
                    for _did, _info in sorted_devs[idx:]:
                        results["skipped"].append({"name": _info.get('name', _did)})
                    break

                self._debug_safe(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                self._debug_safe(f"  [{idx+1}/{total}] 设备 {name}")
                self._debug_safe(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                c = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
                try:
                    # 横屏检测
                    c.fix_landscape(did, log=self._debug_safe)
                    # 跑完整推流码抓取流程（慢速模式）
                    ad_code = _do_ad_auth_flow(c, did, is_first=True,
                                               log_fn=self._debug_safe,
                                               stop_check=stop_cb,
                                               slow=True,
                                               tag=name)
                    if stop_cb() and not ad_code:
                        results["skipped"].append({"name": name})
                        continue
                    if ad_code:
                        self._debug_safe(f"  [{name}] ✓ 推流码: {ad_code}")
                        results["success"].append({"name": name, "code": ad_code})
                    else:
                        self._debug_safe(f"  [{name}] ✗ 未获取到推流码")
                        results["fail"].append({"name": name, "reason": "流程走完但剪贴板没读到推流码"})
                except Exception as e:
                    self._debug_safe(f"  [{name}] 异常: {e}")
                    results["fail"].append({"name": name, "reason": str(e)})
                # 设备间等待
                time.sleep(1.5)

            # 弹窗
            ok = len(results["success"])
            fl = len(results["fail"])
            sk = len(results["skipped"])
            lines = [
                f"[测试推流码] 在线设备: {total}",
                f"  成功: {ok}, 失败: {fl}, 已跳过: {sk}",
            ]
            if results["success"]:
                lines.append(""); lines.append("═══ 成功明细 ═══")
                for r in results["success"]:
                    lines.append(f"  {r['name']} → {r['code']}")
            if results["fail"]:
                lines.append(""); lines.append("═══ 失败明细 ═══")
                for r in results["fail"]:
                    lines.append(f"  {r['name']} → {r['reason']}")
            if results["skipped"]:
                lines.append(""); lines.append("═══ 已跳过 (手动停止) ═══")
                for r in results["skipped"]:
                    lines.append(f"  {r['name']}")

            self._signal_msgEvent.emit({
                "fun": "_show_result_dialog", "status": 0,
                "title": f"测试推流码完成  ✓{ok}/{total}",
                "text": "\n".join(lines)
            })
        except Exception as e:
            self._debug_safe(f"[测试推流码] 异常: {e}")
            import traceback
            self._debug_safe(traceback.format_exc())
        finally:
            self._test_stop_event.clear()
            self._test_running = False

    # ═══════════════════════════ 完播率分析 (Tab4 本地Excel) ═══════════════════════════

    def _select_analytics_excel(self):
        """选择完播率分析的Excel文件"""
        fp, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel Files (*.xlsx *.xls)")
        if fp:
            self.__ui.lineEdit_analytics_excel.setText(fp)
            self._debug(f"已选择: {fp}")

    def _fetch_video_stats_from_excel(self):
        """步骤1: 读取Excel中的视频链接，通过TikHub获取播放量/点赞量"""
        fp = self.__ui.lineEdit_analytics_excel.text().strip()
        if not fp or not os.path.isfile(fp):
            self._debug("请先选择Excel文件")
            return
        if not HAS_REQUESTS:
            self._debug("缺少 requests 模块")
            return
        self._debug("开始获取视频统计数据...")
        threading.Thread(target=self._fetch_stats_thread, args=(fp,), daemon=True).start()

    def _fetch_stats_thread(self, excel_path):
        """获取播放量/点赞量线程 (5并发, 3重试)"""
        try:
            df = pd.read_excel(excel_path)
            self._debug_safe(f"读取Excel: {len(df)} 行")

            # 查找视频链接列
            link_col = None
            for col in df.columns:
                if '视频链接' in str(col) or 'video_link' in str(col).lower() or '链接' in str(col):
                    link_col = col; break
            if not link_col:
                self._debug_safe("未找到'视频链接'列，请确保Excel包含此列")
                return
            self._debug_safe(f"视频链接列: {link_col}")

            # 确保播放量/点赞量列存在
            play_col = None; like_col = None
            for col in df.columns:
                if '播放量' in str(col) or 'play_count' in str(col).lower(): play_col = col
                if '点赞量' in str(col) or 'like_count' in str(col).lower() or '点赞' in str(col): like_col = col
            if not play_col:
                play_col = '播放量'; df[play_col] = None
            if not like_col:
                like_col = '点赞量'; df[like_col] = None

            # 收集需要获取的链接
            tasks = []
            for idx, row in df.iterrows():
                link = str(row.get(link_col, '')).strip()
                if not link or link == 'nan': continue
                # 跳过已有数据的
                existing_play = row.get(play_col)
                if pd.notna(existing_play) and existing_play not in ('', 0, '0'):
                    continue
                tasks.append((idx, link))

            self._debug_safe(f"需获取: {len(tasks)} 个视频 (跳过已有数据的)")
            if not tasks:
                self._debug_safe("所有视频已有数据，无需获取")
                return

            # 5并发获取
            MAX_RETRIES = 3
            success = 0; fail = 0

            def _get_one(idx, link):
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        th = _TikHubClient()
                        stats = th.fetch_video_stats(link)
                        if stats and stats.get("play_count", 0) > 0:
                            return idx, stats
                        if attempt < MAX_RETRIES:
                            time.sleep(2)
                    except Exception as e:
                        if attempt < MAX_RETRIES:
                            time.sleep(2)
                return idx, None

            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {pool.submit(_get_one, idx, link): (idx, link) for idx, link in tasks}
                for fut in as_completed(futures):
                    idx, stats = fut.result()
                    if stats:
                        df.at[idx, play_col] = stats["play_count"]
                        df.at[idx, like_col] = stats["digg_count"]
                        success += 1
                    else:
                        fail += 1
                    if (success + fail) % 10 == 0:
                        self._debug_safe(f"  进度: {success+fail}/{len(tasks)} (成功{success})")

            # 保存Excel
            df.to_excel(excel_path, index=False)
            self._debug_safe(f"统计数据获取完成: 成功 {success}, 失败 {fail}")
            self._debug_safe(f"已保存到: {excel_path}")

        except Exception as e:
            self._debug_safe(f"获取统计数据异常: {e}")

    def _fetch_completion_rate(self):
        """步骤2: 匹配设备，获取完播率（不含推流码，推流码是独立功能）"""
        fp = self.__ui.lineEdit_analytics_excel.text().strip()
        if not fp or not os.path.isfile(fp):
            self._debug("请先选择Excel文件")
            return
        if not self.device_list:
            self._debug("没有设备，请先刷新设备列表")
            return
        online = {did: info for did, info in self.device_list.items()
                  if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备")
            return
        self._debug("开始获取完播率...")
        threading.Thread(target=self._completion_rate_thread, args=(fp, online), daemon=True).start()

    def _completion_rate_thread(self, excel_path, online_devices):
        """完播率获取线程"""
        try:
            df = pd.read_excel(excel_path)

            # 查找列
            link_col = None; rate_col = None; account_col = None
            for col in df.columns:
                c = str(col)
                if '视频链接' in c or 'video_link' in c.lower() or '链接' in c: link_col = col
                if '完播率' in c or 'completion' in c.lower(): rate_col = col
                if '账号' in c or 'account' in c.lower() or '用户' in c: account_col = col
            if not link_col:
                self._debug_safe("未找到'视频链接'列"); return
            if not rate_col:
                rate_col = '完播率'; df[rate_col] = None

            # 按设备名排序
            sorted_devices = sorted(online_devices.items(), key=lambda x: x[1].get('name', ''))

            # 构建设备名到deviceid的映射
            dev_map = {}
            for did, info in sorted_devices:
                name = info.get('name', '').strip()
                if name: dev_map[name] = did

            # 按行遍历Excel，匹配设备
            # 假设账号列的值对应设备名
            tasks = []  # [(excel_idx, video_link, deviceid, device_name)]
            for idx, row in df.iterrows():
                link = str(row.get(link_col, '')).strip()
                if not link or link == 'nan': continue

                # 已有完播率的跳过
                existing_rate = row.get(rate_col)
                if pd.notna(existing_rate) and existing_rate not in ('', 0):
                    continue

                # 匹配设备 - 用账号列匹配设备名
                matched_did = None; matched_name = None
                if account_col:
                    acc = str(row.get(account_col, '')).strip()
                    if acc in dev_map:
                        matched_did = dev_map[acc]; matched_name = acc

                # 如果没匹配到，按顺序分配
                if not matched_did and sorted_devices:
                    dev_idx = len(tasks) % len(sorted_devices)
                    matched_did = sorted_devices[dev_idx][0]
                    matched_name = sorted_devices[dev_idx][1].get('name', '')

                if matched_did:
                    tasks.append((idx, link, matched_did, matched_name))

            self._debug_safe(f"待处理: {len(tasks)} 个视频")
            if not tasks:
                self._debug_safe("没有需要处理的视频"); return

            # 逐个设备处理（按设备分组后同一设备串行，不同设备并行）
            from collections import defaultdict
            device_tasks = defaultdict(list)
            for idx, link, did, name in tasks:
                device_tasks[did].append((idx, link, name))

            ic = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
            results_lock = threading.Lock()

            def _process_device(did, dev_tasks):
                """处理一台设备上的所有视频"""
                c = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
                name = dev_tasks[0][2] if dev_tasks else "?"
                self._debug_safe(f"设备 {name}: 开始处理 {len(dev_tasks)} 个视频")

                for task_idx, (excel_idx, link, _) in enumerate(dev_tasks):
                    self._debug_safe(f"  [{name}] {task_idx+1}/{len(dev_tasks)}: 打开视频...")

                    try:
                        # 1. 打开视频链接
                        c.open_url(did, link)
                        time.sleep(4)

                        # 横屏检测
                        c.fix_landscape(did, log=self._debug_safe)

                        # 2. 先点三个点（和推流码一样的流程）
                        _find_click_three_dots(c, did)
                        time.sleep(1.5)

                        # 3. 点击 Analytics 按钮（查图）
                        analytics_icon = _load_icon("icon/analytics.bmp")
                        if analytics_icon:
                            pos = c.find_image(did, analytics_icon, 0.75)
                            if pos:
                                c.tap(did, pos[0], pos[1])
                                self._debug_safe(f"  [{name}] 找到Analytics按钮，已点击")
                            else:
                                self._debug_safe(f"  [{name}] 未找到Analytics按钮，跳过")
                                continue
                        else:
                            self._debug_safe(f"  [{name}] 缺少 icon/analytics.bmp")
                            continue

                        time.sleep(2)

                        # 3. 往下滑到中间
                        c.swipe_vertical(did, 600, 300, x=200)
                        time.sleep(1.5)

                        # 4. 全屏OCR查找 "Traffic sources" 定位白色球体，失败则全屏识图
                        def _ocr_find_traffic_y2(_c, _did, _name, _log):
                            raw = _c.ocr(_did)
                            if not raw:
                                _log(f"  [{_name}] OCR返回空")
                                return None
                            items = raw
                            if isinstance(raw, dict):
                                for k in ("texts", "result", "items"):
                                    v = raw.get(k)
                                    if isinstance(v, list): items = v; break
                                    if isinstance(v, dict):
                                        for k2 in ("texts", "result", "items"):
                                            v2 = v.get(k2)
                                            if isinstance(v2, list): items = v2; break
                            if not isinstance(items, list):
                                _log(f"  [{_name}] OCR结构未知: {type(raw)}")
                                return None
                            all_texts = []
                            found_y = None
                            for it in items:
                                if not isinstance(it, dict): continue
                                t = it.get("text","")
                                all_texts.append(t)
                                if "traffic" in t.lower() or "sources" in t.lower():
                                    y = it.get("y") or it.get("top") or it.get("cy")
                                    rect = it.get("rect") or it.get("box")
                                    if y is None and isinstance(rect,(list,tuple)) and len(rect)>=2:
                                        y = rect[1]
                                    if y and int(y) > 0:
                                        found_y = int(y)
                                        _log(f"  [{_name}] OCR找到'{t}' y={y}")
                                        break
                            _log(f"  [{_name}] OCR全屏文字: {all_texts}")
                            return found_y

                        ball_pos = None
                        _scroll_offsets2 = [0, -100, 100]
                        for _soff2 in _scroll_offsets2:
                            if _soff2 != 0:
                                c.swipe_vertical(did, 300 + _soff2, 300, x=200)
                                time.sleep(1)
                            for _ in range(2):
                                _ty2 = _ocr_find_traffic_y2(c, did, name, self._debug_safe)
                                if _ty2:
                                    ball_pos = (35, _ty2 - 90)
                                    self._debug_safe(f"  [{name}] 球体定位 {ball_pos}")
                                    break
                                time.sleep(1)
                            if ball_pos: break

                        if not ball_pos:
                            self._debug_safe(f"  [{name}] OCR未找到Traffic sources，尝试全屏识图")
                            _ball_icon = _load_icon("icon/white_ball.bmp")
                            if _ball_icon:
                                for _sim in (0.65, 0.55, 0.45):
                                    for _ in range(2):
                                        _bp2 = c.find_image(did, _ball_icon, _sim)
                                        if _bp2 and 150 < _bp2[1] < 800 and 10 < _bp2[0] < 400:
                                            ball_pos = _bp2; break
                                        elif _bp2:
                                            self._debug_safe(f"  [{name}] 识图坐标不合理 sim={_sim} {_bp2}，忽略")
                                        time.sleep(1)
                                    if ball_pos:
                                        self._debug_safe(f"  [{name}] 识图找到球体 sim={_sim} {ball_pos}")
                                        break

                        if not ball_pos:
                            self._debug_safe(f"  [{name}] 未找到白色球体，跳过")
                            continue

                        self._debug_safe(f"  [{name}] 找到球体 ({ball_pos[0]},{ball_pos[1]})")

                        # 5. 长按住球体，步进拖到 x=355，保持按住
                        c.drag_to(did, ball_pos[0], ball_pos[1], 355, ball_pos[1])
                        time.sleep(1.5)  # 等气泡出现，此时仍按住

                        def _grab_rate2(_c, _did, _by, _name, _log):
                            try:
                                import base64 as _b64
                                from io import BytesIO
                                from PIL import Image as _PIL, ImageEnhance as _IE
                                ss = _c._post("/pic/screenshot",
                                              {"id": _did, "jpg": True})
                                if not ss or ss.get("status") != 200:
                                    _log(f"  [{_name}] 截图失败: {ss}")
                                    return None
                                _d = ss.get("data", {})
                                img_b64 = _d.get("img") or _d.get("screenshot")
                                if not img_b64:
                                    _log(f"  [{_name}] 截图数据空, keys={list(_d.keys())}")
                                    return None
                                full_img = _PIL.open(BytesIO(_b64.b64decode(img_b64))).convert("RGB")
                                _log(f"  [{_name}] 截图尺寸: {full_img.size}")
                                crop = full_img.crop((0, max(0, _by-150), 330, min(full_img.height, _by+50)))
                                w, h = crop.size
                                crop = crop.resize((w*3, h*3), _PIL.LANCZOS)
                                crop = crop.convert("L")
                                crop = _IE.Contrast(crop).enhance(3.0)
                                crop = _IE.Sharpness(crop).enhance(2.0)
                                try:
                                    import pytesseract
                                    import os as _os
                                    for _tpath in [
                                        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                                        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                                    ]:
                                        if _os.path.exists(_tpath):
                                            pytesseract.pytesseract.tesseract_cmd = _tpath
                                            break
                                    text = pytesseract.image_to_string(
                                        crop, config="--psm 6 -c tessedit_char_whitelist=0123456789.%")
                                    _log(f"  [{_name}] 截图OCR原文: {text.strip()!r}")
                                    for _m in re.finditer(r'(\d*\.\d+)\s*%?', text):
                                        val = float(_m.group(1))
                                        if not (abs(val - 50) < 0.5 or abs(val - 100) < 0.5):
                                            return val
                                except ImportError:
                                    _log(f"  [{_name}] pytesseract未安装")
                                except Exception as _te:
                                    _log(f"  [{_name}] pytesseract异常: {_te}")
                            except Exception as _e:
                                _log(f"  [{_name}] 截图处理异常: {_e}")
                            return None

                        # 按住时截图读数，读完再松手
                        completion_rate = _grab_rate2(c, did, ball_pos[1], name, self._debug_safe)
                        c.mouse_release(did, 355, ball_pos[1])

                        # 兜底：松手后设备OCR，过滤50/100
                        if completion_rate is None:
                            time.sleep(1)
                            for _rect2 in [[0, ball_pos[1]-150, 330, 100], [0, ball_pos[1]-150, 330, 200]]:
                                _raw2 = c.ocr(did, rect=_rect2)
                                if not _raw2: continue
                                _items2 = _raw2 if isinstance(_raw2,list) else _raw2.get("texts",_raw2.get("result",[]))
                                _texts2 = [i.get("text","") if isinstance(i,dict) else str(i) for i in (_items2 if isinstance(_items2,list) else [])]
                                self._debug_safe(f"  [{name}] 设备OCR: {_texts2}")
                                _full2 = " ".join(_texts2)
                                for _m2 in re.finditer(r'(\d*\.\d+)\s*%?', _full2):
                                    _v2 = float(_m2.group(1))
                                    if not (abs(_v2 - 50) < 0.5 or abs(_v2 - 100) < 0.5):
                                        completion_rate = _v2; break
                                if completion_rate is not None: break

                        # 7. 写入完播率
                        with results_lock:
                            if completion_rate is not None:
                                df.at[excel_idx, rate_col] = completion_rate

                    except Exception as e:
                        self._debug_safe(f"  [{name}] 视频处理异常: {e}")

                return name, len(dev_tasks)

            # 最多4设备并发
            workers = min(4, len(device_tasks))
            self._debug_safe(f"启动 {workers} 设备并发处理...")

            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_process_device, did, dtasks): did
                           for did, dtasks in device_tasks.items()}
                for fut in as_completed(futures):
                    try:
                        name, count = fut.result()
                        self._debug_safe(f"设备 {name} 全部完成 ({count}个视频)")
                    except Exception as e:
                        self._debug_safe(f"设备处理异常: {e}")

            # 保存Excel
            df.to_excel(excel_path, index=False)
            self._debug_safe(f"全部完成! 结果已保存到: {excel_path}")

            # 弹窗显示结果
            summary_lines = []
            summary_lines.append("═══ 完播率分析结果 ═══\n")
            rate_filled = df[rate_col].notna().sum() if rate_col in df.columns else 0
            summary_lines.append(f"总视频数: {len(df)}")
            summary_lines.append(f"已获取完播率: {rate_filled}")
            summary_text = "\n".join(summary_lines)

            self._signal_msgEvent.emit({
                "fun": "_show_result_dialog",
                "status": 0,
                "title": "完播率分析完成",
                "text": summary_text
            })

        except Exception as e:
            self._debug_safe(f"完播率分析异常: {e}")
            import traceback
            self._debug_safe(traceback.format_exc())

    # ═══════════════════════════ 一键上传图片 ═══════════════════════════

    def _select_upload_folder(self):
        """选择图片文件夹"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if folder:
            self.__ui.lineEdit_upload_folder.setText(folder)
            self._preview_upload_distribution(folder)

    def _select_upload_video_folder(self):
        """选择视频文件夹"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "选择视频文件夹")
        if folder:
            self.__ui.lineEdit_upload_video_folder.setText(folder)

    def _preview_upload_distribution(self, folder):
        """预览文件分配"""
        import glob
        files = []
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.webp', '*.JPG', '*.PNG'):
            files.extend(glob.glob(os.path.join(folder, ext)))
        if not files:
            self._debug(f"文件夹 {folder} 中没有找到图片文件")
            return

        # 按开头数字分组
        groups = {}
        for fp in files:
            fname = os.path.basename(fp)
            # 提取开头数字
            num = ''
            for ch in fname:
                if ch.isdigit():
                    num += ch
                else:
                    break
            if num:
                groups.setdefault(int(num), []).append(fname)

        self._debug(f"找到 {len(files)} 张图片，分为 {len(groups)} 组:")
        for num in sorted(groups.keys()):
            self._debug(f"  编号{num}: {len(groups[num])} 张图片")

    # ═══════════════════════════ 切号 ═══════════════════════════

    def _switch_account(self, selected_only=False):
        """切号入口"""
        if not self.device_list:
            self._debug("没有在线设备")
            return
        online = {did: info for did, info in self.device_list.items() if info.get('state', 0) != 0}
        if not online:
            self._debug("没有在线设备")
            return

        if selected_only:
            did = self._get_selected_deviceid()
            if not did:
                return
            if did not in online:
                self._debug("所选设备不在线")
                return
            devs = [(did, online[did])]
        else:
            devs = list(online.items())

        n = len(devs)
        label = "选中" if selected_only else "所有在线"
        self._debug(f"准备对 {label} {n} 台设备切号...")
        threading.Thread(target=self._switch_account_thread, args=(devs,), daemon=True).start()

    def _switch_account_thread(self, devs):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        total = len(devs)
        success = 0
        lock = threading.Lock()

        def do_one(item):
            did, info = item
            name = info.get("custom_name","") or info.get("name","") or did
            self._debug_safe(f"[{name}] 开始切号...")
            try:
                ok = self._switch_single(did, name)
                return name, ok
            except Exception as e:
                self._debug_safe(f"[{name}] 切号异常: {e}")
                return name, False

        with ThreadPoolExecutor(max_workers=min(4, total)) as ex:
            futures = {ex.submit(do_one, d): d for d in devs}
            for f in as_completed(futures):
                name, ok = f.result()
                with lock:
                    if ok: success += 1
                self._debug_safe(f"[{name}] {'切号成功' if ok else '切号失败'}")

        self._debug_safe(f"切号完成: 成功 {success}/{total}")

    def _switch_single(self, did, name):
        """单台设备切号流程（Pro接口版）"""
        c = _IMouseXPClient(self.__server, self.__port)

        def log(msg):
            self._debug_safe(f"  [{name}] {msg}")

        def tap(x, y, delay=1.0):
            c.tap(did, x, y)
            time.sleep(delay)

        def ocr_find(keywords):
            """全屏OCR查找包含任意关键词的条目，返回(x,y)或None"""
            raw = c.ocr(did)
            if not raw: return None
            items = raw if isinstance(raw, list) else raw.get("texts", raw.get("result", []))
            if not isinstance(items, list): return None
            for it in items:
                if not isinstance(it, dict): continue
                t = it.get("text","").lower()
                if any(k.lower() in t for k in keywords):
                    x = it.get("x") or it.get("cx", 0)
                    y = it.get("y") or it.get("cy", 0)
                    if x and y:
                        return (int(x), int(y))
            return None

        # Step 1: 回主屏幕
        log("Step1: 回主屏幕")
        c.press_home(did); time.sleep(2)

        # Step 2: 打开 TikTok
        log("Step2: 打开 TikTok")
        c.open_url(did, "tiktok://")
        time.sleep(6)

        # Step 3: 点个人页（右下角）
        log("Step3: 进入个人页")
        tap(390, 850, delay=3)

        # Step 4: 点右上角三条杠 ≡，先识图再固定坐标
        log("Step4: 点击菜单 ≡")
        _three_icon = _load_icon("icon/three_dots_icon.bmp") or _load_icon("icon/three.bmp")
        pos = None
        if _three_icon:
            pos = c.find_image(did, _three_icon, similarity=0.7)
        if pos:
            tap(pos[0], pos[1], delay=3)
            log(f"识图找到≡ ({pos[0]},{pos[1]})")
        else:
            tap(390, 73, delay=3)
            log("固定坐标点击≡ (390,73)")

        # Step 5: 点 Settings and privacy（OCR找privacy，失败用固定坐标）
        log("Step5: 点击 Settings and privacy")
        pos = ocr_find(["privacy", "settings"])
        if pos:
            tap(pos[0], pos[1], delay=3)
            log(f"OCR找到 Settings ({pos[0]},{pos[1]})")
        else:
            tap(200, 460, delay=3)
            log("固定坐标点击 Settings (200,460)")

        # Step 6: 向下滚动5次找到 Switch account
        log("Step6: 向下滚动")
        for _ in range(5):
            c.swipe(did, 200, 800, 200, 200)
            time.sleep(0.4)
        time.sleep(1)

        # Step 7: 点 Switch account（OCR找，失败用固定坐标）
        log("Step7: 点击 Switch account")
        raw = c.ocr(did)
        items = []
        if raw:
            items = raw if isinstance(raw, list) else raw.get("texts", raw.get("result", []))
        candidates = []
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict): continue
                t = it.get("text","").lower()
                if "switch" in t and "account" in t:
                    y = it.get("y") or it.get("cy", 0)
                    x = it.get("x") or it.get("cx", 207)
                    if y: candidates.append((int(x), int(y)))
        if candidates:
            # 取y最大的（列表最底部）
            tx, ty = max(candidates, key=lambda p: p[1])
            tap(tx, ty, delay=3)
            log(f"OCR找到 Switch account ({tx},{ty})")
        else:
            tap(175, 810, delay=3)
            log("固定坐标点击 Switch account (175,810)")

        # Step 8: 识别账号列表，点击非当前账号
        log("Step8: 选择另一个账号")
        time.sleep(2)

        switched = False
        for attempt in range(3):
            # 截图分析：找右侧✓（红色像素聚类）
            ck_y = None
            try:
                import base64 as _b64
                from io import BytesIO
                from PIL import Image as _PILImage
                r = c._post("/pic/screenshot", {"id": did, "jpg": True}, quiet=True)
                img_data = None
                if r and r.get("status") == 0:
                    img_data = r.get("data", {}).get("img") or r.get("data", {}).get("screenshot")
                if img_data:
                    img_bytes = _b64.b64decode(img_data)
                    img = _PILImage.open(BytesIO(img_bytes)).convert("RGB")
                    w, h = img.size
                    red_rows = {}
                    for py in range(int(h*0.05), int(h*0.95)):
                        cnt = sum(1 for px in range(int(w*0.68), w-2, 2)
                                  if img.getpixel((px,py))[0]>160
                                  and img.getpixel((px,py))[0] > img.getpixel((px,py))[1]+50
                                  and img.getpixel((px,py))[0] > img.getpixel((px,py))[2]+30)
                        if cnt > 0: red_rows[py] = cnt
                    if red_rows:
                        ck_y = max(red_rows, key=red_rows.get)
                        log(f"截图找到✓ y={ck_y}")
            except Exception as e:
                log(f"截图分析异常: {e}")

            # 扫描左侧头像行
            row_ys = []
            try:
                r2 = c._post("/pic/screenshot", {"id": did, "jpg": True}, quiet=True)
                img_data2 = None
                if r2 and r2.get("status") == 0:
                    img_data2 = r2.get("data", {}).get("img") or r2.get("data", {}).get("screenshot")
                if img_data2:
                    import base64 as _b64
                    from io import BytesIO
                    from PIL import Image as _PILImage
                    img2 = _PILImage.open(BytesIO(_b64.b64decode(img_data2))).convert("RGB")
                    w2, h2 = img2.size
                    x0 = max(1, int(w2*0.03)); x1 = min(w2-1, int(w2*0.22))
                    y_min = max(0, ck_y-200) if ck_y else int(h2*0.03)
                    y_max = min(h2, ck_y+200) if ck_y else int(h2*0.97)
                    seg_start = seg_end = None
                    rows_data = []
                    for py in range(y_min, y_max, 2):
                        cnt = sum(1 for px in range(x0, x1, 3)
                                  if not all(v > 215 for v in img2.getpixel((px, py))))
                        rows_data.append((py, cnt))
                    for py, cnt in rows_data:
                        if cnt >= 2:
                            if seg_start is None: seg_start = py
                            seg_end = py
                        else:
                            if seg_start is not None:
                                if seg_end - seg_start > 25:
                                    row_ys.append((seg_start + seg_end) // 2)
                                seg_start = seg_end = None
                    if seg_start and seg_end and seg_end - seg_start > 25:
                        row_ys.append((seg_start + seg_end) // 2)
                    log(f"头像扫描找到账号行: {row_ys}")
            except Exception as e:
                log(f"头像扫描异常: {e}")

            if ck_y and row_ys:
                others = [y for y in row_ys if 40 < abs(y - ck_y) < 250]
                if others:
                    target_y = min(others, key=lambda y: abs(y - ck_y))
                    tap(200, target_y, delay=2)
                    log(f"✓在y={ck_y}，点击另一账号 y={target_y}")
                    switched = True
                    break
            elif not ck_y and len(row_ys) >= 2:
                # OCR找✓符号
                pos_ck = ocr_find(["✓","√","✔","☑"])
                if pos_ck:
                    ck_y2 = pos_ck[1]
                    others = [y for y in row_ys if abs(y - ck_y2) > 40]
                    if others:
                        target_y = max(others, key=lambda y: abs(y - ck_y2))
                        tap(200, target_y, delay=2)
                        log(f"OCR✓ y={ck_y2}，点击 y={target_y}")
                        switched = True
                        break

            log(f"未确定目标账号，重试({attempt+1}/3)...")
            time.sleep(2)

        if not switched:
            log("无法识别账号列表，切号失败")
            return False

        time.sleep(3)
        log("切号完成")
        return True

    def _batch_upload_photos(self):
        """一键上传图片到图文分组设备"""
        folder = self.__ui.lineEdit_upload_folder.text().strip()
        if not folder or not os.path.isdir(folder):
            self._debug("请先选择图片文件夹"); return
        self._batch_upload_media(folder, 'tuwen',
            ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.webp'), '图片')

    def _batch_upload_videos(self):
        """一键上传视频到视频分组设备"""
        folder = self.__ui.lineEdit_upload_video_folder.text().strip()
        if not folder or not os.path.isdir(folder):
            self._debug("请先选择视频文件夹"); return
        self._batch_upload_media(folder, 'shipin',
            ('*.mp4', '*.mov', '*.avi', '*.m4v', '*.mkv', '*.wmv'), '视频')

    def _batch_upload_media(self, folder, group_keyword, file_exts, file_desc):
        """通用批量上传：按分组过滤设备，按分组内顺序分配序号"""
        if not self.device_list:
            self._debug("没有设备，请先刷新设备列表"); return

        # 查询分组列表，找到含group_keyword的分组gid
        ic = _IMouseXPClient("127.0.0.1", IMOUSE_XP_PORT)
        gr = ic._post("/device/group/get", {})
        target_gids = set()
        if gr and gr.get("status") in (0, 200):
            gd = gr.get("data", {})
            # 兼容XP: data可能是{list:[...]}
            if isinstance(gd, dict) and "list" in gd and isinstance(gd["list"], list):
                for gi in gd["list"]:
                    if isinstance(gi, dict):
                        gname = gi.get("name", "")
                        gid = str(gi.get("id", ""))
                        self._debug(f"  分组: gid={gid} name={gname}")
                        if group_keyword in gname:
                            target_gids.add(gid)
            elif isinstance(gd, dict):
                for gid, gi in gd.items():
                    gname = gi.get("name", "") if isinstance(gi, dict) else str(gi)
                    self._debug(f"  分组: gid={gid} name={gname}")
                    if group_keyword in gname:
                        target_gids.add(str(gid))
        else:
            self._debug(f"  获取分组列表失败: {gr}")
        if not target_gids:
            self._debug(f"未找到分组名包含'{group_keyword}'的分组，请检查分组名称"); return
        self._debug(f"  目标分组gid: {target_gids}")

        # 打印每个在线设备的gid供对照
        online_count = 0
        for did, info in self.device_list.items():
            if info.get('state', 0) != 0:
                online_count += 1
                dev_gid = str(info.get('gid', ''))
                matched = "<<匹配>>" if dev_gid in target_gids else ""
                if online_count <= 5 or matched:
                    self._debug(f"  设备 {info.get('name','?')} gid={dev_gid} {matched}")
        if online_count > 5:
            self._debug(f"  ... 共 {online_count} 台在线设备")

        # 按自定义名（name）字母排序，与UI显示顺序一致
        group_devices = sorted(
            [(did, info) for did, info in self.device_list.items()
             if info.get('state', 0) != 0 and str(info.get('gid', '')) in target_gids],
            key=lambda x: x[1].get('name', '').lower()
        )
        if not group_devices:
            self._debug(f"'{group_keyword}'分组中没有在线设备"); return

        self._debug(f"'{group_keyword}'分组在线设备 {len(group_devices)} 台:")
        for i, (did, info) in enumerate(group_devices):
            self._debug(f"  第{i+1}台: {info.get('name', did)}")

        # 收集文件（去重，只取第一个匹配的扩展名，避免同名不同格式导致翻倍）
        import glob
        seen_normcase = set()   # 去重：完全相同的文件路径（不区分大小写）
        seen_stem = set()       # 去重：相同文件名前缀（不同格式如 1.jpg/1.png 只取一个）
        files = []
        for ext in file_exts:
            count_ext = 0
            for fp in glob.glob(os.path.join(folder, ext)):
                key = os.path.normcase(fp)
                if key in seen_normcase:
                    continue
                seen_normcase.add(key)
                # 用文件名（不含扩展名）去重，避免同一个编号多种格式
                stem = os.path.splitext(os.path.basename(fp).lower())[0]
                if stem in seen_stem:
                    continue
                seen_stem.add(stem)
                files.append(fp)
                count_ext += 1
            if count_ext > 0:
                self._debug(f"  {ext}: {count_ext} 个文件")
        if not files:
            self._debug(f"文件夹中没有{file_desc}文件"); return

        # 按开头数字分组
        groups = {}
        skipped = []
        for fp in files:
            fname = os.path.basename(fp)
            num = ''
            for ch in fname:
                if ch.isdigit(): num += ch
                else: break
            if num:
                groups.setdefault(int(num), []).append(fp)
            else:
                skipped.append(fname)
        if skipped:
            self._debug(f"跳过 {len(skipped)} 个无编号文件")

        # 序号 → 分组内第n台设备
        upload_tasks = []
        for num in sorted(groups.keys()):
            idx = num - 1
            if idx < 0 or idx >= len(group_devices):
                self._debug(f"  编号{num}: '{group_keyword}'分组只有{len(group_devices)}台，跳过"); continue
            did, info = group_devices[idx]
            name = info.get('name', did)
            sorted_files = sorted(groups[num], key=lambda f: os.path.basename(f).lower())
            upload_tasks.append((did, name, sorted_files))
            self._debug(f"  编号{num} → 设备 {name}: {len(sorted_files)} 个{file_desc}")

        if not upload_tasks:
            self._debug("没有可上传的任务"); return

        total_files = sum(len(t[2]) for t in upload_tasks)
        self._debug(f"开始上传: {total_files} 个{file_desc}到 {len(upload_tasks)} 台设备 (3并发)...")
        threading.Thread(target=self._batch_upload_thread,
                         args=(upload_tasks, file_desc), daemon=True).start()

    def _batch_upload_thread(self, upload_tasks, file_desc='文件'):
        """批量上传线程 - 3设备并发"""
        MAX_RETRIES = 3
        success = 0
        fail = 0

        def _upload_one_device(did, name, file_list):
            """分批上传（每批5个），检查 data.code 确认真正成功"""
            total = len(file_list)
            BATCH_SIZE = 5  # 官方SDK也用5个一批
            self._debug_safe(f"  [{name}] 开始上传 {total} 个{file_desc} (分{(total+BATCH_SIZE-1)//BATCH_SIZE}批)...")

            batches = [file_list[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
            ok_count = 0
            for bi, batch in enumerate(batches):
                success = False
                for retry in range(1, MAX_RETRIES + 1):
                    try:
                        ret = self.api.shortcut_up_photo(
                            deviceid=did,
                            files=batch,
                            name='Recents',
                            devlist=[],
                            outtime=60000  # 每批60秒
                        )
                        status_ok = ret and ret.get('status', -1) in (0, 200)
                        # 检查 data.code (XP: 0=成功)
                        data = (ret or {}).get('data', {}) or {}
                        code_ok = data.get('code', -1) == 0 if status_ok else False
                        if status_ok and code_ok:
                            ok_count += len(batch)
                            self._debug_safe(f"  [{name}] 第{bi+1}/{len(batches)}批: {len(batch)}个 OK")
                            success = True
                            break
                        else:
                            code = data.get('code', '?')
                            msg = data.get('message') or (ret.get('message','') if ret else '无响应')
                            self._debug_safe(f"  [{name}] 第{bi+1}批第{retry}次失败: code={code} msg={msg}")
                            if retry < MAX_RETRIES: time.sleep(3)
                    except Exception as e:
                        self._debug_safe(f"  [{name}] 第{bi+1}批第{retry}次异常: {e}")
                        if retry < MAX_RETRIES: time.sleep(3)
                if not success:
                    self._debug_safe(f"  [{name}] 第{bi+1}批彻底失败，已放弃")
                    return False
                time.sleep(1)  # 批间等待

            self._debug_safe(f"  [OK] {name}: {ok_count}/{total} 个{file_desc}上传成功")
            return ok_count == total

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {}
            for did, name, file_list in upload_tasks:
                fut = pool.submit(_upload_one_device, did, name, file_list)
                futures[fut] = name

            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    if fut.result():
                        success += 1
                    else:
                        fail += 1
                except Exception as e:
                    self._debug_safe(f"  [ERROR] {name}: {e}")
                    fail += 1

        self._debug_safe(f"{file_desc}上传完成: 成功 {success}/{success+fail} 台设备")

    def _transfer_media_files(self, deviceid):
        """
        遍历读取 D:\\iMousePro\\Shortcut\\Media 下的子文件夹的内容，按设备名称分配到对应设备。
        例如：文件夹 "1" 的内容上传到设备名为 "1" 的手机。
        """
        dev_info = self.device_list.get(deviceid, {})
        dev_name = dev_info.get('name', '')
        if not dev_name:
            self._debug(f"错误：无法获取设备 {deviceid} 的名称，跳过上传")
            return

        base_dir = Path(r'D:\iMousePro\Shortcut\Media')
        device_dir = base_dir / dev_name

        if not device_dir.exists() or not device_dir.is_dir():
            self._debug(f"错误：对应目录不存在或非目录: {device_dir}")
            return

        files = [str(f) for f in device_dir.iterdir() if f.is_file()]
        if not files:
            self._debug(f"{dev_name} 下没有文件可供上传")
            return

        self._debug(f"准备上传 {len(files)} 个文件从 {device_dir} 到设备 {dev_name}")
        try:
            ret = self.api.shortcut_up_photo(
                deviceid=deviceid,
                files=files,
                name='Recents',
                devlist=[],
                outtime=60000
            )
            if ret and ret.get('status', -1) != 0:
                self._debug(f"上传失败，原因: {ret.get('message', '未知错误')}")
            else:
                self._debug(f"上传请求已提交: 共 {len(files)} 个文件")
        except Exception as e:
            self._debug(f"上传过程中发生异常: {e}")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
