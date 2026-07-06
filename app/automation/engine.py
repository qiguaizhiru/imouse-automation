import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, List, Optional

from .device import DeviceManager, Device
from .tasks.base import BaseTask, TaskStatus
from .config import load_config
from .logger import setup_logger

logger = logging.getLogger("automation.engine")


class TaskRunner:
    """单个设备上的任务运行信息"""

    def __init__(self, device, task, future):
        self.device = device
        self.task = task
        self.future = future  # type: Future

    @property
    def is_done(self):
        return self.future.done()


class AutomationEngine:
    """自动化引擎 - 调度多设备并行执行任务

    用法:
        engine = AutomationEngine()
        engine.start()

        # 对所有在线设备执行养号
        from automation.tasks import NurtureTask
        engine.run_task_on_all(NurtureTask, config={...})

        # 或对指定设备
        engine.run_task_on_device("设备名", NurtureTask, config={...})

        engine.stop_all()
        engine.shutdown()
    """

    def __init__(self, config=None, max_workers=10, log_callback=None,
                 error_reporter=None, device_manager=None):
        self.config = config or load_config()
        self.max_workers = max_workers
        self.log_callback = log_callback  # GUI 日志回调
        self.error_reporter = error_reporter

        setup_logger("automation")
        # 设备管理器：可传入多节点管理器；默认单节点（本机）
        if device_manager is not None:
            self._dm = device_manager
        else:
            self._dm = DeviceManager(
                host=self.config.get("imouse_host", "127.0.0.1"),
                port=self.config.get("imouse_port", 9912),
            )
        self._pool = None  # type: Optional[ThreadPoolExecutor]
        self._runners = {}  # type: Dict[str, TaskRunner]  # device_id -> runner
        self._lock = threading.Lock()
        self._running = False

    def start(self):
        if self._running:
            return
        self._pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self._running = True
        logger.info(f"自动化引擎启动 (最大并发: {self.max_workers})")

    def shutdown(self):
        self.stop_all()
        if self._pool:
            self._pool.shutdown(wait=True, cancel_futures=True)
            self._pool = None
        self._running = False
        logger.info("自动化引擎已关闭")

    def get_devices(self):
        return self._dm.get_devices()

    def run_task_on_device(self, device, task_cls, config=None):
        """在指定设备上运行一个任务

        Args:
            device: Device 实例或设备名称字符串
            task_cls: BaseTask 子类
            config: 任务配置字典
        Returns:
            TaskRunner 或 None
        """
        if not self._running:
            logger.error("引擎未启动，请先调用 start()")
            return None

        if isinstance(device, str):
            dev = self._dm.get_device_by_name(device)
            if not dev:
                logger.error(f"找不到设备: {device}")
                return None
        else:
            dev = device

        with self._lock:
            existing = self._runners.get(dev.device_id)
            if existing and not existing.is_done:
                logger.warning(f"[{dev.name}] 已有任务在运行，跳过")
                return None

        task = task_cls(config=config)
        future = self._pool.submit(self._execute_task, dev, task)
        runner = TaskRunner(dev, task, future)

        with self._lock:
            self._runners[dev.device_id] = runner

        return runner

    def run_task_on_all(self, task_cls, config=None, device_filter=None):
        """在所有在线设备上运行任务

        Args:
            task_cls: BaseTask 子类
            config: 任务配置字典
            device_filter: 可选的过滤函数 fn(Device) -> bool
        Returns:
            启动的 TaskRunner 列表
        """
        devices = self._dm.get_devices()
        if device_filter:
            devices = [d for d in devices if device_filter(d)]

        runners = []
        for dev in devices:
            runner = self.run_task_on_device(dev, task_cls, config)
            if runner:
                runners.append(runner)

        logger.info(f"已在 {len(runners)} 台设备上启动任务: {task_cls.name}")
        return runners

    def run_task_on_selected(self, device_names, task_cls, config=None):
        """在指定名称列表的设备上运行任务"""
        runners = []
        for name in device_names:
            runner = self.run_task_on_device(name, task_cls, config)
            if runner:
                runners.append(runner)
        return runners

    def stop_device(self, device_id):
        """停止指定设备上的任务"""
        with self._lock:
            runner = self._runners.get(device_id)
        if runner and not runner.is_done:
            runner.task.stop()
            logger.info(f"[{runner.device.name}] 发送停止信号")

    def stop_all(self):
        with self._lock:
            runners = list(self._runners.values())
        for runner in runners:
            if not runner.is_done:
                runner.task.stop()
        logger.info(f"已向 {len(runners)} 个运行中任务发送停止信号")

    def pause_device(self, device_id):
        with self._lock:
            runner = self._runners.get(device_id)
        if runner and not runner.is_done:
            runner.task.pause()

    def resume_device(self, device_id):
        with self._lock:
            runner = self._runners.get(device_id)
        if runner and not runner.is_done:
            runner.task.resume()

    def get_status(self):
        """获取所有任务的状态"""
        result = {}
        with self._lock:
            for did, runner in self._runners.items():
                result[did] = {
                    "device_name": runner.device.name,
                    "task": runner.task.name,
                    "status": runner.task.status.value,
                    "error": runner.task.error,
                    "progress": runner.task.progress,
                }
        return result

    def _execute_task(self, device, task):
        try:
            if self.log_callback:
                self.log_callback(f"[{device.name}] 开始: {task.name}")
            task.execute(device)
            if self.log_callback:
                self.log_callback(f"[{device.name}] 结束: {task.name} ({task.status.value})")
            if task.status == TaskStatus.FAILED and task.error and self.error_reporter:
                self.error_reporter.report_error(
                    task.error,
                    context=f"任务: {task.name}",
                    device_name=device.name,
                )
        except Exception as e:
            logger.error(f"[{device.name}] 任务执行异常: {e}")
            if self.error_reporter:
                self.error_reporter.report_error(
                    e, context=f"任务: {task.name}", device_name=device.name)
        finally:
            with self._lock:
                if device.device_id in self._runners:
                    runner = self._runners[device.device_id]
                    if runner.task is task:
                        pass  # 保留记录供查询
