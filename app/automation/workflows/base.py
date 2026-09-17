# -*- coding: utf-8 -*-
# 工作流基类 - 后台线程运行，开关控制启停

import logging
import threading

logger = logging.getLogger("automation.workflow")


class WorkflowBase:
    name = "workflow"
    display = "工作流"

    def __init__(self, device_manager, log_callback=None, error_reporter=None):
        self.dm = device_manager
        self.log_callback = log_callback
        self.error_reporter = error_reporter
        self._stop = threading.Event()
        self._thread = None
        self.running = False

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self.running = True
        self._thread = threading.Thread(target=self._run_wrapper, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self.running = False

    def _run_wrapper(self):
        try:
            self.run()
        except Exception as e:
            self._log(f"工作流异常: {e}")
            if self.error_reporter:
                self.error_reporter.report_error(e, context=f"工作流: {self.display}")
        finally:
            self.running = False

    def run(self):
        raise NotImplementedError

    @property
    def should_stop(self):
        return self._stop.is_set()

    def wait(self, seconds):
        """可中断等待"""
        self._stop.wait(seconds)

    def _log(self, msg):
        logger.info(f"[{self.name}] {msg}")
        if self.log_callback:
            self.log_callback(f"[工作流·{self.display}] {msg}")
