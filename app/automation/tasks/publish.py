# -*- coding: utf-8 -*-
# TikTok 发布任务 - 图文/视频发布，方法与原 iMouse Pro 完全一致

import io
import os
import time
import logging

from .base import BaseTask
from ..paths import resource_path

logger = logging.getLogger("automation.publish")

# 媒体文件根目录（与原程序一致）
MEDIA_BASE_DIR = r"D:\iMousePro\Shortcut\Media"

# 支持的视频/图片格式（按优先级；本地文件只用于提取缩略图做识图匹配，cv2 都能读）
VIDEO_EXTS = [".mov", ".mp4", ".m4v", ".avi", ".mkv", ".3gp", ".flv", ".wmv", ".webm"]
IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".bmp", ".webp"]

# icon 目录：只读资源，打包后在程序内部
ICON_DIR = resource_path("icon")


def _find_media_file(device_dir, file_name, exts):
    """在目录下按多种扩展名查找素材文件，返回完整路径或 None。
    兼容 file_name 本身已带扩展名的情况。"""
    # 1) file_name 已带扩展名且文件存在
    root, ext = os.path.splitext(file_name)
    if ext and ext.lower() in exts:
        cand = os.path.join(device_dir, file_name)
        if os.path.exists(cand):
            return cand
    # 2) 依次尝试各扩展名
    for e in exts:
        cand = os.path.join(device_dir, file_name + e)
        if os.path.exists(cand):
            return cand
    return None

DEFAULT_PUBLISH_CONFIG = {
    "media_base_dir": MEDIA_BASE_DIR,
    "icon_dir": ICON_DIR,
    "icon_similarity": 0.7,
    "step_wait": 5,          # 关键步骤间等待（秒）
}


def _icon(cfg, name):
    return os.path.join(cfg.get("icon_dir", ICON_DIR), name)


