import logging
import threading
import time
from enum import Enum

logger = logging.getLogger("automation.task")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class BaseTask:
    """所有自动化任务的基类

    子类需实现 run(device) 方法，该方法包含具体的自动化逻辑。
    框架负责生命周期管理（启动/停止/暂停）、日志、错误处理。
    """

    name = "base_task"
    description = "基础任务"

    def __init__(self, config=None):
        self.config = config or {}
        self.status = TaskStatus.PENDING
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 初始状态为未暂停
        self.error = None
        self.progress = {}  # 子类可用来上报进度

    def run(self, device):
        """子类实现此方法，包含具体的自动化流程"""
        raise NotImplementedError

    def execute(self, device):
        """框架调用此方法来执行任务，包装了生命周期管理"""
        self.status = TaskStatus.RUNNING
        self.error = None
        logger.info(f"[{device.name}] 开始任务: {self.name}")
        try:
            self.run(device)
            if self._stop_event.is_set():
                self.status = TaskStatus.STOPPED
                logger.info(f"[{device.name}] 任务被停止: {self.name}")
            else:
                self.status = TaskStatus.COMPLETED
                logger.info(f"[{device.name}] 任务完成: {self.name}")
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            logger.error(f"[{device.name}] 任务失败: {self.name} - {e}")

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()  # 如果暂停中也要能停下来

    def pause(self):
        self._pause_event.clear()
        self.status = TaskStatus.PAUSED
        logger.info(f"任务暂停: {self.name}")

    def resume(self):
        self._pause_event.set()
        self.status = TaskStatus.RUNNING
        logger.info(f"任务恢复: {self.name}")

    @property
    def should_stop(self):
        return self._stop_event.is_set()

    def check_pause(self):
        """在任务循环中调用，暂停时阻塞直到恢复或停止"""
        self._pause_event.wait()

    def wait(self, seconds):
        """可中断的等待，停止信号会立即打断"""
        self._stop_event.wait(seconds)
