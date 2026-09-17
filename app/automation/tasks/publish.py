# -*- coding: utf-8 -*-
# TikTok 发布任务 - 图文/视频发布，方法与原 iMouse Pro 完全一致

import base64
import io
import os
import time
import logging

from .base import BaseTask
from ..paths import resource_path, data_path

logger = logging.getLogger("automation.publish")

# 媒体文件根目录（与原程序一致）
MEDIA_BASE_DIR = r"D:\iMousePro\Shortcut\Media"

# 支持的视频/图片格式（按优先级；本地文件只用于提取缩略图做识图匹配，cv2 都能读）
VIDEO_EXTS = [".mov", ".mp4", ".m4v", ".avi", ".mkv", ".3gp", ".flv", ".wmv", ".webm"]
IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".bmp", ".webp"]

# icon 目录：只读资源，打包后在程序内部
ICON_DIR = resource_path("icon")


def _normalize_media_type(t):
    """规范化媒体类型，兼容中英文/大小写。返回 'picture' / 'video' / 原值"""
    s = str(t).strip().lower()
    if s in ("picture", "pic", "image", "img", "photo", "图文", "图片", "图", "照片"):
        return "picture"
    if s in ("video", "vid", "movie", "视频", "影片", "片"):
        return "video"
    return s


def _find_media_file(device_dir, file_name, exts):
    """在目录下按多种扩展名查找素材文件，返回完整路径或 None。
    兼容多种填法：纯文件名(77)、带扩展名(77.jpg)、甚至误填了完整路径。"""
    file_name = str(file_name).strip().strip('"').strip("'")
    if not file_name:
        return None

    # 0) 本身就是一个存在的完整文件路径 → 直接用
    if os.path.isfile(file_name):
        return file_name

    # 1) 只取文件名部分（用户可能误填了完整路径或带了目录）
    base = os.path.basename(file_name.replace("\\", "/").rstrip("/"))
    root, ext = os.path.splitext(base)

    # 2) base 已带素材扩展名且存在
    if ext and ext.lower() in exts:
        cand = os.path.join(device_dir, base)
        if os.path.exists(cand):
            return cand

    # 3) base（去掉可能的非素材扩展名）+ 依次尝试各扩展名
    stem = root if (ext and ext.lower() not in exts) else base
    for e in exts:
        cand = os.path.join(device_dir, stem + e)
        if os.path.exists(cand):
            return cand

    # 4) 按名字没匹配上，但设备文件夹里恰好只有一个该类型素材 → 直接用它
    #    （方便"一个设备文件夹放一个文件、名字随意"的用法）
    if os.path.isdir(device_dir):
        cands = [f for f in os.listdir(device_dir)
                 if os.path.splitext(f)[1].lower() in exts]
        if len(cands) == 1:
            return os.path.join(device_dir, cands[0])
    return None


def _not_found_msg(device_dir, file_name, exts, kind="素材"):
    """生成可诊断的"找不到文件"提示：显示查找目录、文件名、目录里实际有什么。"""
    parts = [f"找不到{kind}: 目录[{device_dir}] 里没有名为「{file_name}」"
             f"({'/'.join(e[1:] for e in exts)})的文件"]
    if not os.path.isdir(device_dir):
        parts.append(f"（该目录不存在，请确认设备名对应的文件夹已建立）")
    else:
        try:
            files = [f for f in os.listdir(device_dir)
                     if os.path.splitext(f)[1].lower() in exts]
            if files:
                parts.append(f"目录里现有: {', '.join(files[:8])}"
                             + ("..." if len(files) > 8 else ""))
            else:
                parts.append("（目录里没有任何匹配格式的文件）")
        except Exception:
            pass
    return "；".join(parts)


