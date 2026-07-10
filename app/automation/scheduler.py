# -*- coding: utf-8 -*-
# 定时发布调度器 - 到点自动派发发布任务

import json
import logging
import os
import threading
import time
from datetime import datetime

from .tasks.publish import PublishTask

logger = logging.getLogger("automation.scheduler")

from .paths import data_path

JOBS_FILE = data_path("publish_jobs.json")


class PublishJob:
    """单条定时发布任务"""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    def __init__(self, device_name, file, media_type, scheduled_time,
                 url="", title="", description="", status="pending",
                 message="", job_id=None, node_name=""):
        self.job_id = job_id or f"{device_name}_{file}_{int(time.time()*1000)}"
        self.device_name = device_name    # 纯设备名（用于定位素材文件夹）
        self.node_name = node_name        # 所属节点（哪台电脑），空=任意节点
        self.file = file
        self.media_type = media_type      # 'picture' / 'video'
        self.scheduled_time = scheduled_time  # datetime
        self.url = url
        self.title = title
        self.description = description
        self.status = status
        self.message = message

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "device_name": self.device_name,
            "node_name": self.node_name,
            "file": self.file,
            "media_type": self.media_type,
            "scheduled_time": self.scheduled_time.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(self.scheduled_time, datetime) else str(self.scheduled_time),
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, d):
        st = d.get("scheduled_time", "")
        try:
            st = datetime.strptime(st, "%Y-%m-%d %H:%M:%S")
        except Exception:
            st = datetime.now()
        return cls(
            device_name=d.get("device_name", ""),
            node_name=d.get("node_name", ""),
            file=d.get("file", ""),
            media_type=d.get("media_type", "picture"),
            scheduled_time=st,
            url=d.get("url", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            status=d.get("status", "pending"),
            message=d.get("message", ""),
            job_id=d.get("job_id"),
        )

    def to_publish_config(self):
        return {
            "device_name": self.device_name,
            "file": self.file,
            "type": self.media_type,
            "url": self.url,
            "title": self.title,
            "description": self.description,
        }


class PublishScheduler:
    """定时发布调度器

    在后台线程中每隔 check_interval 秒检查一次，
    到点的任务通过 engine 派发到对应设备执行。
    """

    def __init__(self, engine, log_callback=None, check_interval=5,
                 on_job_update=None):
        self.engine = engine
        self.log_callback = log_callback
        self.check_interval = check_interval
        self.on_job_update = on_job_update  # 任务状态变化回调

        self.jobs = []  # type: list[PublishJob]
        self._lock = threading.Lock()
        self._thread = None
        self._running = False
        self._active = {}  # device_name -> job_id (正在执行)
        self._warned_missing = set()  # 已提示过"找不到设备"的 job_id（避免刷屏）

    # ── 任务管理 ──

    def add_job(self, job):
        with self._lock:
            self.jobs.append(job)
        self.save_jobs()
        self._notify_update()

    def remove_job(self, job_id):
        with self._lock:
            self.jobs = [j for j in self.jobs if j.job_id != job_id]
        self.save_jobs()
        self._notify_update()

    def clear_jobs(self):
        with self._lock:
            self.jobs = []
        self.save_jobs()
        self._notify_update()

    def get_jobs(self):
        with self._lock:
            return list(self.jobs)

    # ── 持久化 ──

    def save_jobs(self):
        try:
            with self._lock:
                data = [j.to_dict() for j in self.jobs]
            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务失败: {e}")

    def load_jobs(self):
        if not os.path.exists(JOBS_FILE):
            return
        try:
            with open(JOBS_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            with self._lock:
                self.jobs = [PublishJob.from_dict(d) for d in data]
            self._notify_update()
        except Exception as e:
            logger.error(f"加载任务失败: {e}")

    def import_from_excel(self, path):
        """从 Excel 导入定时任务（列: devices|file|type|url|title|description|scheduled_time）"""
        import pandas as pd
        from .tasks.publish import _normalize_media_type
        df = pd.read_excel(path)
        count = 0
        for _, row in df.iterrows():
            try:
                st = row.get("scheduled_time")
                if pd.isna(st):
                    st = datetime.now()
                elif not isinstance(st, datetime):
                    st = pd.to_datetime(st).to_pydatetime()
                job = PublishJob(
                    device_name=str(row.get("devices", "")).strip(),
                    file=str(row.get("file", "")).strip(),
                    media_type=_normalize_media_type(row.get("type", "picture")),
                    scheduled_time=st,
                    url=str(row.get("url", "")) if not pd.isna(row.get("url", "")) else "",
                    title=str(row.get("title", "")) if not pd.isna(row.get("title", "")) else "",
                    description=str(row.get("description", "")) if not pd.isna(row.get("description", "")) else "",
                )
                with self._lock:
                    self.jobs.append(job)
                count += 1
            except Exception as e:
                logger.error(f"导入行失败: {e}")
        self.save_jobs()
        self._notify_update()
        return count

    # ── 调度循环 ──

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._log("定时发布调度器已启动")

    def stop(self):
        self._running = False
        self._log("定时发布调度器已停止")

    def _loop(self):
        while self._running:
            try:
                self._check_due_jobs()
            except Exception as e:
                logger.error(f"调度检查异常: {e}")
            time.sleep(self.check_interval)

    def _check_due_jobs(self):
        now = datetime.now()
        with self._lock:
            due = [
                j for j in self.jobs
                if j.status == PublishJob.STATUS_PENDING
                and isinstance(j.scheduled_time, datetime)
                and j.scheduled_time <= now
            ]

        if not due:
            return
        all_devices = self.engine._dm.get_devices()

        for job in due:
            # 同一设备同一时间只执行一个（用 节点+设备名 做键，避免跨节点重名冲突）
            active_key = f"{job.node_name}/{job.device_name}"
            if active_key in self._active:
                continue

            device = self._resolve_device(job, all_devices)
            if not device:
                # 设备暂时找不到：保持等待，下轮重试（可能设备还没连上），
                # 在信息列显示原因；只在日志提示一次并附上在线设备名，方便排查。
                if job.message != "等待设备连接":
                    job.message = "等待设备连接"
                    self._notify_update()
                if job.job_id not in self._warned_missing:
                    self._warned_missing.add(job.job_id)
                    names = "、".join(sorted({d.name for d in all_devices})) or "（无）"
                    self._log(f"[提示] 找不到设备「{job.device_name}」，任务[{job.file}]保持等待。"
                              f"当前在线设备: {names}（请确认设备名填对、设备在线）")
                continue

            self._warned_missing.discard(job.job_id)
            self._active[active_key] = job.job_id
            self._set_status(job, PublishJob.STATUS_RUNNING, "")
            self._log(f"[{device.node_name}/{device.name}] 开始定时发布: {job.file} ({job.media_type})")

            # 在引擎上执行（带回调更新状态）
            self._dispatch(job, device, active_key)

    def _resolve_device(self, job, all_devices):
        """根据 节点+设备名 解析设备；节点为空则只按设备名匹配"""
        for d in all_devices:
            if d.name != job.device_name:
                continue
            if job.node_name and d.node_name != job.node_name:
                continue
            return d
        return None

    def _dispatch(self, job, device, active_key):
        def _run():
            from .tasks.publish import PublishTask
            from .tasks.base import TaskStatus
            tag = f"{device.node_name}/{device.name}"
            task = PublishTask(config=job.to_publish_config())
            try:
                task.execute(device)
                if task.status == TaskStatus.COMPLETED:
                    self._set_status(job, PublishJob.STATUS_SUCCESS, "发布成功")
                    self._log(f"[{tag}] 发布成功: {job.file}")
                else:
                    err = task.error or "发布未完成"
                    self._set_status(job, PublishJob.STATUS_FAILED, err)
                    self._log(f"[{tag}] 发布失败: {job.file} - {err}")
                    if self.engine.error_reporter:
                        self.engine.error_reporter.report_error(
                            err, context=f"定时发布: {job.file} (节点 {device.node_name})",
                            device_name=device.name)
            except Exception as e:
                self._set_status(job, PublishJob.STATUS_FAILED, str(e))
                self._log(f"[{tag}] 发布异常: {e}")
                if self.engine.error_reporter:
                    self.engine.error_reporter.report_error(
                        e, context=f"定时发布: {job.file} (节点 {device.node_name})",
                        device_name=device.name)
            finally:
                self._active.pop(active_key, None)

        threading.Thread(target=_run, daemon=True).start()

    def _set_status(self, job, status, message):
        job.status = status
        job.message = message
        self.save_jobs()
        self._notify_update()

    def _notify_update(self):
        if self.on_job_update:
            try:
                self.on_job_update()
            except Exception:
                pass

    def _log(self, msg):
        logger.info(msg)
        if self.log_callback:
            self.log_callback(msg)
