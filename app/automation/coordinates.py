# -*- coding: utf-8 -*-
# 分机型坐标系统
#
# 不同机型屏幕分辨率不同，固定坐标会偏。这里维护两套坐标:
#   normal: 普通机型，基准 414×896 (iPhone 11/XR 等)
#   se:     SE 机型，  基准 375×667 (iPhone SE 2/3、8 等小屏)
#
# SE 坐标默认由 normal 按分辨率比例自动换算；可在 coordinates.json 里手动覆盖精调。
# 所有点位仍有「识图」作为第二层保险（见 publish/nurture 任务）。

import json
import logging
import os

logger = logging.getLogger("automation.coordinates")

from .paths import data_path

CONFIG_FILE = data_path("coordinates.json")

# 屏幕基准分辨率
SCREEN = {
    "normal": (414, 896),
    "se": (375, 667),
}

# ── 普通机型坐标 (414×896) ──
# 点位格式: (x, y) 中心点；swipe 用 dict {sx, sy, ex, ey}
NORMAL_COORDS = {
    # ── 养号验证坐标（来自实战程序，iPhone 11 414×896；SE 按比例自动换算）──
    "nurture_home":     (41, 830),   # 底部 Home（识图 home.png 优先，此为兜底）
    "nurture_heart":    (386, 469),  # 视频右侧爱心（识图 heart.png 优先，此为兜底）
    "nurture_swipe_up": (200, 550),  # 上滑下一个视频的起点
    "nurture_foryou":   (100, 50),   # 右滑到 For You 的起点
    "landscape_fix":    (71, 387),   # 横屏(直播)时点这里切回竖屏
    "live_double":      (200, 500),  # 直播模式双击点赞位置

    # ── 其它点位（发布/完整模式用）──
    "video_center":   (205, 400),   # 屏幕中央
    "like_button":    (386, 469),   # 右侧爱心（同养号，验证坐标）
    "comment_button": (385, 420),   # 右侧评论
    "share_button":   (385, 500),   # 右侧分享
    "follow_button":  (385, 270),   # 头像下方 + 号
    "avatar":         (385, 230),   # 头像（进主页）
    "search":         (365, 35),    # 右上搜索图标
    "search_box":     (207, 38),    # 搜索输入框
    "home_tab":       (41, 830),    # 底部 首页（验证坐标）
    "discover_tab":   (125, 830),   # 底部 发现
    "inbox_tab":      (295, 830),   # 底部 收件箱
    "profile_tab":    (380, 830),   # 底部 个人页
    "back":           (27, 72),     # 左上返回
    # 滑动类
    "swipe_next":     {"sx": 205, "sy": 700, "ex": 205, "ey": 200},   # 上滑下一个
    "swipe_prev":     {"sx": 205, "sy": 250, "ex": 205, "ey": 700},   # 下滑上一个
    "comment_scroll": {"sx": 200, "sy": 600, "ex": 200, "ey": 350},   # 评论区上滑
    "comment_close":  {"sx": 200, "sy": 300, "ex": 200, "ey": 700},   # 评论区下滑关闭
    # 偏移量（发布: 标题框下方多少像素是描述框）
    "title_desc_offset": 50,
    # 抖动幅度（模拟人手）
    "jitter": 12,
}


def _scale_point(pt, rx, ry):
    return (int(round(pt[0] * rx)), int(round(pt[1] * ry)))


def _scale_swipe(sw, rx, ry):
    return {
        "sx": int(round(sw["sx"] * rx)), "sy": int(round(sw["sy"] * ry)),
        "ex": int(round(sw["ex"] * rx)), "ey": int(round(sw["ey"] * ry)),
    }


def _auto_scale(base, from_screen, to_screen):
    """按分辨率比例把一套坐标换算到目标屏幕"""
    rx = to_screen[0] / from_screen[0]
    ry = to_screen[1] / from_screen[1]
    out = {}
    for key, val in base.items():
        if isinstance(val, tuple):
            out[key] = _scale_point(val, rx, ry)
        elif isinstance(val, dict):
            out[key] = _scale_swipe(val, rx, ry)
        elif key == "title_desc_offset":
            out[key] = int(round(val * ry))
        elif key == "jitter":
            out[key] = max(6, int(round(val * rx)))
        else:
            out[key] = val
    return out


def _build_coords():
    """构建两套坐标：normal 用基准，se 自动换算，再叠加 JSON 覆盖"""
    coords = {
        "normal": dict(NORMAL_COORDS),
        "se": _auto_scale(NORMAL_COORDS, SCREEN["normal"], SCREEN["se"]),
    }
    # 叠加用户手动覆盖
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                override = json.load(f)
            for mtype in ("normal", "se"):
                if mtype in override:
                    for key, val in override[mtype].items():
                        # JSON 里 list 转回 tuple
                        if isinstance(val, list):
                            val = tuple(val)
                        coords[mtype][key] = val
            logger.info("已加载坐标覆盖配置")
        except Exception as e:
            logger.warning(f"加载坐标覆盖失败: {e}")
    return coords


_COORDS = _build_coords()


def get_coords(model_type="normal"):
    """获取指定机型的坐标表"""
    return _COORDS.get(model_type, _COORDS["normal"])


def reload_coords():
    """重新加载坐标（修改 JSON 后调用）"""
    global _COORDS
    _COORDS = _build_coords()
    return _COORDS


def detect_model_type(info, group_name=""):
    """根据设备信息判断机型

    优先级:
      1. 组名含 'se'  → se   （用户在 iMouse 分组时的显式标记）
      2. device_name 含 'se' → se   （设备自报型号，如 'iPhone SE 2'）
      3. 屏幕分辨率 ≤ 375×667 → se   （SE 小屏兜底）
      4. 其它 → normal
    """
    # 1. 组名
    if group_name and "se" in group_name.lower():
        return "se"
    # 2. 设备型号名
    dn = str(info.get("device_name", "")).lower()
    if "se" in dn:
        return "se"
    # 3. 分辨率兜底
    try:
        w = int(info.get("width", 0) or 0)
        h = int(info.get("height", 0) or 0)
        if w and h and w <= 375 and h <= 667:
            return "se"
    except (ValueError, TypeError):
        pass
    return "normal"


def export_default_config(path=None):
    """导出当前坐标为 JSON，方便手动精调 SE 坐标"""
    path = path or CONFIG_FILE
    out = {}
    for mtype in ("normal", "se"):
        out[mtype] = {}
        for key, val in _COORDS[mtype].items():
            if isinstance(val, tuple):
                out[mtype][key] = list(val)
            else:
                out[mtype][key] = val
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return path
