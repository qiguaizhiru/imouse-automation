# -*- coding: utf-8 -*-
# 本地识图模块 - OpenCV 模板匹配
#
# 比 iMouse 原生识图更稳：截图后在本地做模板匹配。
# 注意坐标系：截图图像是 imgw×imgh，但点击用逻辑坐标 width×height，
# 匹配到的坐标需要按比例换算回逻辑坐标。

import base64
import logging

logger = logging.getLogger("automation.vision")

_CV_AVAILABLE = None


def cv_available():
    global _CV_AVAILABLE
    if _CV_AVAILABLE is None:
        try:
            import cv2  # noqa
            import numpy  # noqa
            _CV_AVAILABLE = True
        except ImportError:
            _CV_AVAILABLE = False
            logger.warning("未安装 opencv-python，本地识图不可用，将仅用 iMouse 原生识图")
    return _CV_AVAILABLE


def cv_find_image(screen_b64, tpl_b64, similarity=0.7, rect=None):
    """在截图上做本地模板匹配

    返回 (center_x, center_y, confidence) — 坐标是【截图像素坐标】，
    调用方需自行按需换算到逻辑坐标。找不到返回 None。
    """
    if not cv_available():
        return None
    try:
        import cv2
        import numpy as np

        screen_bytes = base64.b64decode(screen_b64) if isinstance(screen_b64, str) else screen_b64
        tpl_bytes = base64.b64decode(tpl_b64) if isinstance(tpl_b64, str) else tpl_b64

        screen_img = cv2.imdecode(np.frombuffer(screen_bytes, np.uint8), cv2.IMREAD_COLOR)
        tpl_img = cv2.imdecode(np.frombuffer(tpl_bytes, np.uint8), cv2.IMREAD_COLOR)
        if screen_img is None or tpl_img is None:
            return None

        h_scr, w_scr = screen_img.shape[:2]
        h_tpl, w_tpl = tpl_img.shape[:2]

        # 裁剪搜索区域
        ox, oy = 0, 0
        if rect:
            try:
                if len(rect) == 4 and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in rect):
                    xs = [p[0] for p in rect]
                    ys = [p[1] for p in rect]
                    lx, ty, rx, by = min(xs), min(ys), max(xs), max(ys)
                elif len(rect) == 4:
                    a, b, c, d = rect
                    if c > a and d > b:
                        lx, ty, rx, by = a, b, c, d
                    else:
                        lx, ty, rx, by = a, b, a + c, b + d
                else:
                    lx, ty, rx, by = 0, 0, w_scr, h_scr
                lx = max(0, min(lx, w_scr)); rx = max(0, min(rx, w_scr))
                ty = max(0, min(ty, h_scr)); by = max(0, min(by, h_scr))
                if rx - lx >= w_tpl and by - ty >= h_tpl:
                    screen_img = screen_img[ty:by, lx:rx]
                    ox, oy = lx, ty
            except Exception:
                pass

        result = cv2.matchTemplate(screen_img, tpl_img, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < similarity:
            return None
        cx = max_loc[0] + w_tpl // 2 + ox
        cy = max_loc[1] + h_tpl // 2 + oy
        return (int(cx), int(cy), float(max_val))
    except Exception as e:
        logger.debug(f"本地识图异常: {e}")
        return None


def get_image_size(img_b64):
    """解码图片，返回 (width, height)，失败返回 None"""
    if not cv_available():
        return None
    try:
        import cv2
        import numpy as np
        img_bytes = base64.b64decode(img_b64) if isinstance(img_b64, str) else img_b64
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None
        h, w = img.shape[:2]
        return (w, h)
    except Exception:
        return None