DEFAULT_PUBLISH_CONFIG = {
    "media_base_dir": MEDIA_BASE_DIR,
    "icon_dir": ICON_DIR,
    "icon_similarity": 0.7,
    "step_wait": 5,          # 关键步骤间等待（秒）
    "find_timeout": 15,      # 关键按钮识图最多轮询秒数（与 V2.0 实战程序一致）
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
        media_type = _normalize_media_type(cfg.get("type", "picture"))
        device_name = cfg.get("device_name") or device.name
        file_name = str(cfg.get("file", "")).strip()

        device_dir = os.path.join(cfg.get("media_base_dir", MEDIA_BASE_DIR), device_name)

        self._log(device, f"准备发布: 类型={media_type}, 素材={file_name}")

        if media_type == "picture":
            template_bytes = self._make_image_template(device, device_dir, file_name)
            if template_bytes is None:
                raise FileNotFoundError(
                    _not_found_msg(device_dir, file_name, IMAGE_EXTS, "图片素材"))
            ok = self._publish_image(device, template_bytes)
        elif media_type == "video":
            video_path = _find_media_file(device_dir, file_name, VIDEO_EXTS)
            if not video_path:
                raise FileNotFoundError(
                    _not_found_msg(device_dir, file_name, VIDEO_EXTS, "视频文件"))
            self._log(device, f"找到视频: {os.path.basename(video_path)}")
            template_bytes = self._extract_video_thumbnail(device, video_path)
            if template_bytes is None:
                raise RuntimeError("无法提取视频缩略图")
            ok = self._publish_video(device, template_bytes)
        else:
            raise ValueError(f"未知的媒体类型: {media_type}")

        # 各发布步骤失败时会抛出具体原因的异常；能走到这里即成功
        self.result = ok
        self._log(device, "发布成功")

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
            raise RuntimeError("图文发布失败：没填音乐URL（TikTok图文需要配音乐，"
                               "请在音乐URL框填写）")

        # 1-2. 回桌面 → 打开 TikTok（URL scheme 优先，识图兜底，确认真的进去了）
        self._open_tiktok(device, sim)

        # 3. 打开音乐 URL
        self._log(device, f"打开音乐URL: {url}")
        ret = device.open_url(url)
        if ret and not device._ok(ret):
            raise RuntimeError(f"图文发布失败：音乐URL打开失败({ret.get('message', '未知')})")
        self.wait(10)

        # 4. 点击 Use sound（音乐页加载有快有慢，轮询最多 find_timeout 秒）
        if not self._find_and_click(device, "usesound.bmp", sim):
            self._fail(device, "usesound_fail",
                       "图文发布失败：没找到 Use sound 按钮"
                       "（可能音乐URL没正常打开进音乐页，或TikTok界面变了）")

        # 5. 查找并点击封面图（在相册中）
        self._log(device, "查找封面图...")
        if not self._find_and_click_bytes(device, template_bytes, sim):
            self._fail(device, "cover_fail",
                       "图文发布失败：在相册里没找到这张图（请确认图片已上传到手机相册）")
        self.wait(3)

        # 6. 点击 next 两次
        for i in range(2):
            if not self._find_and_click(device, "next.bmp", sim, required=False, timeout=5):
                self._log(device, f"第{i+1}次 next 未找到（不影响）")
            self.wait(wait)

        # 7. 输入标题 + 描述
        self._input_title_desc(device, title, description, sim)

        # 8. 点击 post
        if not self._find_and_click(device, ["post.bmp", "旧版post.bmp"], sim, label="Post"):
            self._fail(device, "post_fail", "图文发布失败：没找到发布(Post)按钮")

        return True

    # ═══════════════════════════════════════════
    # 视频发布（与 _open_tiktok_app_with_video 一致）
    # ═══════════════════════════════════════════

    def _publish_video(self, device, template_bytes):
        cfg = self.config
        sim = cfg.get("icon_similarity", 0.7)
        wait = cfg.get("step_wait", 5)
        description = cfg.get("description", "")

        # 1-2. 回桌面 → 打开 TikTok（URL scheme 优先，识图兜底，确认真的进去了）
        self._open_tiktok(device, sim)

        # 3. 点击 + 按钮：识图（白/黑两版，轮询等首页加载）→ 底部正中坐标兜底
        self._tap_plus_button(device, sim)

        # 4. 查找并点击视频缩略图
        self._log(device, "查找视频缩略图...")
        if not self._find_and_click_bytes(device, template_bytes, sim):
            self._fail(device, "video_fail",
                       "视频发布失败：在相册里没找到这个视频"
                       "（请确认视频已上传到手机相册；或视频封面和相册里的不一致）")
        self.wait(3)

        # 5. 点击 next 两次
        for i in range(2):
            if not self._find_and_click(device, "next.bmp", sim, required=False, timeout=5):
                self._log(device, f"第{i+1}次 next 未找到（不影响）")
            self.wait(wait)

        # 6. 输入描述
        loc = (self._find_icon(device, "Add description.bmp", sim)
               or self._find_icon(device, "Writing a long description.bmp", sim))
        if loc:
            cx, cy = loc[0], loc[1]
            device.tap(cx, cy)
            self.wait(1)
            self._input_text(device, description)
        else:
            self._log(device, "未找到 Add description（跳过描述）")

        # 7. 点击 post
        if not self._find_and_click(device, ["post.bmp", "旧版post.bmp"], sim, label="Post"):
            self._fail(device, "post_fail",
                       "视频发布失败：没找到发布(Post)按钮"
                       "（可能卡在上一步，或Post按钮位置/图标变了）")

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

    def _save_debug_shot(self, device, tag):
        """发布失败时把当时的手机画面截图存到 debug 目录，方便排查是哪一步、什么界面。
        返回文件路径或 None。"""
        try:
            b64 = device.screenshot_b64()
            if not b64:
                return None
            shot_dir = data_path("debug")
            os.makedirs(shot_dir, exist_ok=True)
            safe = str(device.name).replace("/", "_").replace("\\", "_")
            fn = f"{safe}_{tag}_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            path = os.path.join(shot_dir, fn)
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
            self._log(device, f"已保存失败截图: {path}")
            return path
        except Exception:
            return None

    def _fail(self, device, tag, msg):
        """统一的失败处理：截图 + 抛出带截图路径的异常"""
        shot = self._save_debug_shot(device, tag)
        if shot:
            msg += f"（已存失败截图: {shot}）"
        raise RuntimeError(msg)

    # ── 打开 TikTok / 进入发布页（与 V2.0 实战程序 + 养号 _open_tiktok 一致）──

    def _open_tiktok(self, device, sim):
        """回桌面 → URL scheme 打开 TikTok（失败再识图点桌面图标）→ 验证已进入 → 点首页tab。

        旧逻辑只识图点一次桌面图标、找不到就干等 3 秒往下走，TikTok 根本没打开时
        后面必然报"没找到发布(+)按钮"。这里改成 V2.0 验证过的流程并加确认。
        """
        tiktok_icon = _icon(self.config, "tiktok.bmp")
        has_icon = os.path.exists(tiktok_icon)
        wait = self.config.get("step_wait", 5)

        for attempt in range(3):
            self._log(device, "返回主屏幕..." if attempt == 0 else f"第{attempt+1}次尝试打开 TikTok")
            device.press_home()
            self.wait(2)

            r = device.open_tiktok()           # tiktok:// → snssdk1233://，内部已等 4-6 秒
            if r is not None and device._ok(r):
                self._log(device, "已通过 URL scheme 打开 TikTok")
            elif has_icon:
                loc = device.find_image_file(tiktok_icon, sim)
                if loc:
                    self._log(device, f"URL 方式被拒绝，识图点击桌面图标 ({loc[0]}, {loc[1]})")
                    device.tap(loc[0], loc[1])
                else:
                    self._log(device, "URL 方式被拒绝，桌面也没找到 TikTok 图标")
            self.wait(wait)

            # 验证：桌面图标还在屏幕上 = 没进去，重试
            if has_icon and device.find_image_file(tiktok_icon, sim):
                self._log(device, "  仍在桌面，未进入 TikTok")
                continue
            # 进入后点一下底部首页tab，确保停在推荐页（发布(+)在首页底栏）
            device.tap_home_tab()
            self.wait(2)
            self._log(device, "已进入 TikTok 首页")
            return

        self._fail(device, "open_tiktok_fail",
                   "发布失败：多次尝试后仍未进入 TikTok"
                   "（请确认手机已解锁、TikTok 已安装且 iMouse 投屏正常）")

    def _tap_plus_button(self, device, sim):
        """点击底栏发布(+)：识图 +white/+black 轮询 → 底部正中坐标兜底。"""
        loc = self._find_and_click(device, ["+white.bmp", "+black.bmp"], sim,
                                   required=False, label="发布(+)")
        if loc:
            return
        # 识图没找到：TikTok 首页底栏的 + 固定在正中，用坐标兜底（SE 已按比例换算）
        pt = device.coords.get("plus_button")
        if not pt:
            self._fail(device, "plus_fail",
                       "视频发布失败：没找到发布(+)按钮"
                       "（可能没打开TikTok首页，或TikTok界面已更新导致图标识别不到）")
        self._log(device, f"识图未找到发布(+)，用坐标兜底 ({pt[0]}, {pt[1]})")
        device.tap(pt[0], pt[1])
        self.wait(3)
        # 兜底点击后验证：拍摄页应出现 record/record2 标记 或 底栏 + 消失
        for name in ("record2.bmp", "record.bmp"):
            p = _icon(self.config, name)
            if os.path.exists(p) and device.find_image_file(p, sim):
                self._log(device, "已进入拍摄/上传页")
                return
        still_plus = self._find_icon(device, "+white.bmp", sim) or self._find_icon(device, "+black.bmp", sim)
        if still_plus:
            self._fail(device, "plus_fail",
                       "视频发布失败：点击发布(+)后没进入拍摄页"
                       "（可能有弹窗挡住，或 TikTok 界面已更新）")
        self._log(device, "未识别到拍摄页标记，继续（依赖后续识图）")

    def _find_icon(self, device, icon_name, sim):
        path = _icon(self.config, icon_name)
        return device.find_image_file(path, sim)

    def _find_and_click(self, device, icon_names, sim, required=True, timeout=None, label=None):
        """识图找图标并点击（V2.0 实战程序的轮询方式）。

        icon_names: 单个文件名或列表（任一命中即点击）。
        timeout: 最多轮询秒数（默认 config.find_timeout=15），每秒查一次；
                 页面加载慢/有过渡动画时不会一查不到就放弃。
        返回命中的 (x, y)；没找到 / 图标文件不存在 返回 None（required 仅作说明，
        是否致命由调用方决定）。
        """
        if isinstance(icon_names, str):
            icon_names = [icon_names]
        paths = []
        for n in icon_names:
            p = _icon(self.config, n)
            if os.path.exists(p):
                paths.append((n, p))
            else:
                self._log(device, f"图标不存在: {n}")
        if not paths:
            return None
        if timeout is None:
            timeout = float(self.config.get("find_timeout", 15))
        label = label or "/".join(n for n, _ in paths)

        deadline = time.time() + max(1.0, timeout)
        while time.time() < deadline:          # V2.0 同款：每秒查一次，直到超时
            if self.should_stop:
                return None
            for n, p in paths:
                loc = device.find_image_file(p, sim)
                if loc:
                    cx, cy = loc[0], loc[1]
                    self._log(device, f"点击 {label} ({cx}, {cy})")
                    device.tap(cx, cy)
                    self.wait(3)
                    return (cx, cy)
            time.sleep(1)
        self._log(device, f"识图未找到 {label}（已等 {int(timeout)} 秒）")
        return None

    def _find_and_click_bytes(self, device, img_bytes, sim, timeout=None):
        """在屏幕上找素材缩略图并点击。相册网格加载有延迟，同样轮询等待。"""
        if timeout is None:
            timeout = float(self.config.get("find_timeout", 15))
        deadline = time.time() + max(1.0, timeout)
        while time.time() < deadline:
            if self.should_stop:
                return False
            loc = device.find_image_bytes(img_bytes, sim)
            if loc:
                cx, cy = loc[0], loc[1]
                self._log(device, f"点击素材 ({cx}, {cy})")
                device.tap(cx, cy)
                self.wait(3)
                return True
            time.sleep(1)
        self._log(device, f"识图未找到素材缩略图（已等 {int(timeout)} 秒）")
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
