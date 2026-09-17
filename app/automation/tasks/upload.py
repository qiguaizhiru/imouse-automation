# -*- coding: utf-8 -*-
"""
素材上传：把电脑本地的图片/视频传到 iPhone（走 iMouse 快捷指令，Pro/XP 通用）

逻辑套用 V2.0 实战程序（transfer_gui.py 的 上传 选项卡）：
  上传目标  : album = 相册（shortcut 7 / XP album/upload）
              file  = 文件系统（iOS 15+，shortcut 8 / XP file/upload）
  分发方式  : 填了「素材文件夹」→ 文件夹模式优先：子文件夹名 = 设备自定义名
              （也兼容 设备ID / 序号 1,2,3…），每台设备只收自己文件夹里的文件；
              否则「统一文件上传」：所有设备都收到列表里的相同文件。
  执行方式  : 逐台设备、逐个文件串行上传（视频大，不批量以免整批超时）。

可选：上传成功后删除电脑上的原文件。
"""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Tuple

# 与 V2.0 / publish.py 一致的默认素材根目录（子文件夹 = 设备名）
DEFAULT_MEDIA_ROOTS = [r"D:\iMousePro\Shortcut\Media", r"D:\iMouse\Shortcut\Media"]

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".3gp", ".flv", ".wmv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".gif"}
MEDIA_EXTS = VIDEO_EXTS | IMAGE_EXTS


def default_media_root() -> str:
    """第一个存在的默认素材根目录，都不存在返回第一个"""
    for p in DEFAULT_MEDIA_ROOTS:
        if os.path.isdir(p):
            return p
    return DEFAULT_MEDIA_ROOTS[0]


def gather_dir(dirpath: str) -> List[str]:
    """递归收集目录下的媒体文件（V2.0 的 _get_folder_files_for_device 同款）"""
    out = []
    for root, _, names in os.walk(dirpath):
        for n in names:
            if os.path.splitext(n)[1].lower() in MEDIA_EXTS:
                out.append(os.path.abspath(os.path.join(root, n)))
    return sorted(out)


def scan_folder_dispatch(root_dir: str) -> Dict[str, List[str]]:
    """{子文件夹名: [媒体文件…]}，只收含媒体的子文件夹（递归）"""
    out: Dict[str, List[str]] = {}
    if not os.path.isdir(root_dir):
        return out
    for name in sorted(os.listdir(root_dir), key=lambda x: (len(x), x)):
        sub = os.path.join(root_dir, name)
        if not os.path.isdir(sub):
            continue
        files = gather_dir(sub)
        if files:
            out[name.strip()] = files
    return out


def build_device_index(devices) -> Dict[str, object]:
    """把设备按 自定义名 / 设备ID / 序号(1-based) 建索引。
    自定义名优先（V2.0 只按自定义名匹配），ID/序号是额外兼容。"""
    idx: Dict[str, object] = {}
    for i, d in enumerate(devices, 1):
        idx.setdefault(str(i), d)
        if d.device_id:
            idx.setdefault(str(d.device_id).strip(), d)
    for d in devices:
        # 自定义名最后写入 → 覆盖同名的序号/ID，保证"文件夹名=自定义名"优先
        if d.name:
            idx[str(d.name).strip()] = d
    return idx


def files_for_device(root_dir: str, device) -> Tuple[str, List[str]]:
    """文件夹模式：返回 (匹配到的子文件夹名, 文件列表)。按 自定义名 → 设备ID → 序号? 找。
    序号需要设备列表上下文，这里只查名字和ID；序号匹配在 run_folder 里通过索引完成。"""
    for key in (device.name, device.device_id):
        if not key:
            continue
        sub = os.path.join(root_dir, str(key).strip())
        if os.path.isdir(sub):
            return str(key).strip(), gather_dir(sub)
    return "", []