class PublishTask(BaseTask):
    """单条发布任务（图文 或 视频）

    任务数据通过 config 传入:
        device_name:  设备名（用于定位媒体文件夹）
        file:         素材文件名（不含扩展名）
        type:         'picture' 或 'video'
        url:          音乐URL（图文模式必填）
        title:        标题
        description:  描述/标签
    """

    name = "publish"
    description = "发布作品 - 图文/视频"

    def __init__(self, config=None):
        merged = dict(DEFAULT_PUBLISH_CONFIG)
        if config:
            merged.update(config)
        super().__init__(merged)
        self.result = None

    def run(self, device):
        cfg = self.config
        media_type = str(cfg.get("type", "picture")).strip().lower()
        device_name = cfg.get("device_name") or device.name
        file_name = str(cfg.get("file", "")).strip()

        device_dir = os.path.join(cfg.get("media_base_dir", MEDIA_BASE_DIR), device_name)

        self._log(device, f"准备发布: 类型={media_type}, 素材={file_name}")

        if media_type == "picture":
            template_bytes = self._make_image_template(device, device_dir, file_name)
            if template_bytes is None:
                raise FileNotFoundError(f"找不到图片素材: {file_name}")
            ok = self._publish_image(device, template_bytes)
        elif media_type == "video":
            video_path = _find_media_file(device_dir, file_name, VIDEO_EXTS)
            if not video_path:
                raise FileNotFoundError(
                    f"找不到视频文件: {os.path.join(device_dir, file_name)}"
                    f"（支持 {'/'.join(e[1:] for e in VIDEO_EXTS)}）")
            self._log(device, f"找到视频: {os.path.basename(video_path)}")
            template_bytes = self._extract_video_thumbnail(device, video_path)
            if template_bytes is None:
                raise RuntimeError("无法提取视频缩略图")
            ok = self._publish_video(device, template_bytes)
        else:
            raise ValueError(f"未知的媒体类型: {media_type}")

        self.result = ok
        if ok:
            self._log(device, "发布成功")
        else:
            self._log(device, "发布失败（流程未完成）")
            raise RuntimeError("发布流程未完成")

    # ═══════════════════════════════════════════
    # 图文发布（与 _open_tiktok_app_with_data 一致）
    # ═══════════════════════════════════════════

    def _publish_image(self, device, template_bytes):
        cfg = self.config
        sim = cfg.get("icon_similarity", 0.7)
        wait = cfg.get("step_wait", 5)
        url = cfg.get("url", "")
        title = cfg.get("title", "")
        description = cfg.get("description", "")

        if not url:
            self._log(device, "音乐URL为空，图文模式需要URL，跳过")
            return False

        # 1. 返回主屏幕
        self._log(device, "返回主屏幕...")
        device.send_key(fn_key="HOME")
        self.wait(2)

        # 2. 打开 TikTok
        if not self._find_and_click(device, "tiktok.bmp", sim):
            self._log(device, "未找到 TikTok 图标，使用备选方案")
            self.wait(3)

        # 3. 打开音乐 URL
        self._log(device, f"打开音乐URL: {url}")
        ret = device.open_url(url)
        if ret and ret.get("status", -1) not in (0, 200):
            self._log(device, f"URL打开失败: {ret.get('message', '未知')}")
            return False
        self.wait(10)

        # 4. 点击 Use sound
        if not self._find_and_click(device, "usesound.bmp", sim):
            self._log(device, "未找到 Use sound")
            return False

        # 5. 查找并点击封面图（在相册中）
        self._log(device, "查找封面图...")
        if not self._find_and_click_bytes(device, template_bytes, sim):
            self._log(device, "未找到封面图")
            return False
        self.wait(3)

        # 6. 点击 next 两次
        for i in range(2):
            if not self._find_and_click(device, "next.bmp", sim, required=False):
                self._log(device, f"第{i+1}次 next 未找到（不影响）")
            self.wait(wait)

        # 7. 输入标题 + 描述
        self._input_title_desc(device, title, description, sim)

        # 8. 点击 post
        if not self._find_and_click(device, "post.bmp", sim):
            self._log(device, "未找到 post 按钮")
            return False

        return True

    # ═══════════════════════════════════════════
    # 视频发布（与 _open_tiktok_app_with_video 一致）
    # ═══════════════════════════════════════════

    def _publish_video(self, device, template_bytes):
        cfg = self.config
        sim = cfg.get("icon_similarity", 0.7)
        wait = cfg.get("step_wait", 5)
        description = cfg.get("description", "")

        # 1. 返回主屏幕
        self._log(device, "返回主屏幕...")
        device.send_key(fn_key="HOME")
        self.wait(2)

        # 2. 打开 TikTok
        if not self._find_and_click(device, "tiktok.bmp", sim):
            self._log(device, "未找到 TikTok 图标，使用备选方案")
            self.wait(3)

        # 3. 点击 + 按钮（先白后黑）
        if not self._find_and_click(device, "+white.bmp", sim, required=False):
            if not self._find_and_click(device, "+black.bmp", sim):
                self._log(device, "未找到 + 按钮")
                return False

        # 4. 查找并点击视频缩略图
        self._log(device, "查找视频缩略图...")
        if not self._find_and_click_bytes(device, template_bytes, sim):
            self._log(device, "未找到视频")
            return False
        self.wait(3)

        # 5. 点击 next 两次
        for i in range(2):
            if not self._find_and_click(device, "next.bmp", sim, required=False):
                self._log(device, f"第{i+1}次 next 未找到（不影响）")
            self.wait(wait)

        # 6. 输入描述
        loc = self._find_icon(device, "Add description.bmp", sim)
        if loc:
            cx, cy = loc[0], loc[1]
            device.tap(cx, cy)
            self.wait(1)
            self._input_text(device, description)
        else:
            self._log(device, "未找到 Add description（跳过描述）")

        # 7. 点击 post
        if not self._find_and_click(device, "post.bmp", sim):
            self._log(device, "未找到 post 按钮")
            return False

        return True

    # ═══════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════

    def _input_title_desc(self, device, title, description, sim):
        """图文模式：找到标题框，输入标题，再点下方输入描述"""
        icon_path = _icon(self.config, "Add a catchy title.bmp")
        if not os.path.exists(icon_path):
            self._log(device, "标题图标文件不存在，跳过标题输入")
            return
        loc = device.find_image_file(icon_path, sim)
        if not loc:
            self._log(device, "未找到标题输入框")
            return
        cx, cy = loc[0], loc[1]
        device.tap(cx, cy)
        self.wait(1)
        self._input_text(device, title)
        self.wait(2)
        # 点击标题下方输入描述（偏移量按机型）
        offset = device.coords.get("title_desc_offset", 50)
        device.tap(cx, cy + offset)
        self.wait(1)
        self._input_text(device, description)

    def _input_text(self, device, text):
        if not text:
            return
        self._log(device, f"输入文本: {text[:30]}")
        device.send_text(text)
        self.wait(1)

    def _find_icon(self, device, icon_name, sim):
        path = _icon(self.config, icon_name)
        return device.find_image_file(path, sim)

    def _find_and_click(self, device, icon_name, sim, required=True):
        path = _icon(self.config, icon_name)
        if not os.path.exists(path):
            self._log(device, f"图标不存在: {icon_name}")
            return not required
        loc = device.find_image_file(path, sim)
        if loc:
            cx, cy = loc[0], loc[1]
            self._log(device, f"点击 {icon_name} ({cx}, {cy})")
            device.tap(cx, cy)
            self.wait(3)
            return True
        return False

    def _find_and_click_bytes(self, device, img_bytes, sim):
        loc = device.find_image_bytes(img_bytes, sim)
        if loc:
            cx, cy = loc[0], loc[1]
            self._log(device, f"点击素材 ({cx}, {cy})")
            device.tap(cx, cy)
            self.wait(3)
            return True
        return False

    def _make_image_template(self, device, device_dir, file_name):
        """读取图片素材，居中裁切正方形并缩放到 135×135（与原程序一致）"""
        try:
            from PIL import Image
        except ImportError:
            self._log(device, "缺少 PIL 库")
            return None

        img_path = _find_media_file(device_dir, file_name, IMAGE_EXTS)
        if not img_path:
            return None

        img = Image.open(img_path)
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        img = img.resize((135, 135), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _extract_video_thumbnail(self, device, video_path):
        """提取视频第一帧，裁切缩放到 135×135（与原程序一致）"""
        try:
            import cv2
            from PIL import Image
        except ImportError:
            self._log(device, "缺少 cv2 或 PIL 库")
            return None

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            ret, frame = cap.read()
            cap.release()
            if not ret:
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
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            self._log(device, f"提取视频缩略失败: {e}")
            return None

    def _log(self, device, msg):
        logger.info(f"[{device.name}] {msg}")