class UploadTask:
    """独立于 TaskRunner 的轻量任务：自己管线程池和停止标志"""

    def __init__(self, log_cb: Optional[Callable[[str], None]] = None,
                 progress_cb: Optional[Callable[[int, int, int], None]] = None):
        self._log_cb = log_cb or (lambda m: None)
        self._progress_cb = progress_cb or (lambda done, ok, fail: None)
        self._stop = threading.Event()
        self.running = False

    def stop(self):
        self._stop.set()

    def _log(self, msg):
        try:
            self._log_cb(msg)
        except Exception:
            pass

    # ─────────────────────────── 核心：单文件上传 ───────────────────────────

    @staticmethod
    def _upload_one(device, path: str, target: str, target_path: str,
                    outtime_ms: int) -> Tuple[bool, str]:
        """target='album' → 相册（target_path=相册名，空=Recents）
           target='file'  → 文件系统（target_path=手机目录，空=根目录）"""
        if not os.path.isfile(path):
            return False, "文件不存在"
        try:
            if target == "file":
                r = device.file_upload([path], path=target_path or "/", outtime=outtime_ms)
            else:
                r = device.album_upload([path], album=target_path or "Recents", outtime=outtime_ms)
            if r is None:
                return False, "无响应（超时或断连）"
            if device._ok(r):
                return True, "OK"
            return False, f"status={r.get('status')} {r.get('message', '')}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    # ─────────────────────────── 通用执行 ───────────────────────────

    def run_pairs(self, pairs: List[Tuple[object, str, str]], target: str = "album",
                  target_path: str = "", workers: int = 1, delete_after: bool = False,
                  outtime_ms: int = 90000) -> Dict[str, int]:
        """pairs: [(device, local_path, label), …]。同一设备串行；workers>1 时不同设备并发。"""
        self._stop.clear()
        self.running = True
        stat = {"ok": 0, "fail": 0, "deleted": 0, "total": len(pairs)}
        if not pairs:
            self._log("没有可上传的任务")
            self.running = False
            return stat

        by_dev: Dict[str, List[Tuple[object, str, str]]] = {}
        order: List[object] = []
        for dev, p, label in pairs:
            if dev.device_id not in by_dev:
                order.append(dev)
            by_dev.setdefault(dev.device_id, []).append((dev, p, label))

        where = (f"相册=[{target_path or 'Recents'}]" if target == "album"
                 else f"文件系统目录=[{target_path or '/'}]（需 iOS 15+）")
        self._log(f"共 {len(pairs)} 个文件 → {len(by_dev)} 台设备，{where}，"
                  f"并发 {max(1, min(workers, len(by_dev)))}")
        if delete_after:
            self._log("⚠ 已开启：上传成功后删除电脑上的原文件")

        done_files: List[str] = []
        lock = threading.Lock()

        def run_dev(dev, items, di):
            n = len(items)
            self._log(f"-- 设备 [{di}/{len(by_dev)}]: {dev.name} ({n} 个文件) --")
            ok_n = 0
            for i, (dev, p, label) in enumerate(items, 1):
                if self._stop.is_set():
                    return
                fname = os.path.basename(p)
                self._log(f"  [{i}/{n}] 上传中: {fname}")
                ok, why = self._upload_one(dev, p, target, target_path, outtime_ms)
                with lock:
                    if ok:
                        stat["ok"] += 1
                        ok_n += 1
                        done_files.append(p)
                        self._log(f"  [OK] {fname}")
                    else:
                        stat["fail"] += 1
                        self._log(f"  [FAIL] {fname}: {why}")
                    self._progress_cb(stat["ok"] + stat["fail"], stat["ok"], stat["fail"])
                time.sleep(0.4)
            self._log(f"  {dev.name}: 成功 {ok_n}/{n}")

        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(by_dev)))) as ex:
            futs = [ex.submit(run_dev, dev, by_dev[dev.device_id], i)
                    for i, dev in enumerate(order, 1)]
            for _ in as_completed(futs):
                pass

        if delete_after and done_files and not self._stop.is_set():
            for p in done_files:
                try:
                    os.remove(p)
                    stat["deleted"] += 1
                except Exception as e:
                    self._log(f"删除失败 {p}: {e}")
            self._log(f"已删除电脑上 {stat['deleted']} 个已上传文件")

        tail = "（已停止）" if self._stop.is_set() else ""
        self._log(f"上传任务完成{tail}: 成功 {stat['ok']} / 失败 {stat['fail']}"
                  + (f" / 删除 {stat['deleted']}" if delete_after else ""))
        self.running = False
        return stat

    # ─────────────────────────── 两种分发（V2.0 同款） ───────────────────────────

    def run_broadcast(self, devices, files: List[str], **kw) -> Dict[str, int]:
        """统一文件上传：所有设备相同文件"""
        files = [f for f in files if os.path.isfile(f)]
        pairs = [(d, f, "统一") for d in devices for f in files]
        return self.run_pairs(pairs, **kw)

    def run_folder(self, devices, root_dir: str, remove_empty_dir: bool = False,
                   **kw) -> Dict[str, int]:
        """按自定义名分文件夹上传：root_dir/<设备自定义名>/*  → 该设备。
        没有对应子文件夹的设备跳过（与 V2.0 一致），并列出没设备认领的文件夹。"""
        groups = scan_folder_dispatch(root_dir)
        if not groups:
            self._log(f"{root_dir} 下没有「含图片/视频」的子文件夹")
            return {"ok": 0, "fail": 0, "deleted": 0, "total": 0}
        pairs, claimed = [], set()
        for di, dev in enumerate(devices, 1):
            folder, files = files_for_device(root_dir, dev)
            if not files:
                # 兼容序号文件夹 1,2,3…
                if str(di) in groups:
                    folder, files = str(di), groups[str(di)]
            if not files:
                self._log(f"-- 设备 [{di}/{len(devices)}]: {dev.name} - 跳过"
                          f"(未找到子文件夹 '{dev.name}') --")
                continue
            claimed.add(folder)
            for f in files:
                pairs.append((dev, f, folder))
        for folder, files in groups.items():
            if folder not in claimed:
                self._log(f"文件夹 [{folder}] ({len(files)} 个文件) 没有对应的已勾选设备，跳过")
        stat = self.run_pairs(pairs, **kw)
        if kw.get("delete_after") and remove_empty_dir and not self._stop.is_set():
            for folder in claimed:
                d = os.path.join(root_dir, folder)
                try:
                    if os.path.isdir(d) and not os.listdir(d):
                        os.rmdir(d)
                        self._log(f"已移除空文件夹 [{folder}]")
                except Exception:
                    pass
        return stat
