# -*- coding: utf-8 -*-
# iMouse Pro 自动化中心 - 主程序

import json
import os
import random
import sys
import time
import threading

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

from .ui_form import Ui_AutomationWindow
from .engine import AutomationEngine
from .device import DeviceManager
from .nodes import MultiNodeManager, load_nodes, save_nodes
from .tasks.nurture import NurtureTask, DEFAULT_NURTURE_CONFIG
from .scheduler import PublishScheduler, PublishJob
from .config import load_config, save_config
from .error_reporter import ErrorReporter, load_user_info, save_user_info
from .paths import data_path
from .updater import Updater
from .version import VERSION

SCRIPT_DIR = data_path("")  # 可写数据目录（配置/文件对话框起始目录）
CONFIG_FILE = data_path("config.json")
NURTURE_CONFIG_FILE = data_path("nurture_config.json")


class AutomationApp(QtWidgets.QMainWindow):
    _signal_log = pyqtSignal(str)
    _signal_refresh_progress = pyqtSignal()
    _signal_refresh_jobs = pyqtSignal()
    _signal_refresh_nodes = pyqtSignal()
    _signal_update_result = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        # UI
        self._ui = Ui_AutomationWindow()
        self._ui.setupUi(self)

        # 错误上报（飞书群机器人）
        self._reporter = ErrorReporter()

        # 全局异常钩子
        self._orig_excepthook = sys.excepthook
        sys.excepthook = self._global_except_hook

        # 状态
        self._devices = []          # list[Device]
        self._engine = None         # AutomationEngine
        self._is_running = False
        self._is_paused = False
        self._start_time = None
        self._scheduler = None      # PublishScheduler
        self._node_manager = None   # MultiNodeManager
        self._node_status = {}      # 节点名 -> {online, device_count, host, port}

        # 信号绑定
        self._signal_log.connect(self._append_log)
        self._signal_refresh_progress.connect(self._refresh_progress_table)
        self._signal_refresh_jobs.connect(self._refresh_jobs_table)
        self._signal_refresh_nodes.connect(self._refresh_nodes_table)
        self._signal_update_result.connect(self._on_update_result)

        # 按钮事件
        self._ui.button_refresh.clicked.connect(self._refresh_devices)
        self._ui.button_select_all.clicked.connect(self._select_all_devices)
        self._ui.button_select_none.clicked.connect(self._deselect_all_devices)
        self._ui.button_clear_log.clicked.connect(
            lambda: self._ui.textEdit_log.clear())

        self._ui.button_start_nurture.clicked.connect(self._start_nurture)
        self._ui.button_pause_nurture.clicked.connect(self._toggle_pause)
        self._ui.button_stop_nurture.clicked.connect(self._stop_nurture)

        # 定时发布 Tab
        self._ui.button_add_job.clicked.connect(self._add_publish_job)
        self._ui.button_import_jobs.clicked.connect(self._import_jobs_excel)
        self._ui.button_start_scheduler.clicked.connect(self._start_scheduler)
        self._ui.button_stop_scheduler.clicked.connect(self._stop_scheduler)
        self._ui.button_del_job.clicked.connect(self._delete_selected_job)
        self._ui.button_clear_jobs.clicked.connect(self._clear_finished_jobs)

        # 设置 Tab
        self._ui.button_test_conn.clicked.connect(self._test_connection)
        self._ui.button_save_config.clicked.connect(self._save_nurture_config)
        self._ui.button_load_config.clicked.connect(self._load_nurture_config)
        self._ui.button_reset_config.clicked.connect(self._reset_nurture_config)
        self._ui.button_save_username.clicked.connect(self._save_username)
        self._ui.button_test_email.clicked.connect(self._test_email)
        self._ui.button_add_node.clicked.connect(self._add_node)
        self._ui.button_del_node.clicked.connect(self._delete_node)
        self._ui.button_check_update.clicked.connect(self._check_update)

        # 版本号 + 更新器
        self._ui.label_version.setText(f"v{VERSION}")
        self._updater = Updater(log_callback=self._log)

        # 进度刷新定时器
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._on_progress_tick)

        # 默认发布时间设为当前时间，结束时间默认 +3 小时（随机时间段用）
        from PyQt6.QtCore import QDateTime
        now_dt = QDateTime.currentDateTime()
        self._ui.dateTime_pub.setDateTime(now_dt)
        self._ui.dateTime_pub_end.setDateTime(now_dt.addSecs(3 * 3600))
        # 随机控件可用性随勾选联动
        self._ui.check_random_time.toggled.connect(self._toggle_random_time_ui)
        self._ui.check_random_duration.toggled.connect(self._toggle_random_duration_ui)
        self._ui.check_simple_mode.toggled.connect(self._toggle_simple_mode_ui)
        self._toggle_random_time_ui(False)
        self._toggle_random_duration_ui(False)
        self._toggle_simple_mode_ui(True)

        # 加载已有配置
        self._load_saved_config()
        self._update_username_display()
        self._refresh_nodes_table()
        self._init_scheduler()

        # 首次使用: 弹出用户名设置
        QTimer.singleShot(300, self._prompt_username_if_needed)

        # 启动时自动刷新设备
        QTimer.singleShot(500, self._refresh_devices)

    # ═══════════════════════════════════════════════
    # 日志
    # ═══════════════════════════════════════════════

    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        if threading.current_thread() is threading.main_thread():
            self._append_log(f"[{ts}] {msg}")
        else:
            self._signal_log.emit(f"[{ts}] {msg}")

    def _append_log(self, text):
        self._ui.textEdit_log.append(text)
        sb = self._ui.textEdit_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ═══════════════════════════════════════════════
    # 设备管理
    # ═══════════════════════════════════════════════

    def _get_dm(self):
        """返回共享的多节点管理器"""
        if self._node_manager is None:
            self._node_manager = MultiNodeManager()
        return self._node_manager

    def _refresh_devices(self):
        self._log("正在刷新设备列表...")
        dm = self._get_dm()
        try:
            self._devices = dm.get_devices()
        except Exception as e:
            self._log(f"刷新设备失败: {e}")
            self._devices = []

        table = self._ui.table_devices
        table.setRowCount(len(self._devices))

        se_count = 0
        nodes_seen = set()
        for i, dev in enumerate(self._devices):
            # 勾选框
            chk = QtWidgets.QTableWidgetItem()
            chk.setCheckState(Qt.CheckState.Checked)
            table.setItem(i, 0, chk)
            # 节点
            nodes_seen.add(dev.node_name)
            node_item = QtWidgets.QTableWidgetItem(dev.node_name)
            if dev.node_name != "本机":
                node_item.setForeground(QColor("#7B1FA2"))
            table.setItem(i, 1, node_item)
            # 名称
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(dev.name))
            # ID
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(dev.device_id[:16]))
            # 型号（系统型号 + 机型标识）
            model = dev.info.get("device_name", "")
            type_label = "SE" if dev.model_type == "se" else "标准"
            model_item = QtWidgets.QTableWidgetItem(f"{model} [{type_label}]")
            if dev.model_type == "se":
                model_item.setForeground(QColor("#E65100"))
                se_count += 1
            table.setItem(i, 4, model_item)
            # 状态
            status_item = QtWidgets.QTableWidgetItem("在线")
            status_item.setForeground(QColor("#4CAF50"))
            table.setItem(i, 5, status_item)

        if self._devices:
            parts = [f"{len(self._devices)}台设备"]
            if len(nodes_seen) > 1:
                parts.append(f"{len(nodes_seen)}个节点")
            if se_count:
                parts.append(f"SE机型{se_count}台")
            self._ui.label_status.setText(f"已连接 ({len(self._devices)}台)")
            self._ui.label_status.setStyleSheet(
                "color: #4CAF50; font-weight: bold; padding: 4px;")
            self._log("找到 " + "，".join(parts))
        else:
            self._ui.label_status.setText("未连接")
            self._ui.label_status.setStyleSheet(
                "color: #F44336; font-weight: bold; padding: 4px;")
            self._log("未找到设备，请确认 iMouse Pro 已启动")

        # 顺便刷新各节点的连接状态（多电脑时能看到每台在线情况）
        self._refresh_node_status()

    def _select_all_devices(self):
        table = self._ui.table_devices
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all_devices(self):
        table = self._ui.table_devices
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _get_checked_devices(self):
        table = self._ui.table_devices
        checked = []
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                if i < len(self._devices):
                    checked.append(self._devices[i])
        return checked

    # ═══════════════════════════════════════════════
    # 养号控制
    # ═══════════════════════════════════════════════

    def _build_nurture_config(self):
        ui = self._ui
        keywords_text = ui.lineEdit_keywords.text().strip()
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()] \
            if keywords_text else []

        cfg = {
            "simple_mode": ui.check_simple_mode.isChecked(),
            "total_duration_min": ui.spin_duration.value(),
            "random_duration": ui.check_random_duration.isChecked(),
            "duration_min": ui.spin_duration_min.value(),
            "duration_max": ui.spin_duration_max.value(),
            "videos_per_session": ui.spin_videos.value(),
            "session_count": ui.spin_sessions.value(),
            "watch_time_min": ui.spin_watch_min.value(),
            "watch_time_max": ui.spin_watch_max.value(),
            "long_watch_chance": ui.spin_long_watch.value(),
            "full_watch_chance": ui.spin_full_watch.value(),
            "search_enabled": ui.check_search.isChecked(),
            "search_interval_videos": ui.spin_search_interval.value(),
            "search_keywords": keywords,
            "rest_enabled": ui.check_rest.isChecked(),
            "rest_interval_videos": ui.spin_rest_interval.value(),
            "rest_time_min": ui.spin_rest_min.value(),
            "rest_time_max": ui.spin_rest_max.value(),
        }

        for key, spin in ui._interact_spins.items():
            cfg[key] = spin.value()

        return cfg

    def _apply_config_to_ui(self, cfg):
        ui = self._ui
        ui.check_simple_mode.setChecked(cfg.get("simple_mode", True))
        ui.spin_duration.setValue(cfg.get("total_duration_min", 30))
        ui.check_random_duration.setChecked(cfg.get("random_duration", False))
        ui.spin_duration_min.setValue(cfg.get("duration_min", 20))
        ui.spin_duration_max.setValue(cfg.get("duration_max", 60))
        ui.spin_videos.setValue(cfg.get("videos_per_session", 15))
        ui.spin_sessions.setValue(cfg.get("session_count", 0))
        ui.spin_watch_min.setValue(cfg.get("watch_time_min", 3))
        ui.spin_watch_max.setValue(cfg.get("watch_time_max", 30))
        ui.spin_long_watch.setValue(cfg.get("long_watch_chance", 0.2))
        ui.spin_full_watch.setValue(cfg.get("full_watch_chance", 0.1))
        ui.check_search.setChecked(cfg.get("search_enabled", True))
        ui.spin_search_interval.setValue(cfg.get("search_interval_videos", 20))
        keywords = cfg.get("search_keywords", [])
        ui.lineEdit_keywords.setText(", ".join(keywords) if keywords else "")
        ui.check_rest.setChecked(cfg.get("rest_enabled", True))
        ui.spin_rest_interval.setValue(cfg.get("rest_interval_videos", 30))
        ui.spin_rest_min.setValue(cfg.get("rest_time_min", 10))
        ui.spin_rest_max.setValue(cfg.get("rest_time_max", 30))

        for key, spin in ui._interact_spins.items():
            if key in cfg:
                spin.setValue(cfg[key])

    def _start_nurture(self):
        checked = self._get_checked_devices()
        if not checked:
            QMessageBox.warning(self, "提示", "请先勾选要养号的设备")
            return

        nurture_cfg = self._build_nurture_config()

        # 校验随机时长范围
        if nurture_cfg.get("random_duration"):
            if nurture_cfg["duration_min"] > nurture_cfg["duration_max"]:
                QMessageBox.warning(self, "提示", "随机时长的最小值不能大于最大值")
                return

        self._engine = AutomationEngine(
            max_workers=max(len(checked), 1),
            log_callback=self._log,
            error_reporter=self._reporter,
            device_manager=self._get_dm(),
        )
        self._engine.start()

        self._is_running = True
        self._is_paused = False
        self._start_time = time.time()

        # 更新 UI 状态
        self._ui.button_start_nurture.setEnabled(False)
        self._ui.button_pause_nurture.setEnabled(True)
        self._ui.button_stop_nurture.setEnabled(True)
        self._set_config_enabled(False)

        # 初始化进度表
        pt = self._ui.table_progress
        pt.setRowCount(len(checked))
        for i, dev in enumerate(checked):
            pt.setItem(i, 0, QtWidgets.QTableWidgetItem(dev.name))
            status_item = QtWidgets.QTableWidgetItem("启动中...")
            status_item.setForeground(QColor("#FF9800"))
            pt.setItem(i, 1, status_item)
            for j in range(2, 7):
                pt.setItem(i, j, QtWidgets.QTableWidgetItem("0"))

        # 启动任务
        if nurture_cfg.get("random_duration"):
            self._log(f"开始养号 | 设备: {len(checked)}台 | "
                      f"随机时长: {nurture_cfg['duration_min']}~{nurture_cfg['duration_max']}分钟（每台独立随机）")
        else:
            self._log(f"开始养号 | 设备: {len(checked)}台 | "
                      f"时长: {nurture_cfg['total_duration_min']}分钟")

        for dev in checked:
            dev_cfg = dict(nurture_cfg)
            # 随机时长：每台设备独立随机一个时长，做到"每次不一样"
            if dev_cfg.get("random_duration"):
                dur = random.randint(dev_cfg["duration_min"], dev_cfg["duration_max"])
                dev_cfg["total_duration_min"] = dur
                self._log(f"  [{dev.name}] 本次养号时长: {dur}分钟")
            self._engine.run_task_on_device(dev, NurtureTask, config=dev_cfg)

        # 启动进度刷新
        self._progress_timer.start(2000)

    def _toggle_pause(self):
        if not self._engine:
            return

        if self._is_paused:
            # 恢复
            status = self._engine.get_status()
            for did in status:
                self._engine.resume_device(did)
            self._is_paused = False
            self._ui.button_pause_nurture.setText("暂停")
            self._log("所有任务已恢复")
        else:
            # 暂停
            status = self._engine.get_status()
            for did in status:
                self._engine.pause_device(did)
            self._is_paused = True
            self._ui.button_pause_nurture.setText("恢复")
            self._log("所有任务已暂停")

    def _stop_nurture(self):
        if not self._engine:
            return
        self._log("正在停止所有养号任务...")
        self._engine.stop_all()

        # 在后台等待完成
        def _wait_shutdown():
            if self._engine:
                self._engine.shutdown()
            self._signal_log.emit("所有任务已停止")
            self._signal_refresh_progress.emit()

        threading.Thread(target=_wait_shutdown, daemon=True).start()

        self._is_running = False
        self._is_paused = False
        self._progress_timer.stop()
        self._ui.button_start_nurture.setEnabled(True)
        self._ui.button_pause_nurture.setEnabled(False)
        self._ui.button_pause_nurture.setText("暂停")
        self._ui.button_stop_nurture.setEnabled(False)
        self._set_config_enabled(True)

    def _set_config_enabled(self, enabled):
        for widget in [
            self._ui.check_simple_mode,
            self._ui.spin_duration, self._ui.spin_videos, self._ui.spin_sessions,
            self._ui.check_random_duration,
            self._ui.spin_watch_min, self._ui.spin_watch_max,
            self._ui.spin_long_watch, self._ui.spin_full_watch,
            self._ui.check_search, self._ui.spin_search_interval,
            self._ui.lineEdit_keywords,
            self._ui.check_rest, self._ui.spin_rest_interval,
            self._ui.spin_rest_min, self._ui.spin_rest_max,
        ]:
            widget.setEnabled(enabled)
        for spin in self._ui._interact_spins.values():
            spin.setEnabled(enabled)
        # 恢复时重新应用联动状态
        if enabled:
            self._toggle_random_duration_ui(self._ui.check_random_duration.isChecked())
            self._toggle_simple_mode_ui(self._ui.check_simple_mode.isChecked())
        else:
            self._ui.spin_duration_min.setEnabled(False)
            self._ui.spin_duration_max.setEnabled(False)

    # ═══════════════════════════════════════════════
    # 进度刷新
    # ═══════════════════════════════════════════════

    def _on_progress_tick(self):
        if not self._engine:
            return
        self._refresh_progress_table()

        # 检查是否全部完成
        status = self._engine.get_status()
        all_done = all(
            s["status"] in ("completed", "failed", "stopped")
            for s in status.values()
        )
        if all_done and status:
            self._progress_timer.stop()
            self._log("所有养号任务已结束")
            self._is_running = False
            self._ui.button_start_nurture.setEnabled(True)
            self._ui.button_pause_nurture.setEnabled(False)
            self._ui.button_stop_nurture.setEnabled(False)
            self._set_config_enabled(True)

    def _refresh_progress_table(self):
        if not self._engine:
            return
        status = self._engine.get_status()
        pt = self._ui.table_progress

        elapsed = ""
        if self._start_time:
            mins = (time.time() - self._start_time) / 60
            elapsed = f"{mins:.1f}分钟"

        row = 0
        for did, info in status.items():
            if row >= pt.rowCount():
                break
            p = info.get("progress", {})

            # 状态颜色
            s = info["status"]
            status_item = QtWidgets.QTableWidgetItem(self._status_cn(s))
            color_map = {
                "running": "#4CAF50", "paused": "#FF9800",
                "completed": "#1976D2", "failed": "#F44336",
                "stopped": "#9E9E9E", "pending": "#FF9800",
            }
            status_item.setForeground(
                QColor(color_map.get(s, "#333")))
            pt.setItem(row, 0, QtWidgets.QTableWidgetItem(info["device_name"]))
            pt.setItem(row, 1, status_item)
            pt.setItem(row, 2, QtWidgets.QTableWidgetItem(
                str(p.get("videos_watched", 0))))
            pt.setItem(row, 3, QtWidgets.QTableWidgetItem(
                str(p.get("likes_given", 0))))
            pt.setItem(row, 4, QtWidgets.QTableWidgetItem(
                str(p.get("follows_given", 0))))
            pt.setItem(row, 5, QtWidgets.QTableWidgetItem(
                str(p.get("searches_done", 0))))
            pt.setItem(row, 6, QtWidgets.QTableWidgetItem(elapsed))
            row += 1

    @staticmethod
    def _status_cn(s):
        m = {
            "running": "运行中", "paused": "已暂停",
            "completed": "已完成", "failed": "失败",
            "stopped": "已停止", "pending": "等待中",
        }
        return m.get(s, s)

    # ═══════════════════════════════════════════════
    # 定时发布
    # ═══════════════════════════════════════════════

    def _init_scheduler(self):
        engine = AutomationEngine(
            max_workers=10,
            log_callback=self._log,
            error_reporter=self._reporter,
            device_manager=self._get_dm(),
        )
        self._scheduler = PublishScheduler(
            engine=engine,
            log_callback=self._log,
            on_job_update=lambda: self._signal_refresh_jobs.emit(),
        )
        self._scheduler.load_jobs()
        self._refresh_jobs_table()

    def _toggle_random_time_ui(self, checked):
        """随机时间勾选时启用结束时间，并把'发布时间'标签改为'起始时间'语义"""
        self._ui.dateTime_pub_end.setEnabled(checked)
        self._ui.label_pub_end.setEnabled(checked)

    def _toggle_random_duration_ui(self, checked):
        """随机时长勾选时启用范围、禁用固定时长"""
        self._ui.spin_duration.setEnabled(not checked)
        self._ui.spin_duration_min.setEnabled(checked)
        self._ui.spin_duration_max.setEnabled(checked)
        self._ui.label_rand_dur.setEnabled(checked)

    def _toggle_simple_mode_ui(self, checked):
        """简单模式勾选时，灰掉会切页面的互动/搜索控件（只留点赞）"""
        ui = self._ui
        # 简单模式下禁用：关注/评论/查看主页/浏览评论/切换Tab + 搜索
        for key in ("follow_chance", "comment_chance", "profile_view_chance",
                    "scroll_comments_chance", "switch_tab_chance"):
            spin = ui._interact_spins.get(key)
            if spin:
                spin.setEnabled(not checked)
        for w in (ui.check_search, ui.spin_search_interval, ui.lineEdit_keywords):
            w.setEnabled(not checked)

    def _add_publish_job(self):
        device_name = self._ui.lineEdit_pub_device.text().strip()
        file = self._ui.lineEdit_pub_file.text().strip()
        if not file:
            QMessageBox.warning(self, "提示", "请填写素材文件名")
            return

        # 设备名为空：对所有勾选的设备各建一条（带节点信息）
        if not device_name:
            checked = self._get_checked_devices()
            if not checked:
                QMessageBox.warning(self, "提示", "请填写设备名，或在左侧勾选设备")
                return
            targets = [(d.name, d.node_name) for d in checked]
        else:
            targets = [(device_name, "")]  # 手动输入设备名，节点留空=任意

        media_type = "picture" if self._ui.combo_pub_type.currentIndex() == 0 else "video"
        url = self._ui.lineEdit_pub_url.text().strip()
        title = self._ui.lineEdit_pub_title.text().strip()
        desc = self._ui.lineEdit_pub_desc.text().strip()

        # 时间：固定 或 时间段内随机
        random_time = self._ui.check_random_time.isChecked()
        start_dt = self._ui.dateTime_pub.dateTime().toPyDateTime()
        end_dt = self._ui.dateTime_pub_end.dateTime().toPyDateTime()
        if random_time:
            if end_dt <= start_dt:
                QMessageBox.warning(self, "提示", "随机时间的结束时间必须晚于发布时间")
                return

        if media_type == "picture" and not url:
            reply = QMessageBox.question(
                self, "确认", "图文模式通常需要音乐URL，确定不填吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        span = (end_dt - start_dt).total_seconds() if random_time else 0
        for dn, node in targets:
            # 随机时间：每条任务在时间段内独立随机一个时刻，做到"每条都不同"
            if random_time:
                from datetime import timedelta
                sched_dt = start_dt + timedelta(seconds=random.uniform(0, span))
                sched_dt = sched_dt.replace(microsecond=0)
            else:
                sched_dt = start_dt
            job = PublishJob(
                device_name=dn, node_name=node, file=file, media_type=media_type,
                scheduled_time=sched_dt, url=url, title=title, description=desc,
            )
            self._scheduler.add_job(job)

        if random_time:
            self._log(f"已添加 {len(targets)} 条发布任务 | 随机时间段: "
                      f"{start_dt:%m-%d %H:%M} ~ {end_dt:%m-%d %H:%M}（每条随机）")
        else:
            self._log(f"已添加 {len(targets)} 条发布任务 | 时间: {start_dt:%Y-%m-%d %H:%M}")
        self._ui.lineEdit_pub_file.clear()
        self._ui.lineEdit_pub_title.clear()
        self._ui.lineEdit_pub_desc.clear()

    def _import_jobs_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel任务文件", SCRIPT_DIR,
            "Excel Files (*.xlsx *.xls)")
        if not path:
            return
        try:
            count = self._scheduler.import_from_excel(path)
            self._log(f"从Excel导入了 {count} 条任务")
            QMessageBox.information(self, "导入成功", f"成功导入 {count} 条发布任务")
        except Exception as e:
            self._log(f"导入失败: {e}")
            QMessageBox.warning(self, "导入失败", str(e))

    def _start_scheduler(self):
        jobs = self._scheduler.get_jobs()
        pending = [j for j in jobs if j.status == PublishJob.STATUS_PENDING]
        if not pending:
            QMessageBox.warning(self, "提示", "没有待发布的任务")
            return
        # 确保引擎已启动
        if not self._scheduler.engine._running:
            self._scheduler.engine.start()
        self._scheduler.start()
        self._ui.button_start_scheduler.setEnabled(False)
        self._ui.button_stop_scheduler.setEnabled(True)
        self._log(f"定时发布已启动，待发布 {len(pending)} 条")

    def _stop_scheduler(self):
        if self._scheduler:
            self._scheduler.stop()
        self._ui.button_start_scheduler.setEnabled(True)
        self._ui.button_stop_scheduler.setEnabled(False)
        self._log("定时发布已停止")

    def _delete_selected_job(self):
        row = self._ui.table_jobs.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的任务")
            return
        jobs = self._scheduler.get_jobs()
        if row < len(jobs):
            job = jobs[row]
            self._scheduler.remove_job(job.job_id)
            self._log(f"已删除任务: {job.file}")

    def _clear_finished_jobs(self):
        jobs = self._scheduler.get_jobs()
        for j in jobs:
            if j.status in (PublishJob.STATUS_SUCCESS, PublishJob.STATUS_FAILED):
                self._scheduler.remove_job(j.job_id)
        self._log("已清空已完成的任务")

    def _refresh_jobs_table(self):
        if not self._scheduler:
            return
        jobs = self._scheduler.get_jobs()
        jt = self._ui.table_jobs
        jt.setRowCount(len(jobs))

        type_cn = {"picture": "图文", "video": "视频"}
        status_cn = {
            "pending": "等待中", "running": "发布中",
            "success": "成功", "failed": "失败",
        }
        status_color = {
            "pending": "#FF9800", "running": "#1976D2",
            "success": "#4CAF50", "failed": "#F44336",
        }

        for i, job in enumerate(jobs):
            dev_label = f"{job.node_name}/{job.device_name}" if job.node_name else job.device_name
            jt.setItem(i, 0, QtWidgets.QTableWidgetItem(dev_label))
            jt.setItem(i, 1, QtWidgets.QTableWidgetItem(
                type_cn.get(job.media_type, job.media_type)))
            jt.setItem(i, 2, QtWidgets.QTableWidgetItem(job.file))
            st = job.scheduled_time
            st_str = st.strftime("%Y-%m-%d %H:%M:%S") if hasattr(st, "strftime") else str(st)
            jt.setItem(i, 3, QtWidgets.QTableWidgetItem(st_str))
            jt.setItem(i, 4, QtWidgets.QTableWidgetItem(job.title))
            status_item = QtWidgets.QTableWidgetItem(
                status_cn.get(job.status, job.status))
            status_item.setForeground(
                QColor(status_color.get(job.status, "#333")))
            jt.setItem(i, 5, status_item)
            jt.setItem(i, 6, QtWidgets.QTableWidgetItem(job.message))

    # ═══════════════════════════════════════════════
    # 配置管理
    # ═══════════════════════════════════════════════

    def _save_nurture_config(self):
        cfg = self._build_nurture_config()
        path, _ = QFileDialog.getSaveFileName(
            self, "保存养号配置", NURTURE_CONFIG_FILE,
            "JSON Files (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self._log(f"配置已保存: {path}")

    def _load_nurture_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "加载养号配置", SCRIPT_DIR,
            "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._apply_config_to_ui(cfg)
            self._log(f"配置已加载: {path}")
        except Exception as e:
            self._log(f"加载配置失败: {e}")

    def _reset_nurture_config(self):
        self._apply_config_to_ui(DEFAULT_NURTURE_CONFIG)
        self._log("已恢复默认配置")

    def _load_saved_config(self):
        if os.path.exists(NURTURE_CONFIG_FILE):
            try:
                with open(NURTURE_CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._apply_config_to_ui(cfg)
            except Exception:
                pass

    # ═══════════════════════════════════════════════
    # 在线更新
    # ═══════════════════════════════════════════════

    def _check_update(self):
        self._log(f"检查更新中...（当前 v{VERSION}）")
        self._ui.button_check_update.setEnabled(False)
        self._updater.check_async(lambda r: self._signal_update_result.emit(r))

    def _on_update_result(self, result):
        status = result.get("status")

        # 下载完成的结果
        if status == "downloaded":
            self._ui.button_check_update.setEnabled(True)
            if not result.get("ok"):
                self._log(f"更新失败: {result.get('message')}")
                QMessageBox.warning(self, "更新失败", f"下载失败:\n{result.get('message')}")
                return
            self._log("更新已下载，即将重启应用")
            import subprocess
            try:
                subprocess.Popen(["cmd", "/c", "start", "", result.get("message")],
                                 shell=False)
                QApplication.quit()
            except Exception as e:
                self._log(f"启动更新脚本失败: {e}")
                QMessageBox.warning(self, "更新", f"无法启动更新脚本: {e}")
            return

        self._ui.button_check_update.setEnabled(True)

        if status == "error":
            self._log(f"检查更新失败: {result.get('message')}")
            QMessageBox.warning(self, "检查更新", result.get("message", "未知错误"))
            return

        if status == "latest":
            self._log(result.get("message", "已是最新版本"))
            QMessageBox.information(self, "检查更新", f"当前已是最新版本 v{VERSION}")
            return

        # status == available
        remote_version = result.get("remote_version", "")
        changelog = result.get("changelog", "")
        files = result.get("files", [])
        self._log(f"发现新版本 v{remote_version}（{len(files)} 个文件）")

        msg = f"发现新版本 v{remote_version}（当前 v{VERSION}）\n"
        if changelog:
            msg += f"\n更新内容:\n{changelog}\n"
        msg += f"\n共 {len(files)} 个文件需更新。点击 OK 下载并自动重启。"
        reply = QMessageBox.question(
            self, "发现新版本", msg,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok)
        if reply != QMessageBox.StandardButton.Ok:
            return

        self._log("开始下载更新...")
        self._ui.button_check_update.setEnabled(False)
        self._updater.download_and_apply(
            remote_version, files,
            lambda ok, m: self._signal_update_result.emit(
                {"status": "downloaded", "ok": ok, "message": m}))

    # ═══════════════════════════════════════════════
    # 节点管理（多台电脑）
    # ═══════════════════════════════════════════════

    def _refresh_nodes_table(self):
        nodes = load_nodes()
        nt = self._ui.table_nodes
        nt.setRowCount(len(nodes))
        for i, node in enumerate(nodes):
            name = node.get("name", "")
            nt.setItem(i, 0, QtWidgets.QTableWidgetItem(name))
            nt.setItem(i, 1, QtWidgets.QTableWidgetItem(node.get("host", "")))
            nt.setItem(i, 2, QtWidgets.QTableWidgetItem(str(node.get("port", 9912))))
            # 状态列：显示真实连接情况
            st = self._node_status.get(name)
            if st is None:
                status_item = QtWidgets.QTableWidgetItem("未刷新")
                status_item.setForeground(QColor("#888"))
            elif st.get("online"):
                status_item = QtWidgets.QTableWidgetItem(
                    f"在线 · {st.get('device_count', 0)}台设备")
                status_item.setForeground(QColor("#4CAF50"))
            else:
                status_item = QtWidgets.QTableWidgetItem("离线")
                status_item.setForeground(QColor("#F44336"))
            nt.setItem(i, 3, status_item)

    def _refresh_node_status(self):
        """后台查询所有节点连接状态，更新表格"""
        def _work():
            try:
                self._node_status = self._get_dm().get_node_status()
            except Exception as e:
                self._signal_log.emit(f"刷新节点状态失败: {e}")
            self._signal_refresh_nodes.emit()
        threading.Thread(target=_work, daemon=True).start()

    def _add_node(self):
        name = self._ui.lineEdit_node_name.text().strip()
        host = self._ui.lineEdit_host.text().strip()
        port = self._ui.spin_port.value()
        if not name or not host:
            QMessageBox.warning(self, "提示", "请填写节点名称和 IP 地址")
            return
        nodes = load_nodes()
        # 去重（同名或同 IP:端口）
        for n in nodes:
            if n.get("name") == name:
                QMessageBox.warning(self, "提示", f"节点名 '{name}' 已存在")
                return
            if n.get("host") == host and n.get("port") == port:
                QMessageBox.warning(self, "提示", f"{host}:{port} 已存在")
                return
        nodes.append({"name": name, "host": host, "port": port})
        save_nodes(nodes)
        if self._node_manager:
            self._node_manager.set_nodes(nodes)
        self._refresh_nodes_table()
        self._log(f"已添加节点: {name} ({host}:{port})")
        self._ui.lineEdit_node_name.clear()
        self._ui.lineEdit_host.clear()

    def _delete_node(self):
        row = self._ui.table_nodes.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的节点")
            return
        nodes = load_nodes()
        if row >= len(nodes):
            return
        node = nodes[row]
        if node.get("name") == "本机":
            QMessageBox.warning(self, "提示", "本机节点不可删除")
            return
        nodes.pop(row)
        save_nodes(nodes)
        if self._node_manager:
            self._node_manager.set_nodes(nodes)
        self._refresh_nodes_table()
        self._log(f"已删除节点: {node.get('name')}")

    def _test_connection(self):
        """测试连接：填了IP=测该待添加地址；没填=刷新所有节点状态到表格"""
        host = self._ui.lineEdit_host.text().strip()
        port = self._ui.spin_port.value()

        if host:
            # 测试输入框里这个待添加的节点
            self._log(f"测试连接 {host}:{port} ...")

            def _test_one():
                from .nodes import MultiNodeManager
                count = MultiNodeManager().test_node(host, port)
                if count >= 0:
                    self._signal_log.emit(f"连接成功! {host}:{port} 找到 {count} 台设备，可以添加")
                else:
                    self._signal_log.emit(
                        f"连接失败: 无法连接 {host}:{port}"
                        f"（确认对方电脑开着 iMouse、和本机同一局域网、防火墙放行9912）")

            threading.Thread(target=_test_one, daemon=True).start()
        else:
            # 刷新所有已配置节点的状态
            self._log("刷新所有节点连接状态...")
            self._refresh_node_status()

    # ═══════════════════════════════════════════════
    # 用户名管理
    # ═══════════════════════════════════════════════

    def _prompt_username_if_needed(self):
        user_info = load_user_info()
        if user_info.get("username"):
            return
        name, ok = QInputDialog.getText(
            self, "欢迎使用 iMouse 自动化中心",
            "请输入你的用户名（名字/工号），用于标识错误来源：",
        )
        if ok and name.strip():
            self._reporter.username = name.strip()
            self._update_username_display()
            self._log(f"用户名已设置: {name.strip()}")
        else:
            self._reporter.username = "未命名用户"
            self._update_username_display()

    def _save_username(self):
        name = self._ui.lineEdit_username.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入用户名")
            return
        self._reporter.username = name
        self._update_username_display()
        self._log(f"用户名已更新: {name}")

    def _update_username_display(self):
        name = self._reporter.username
        self._ui.label_user.setText(f"  {name}  ")
        self._ui.lineEdit_username.setText(name if name != "未设置" else "")
        self.setWindowTitle(f"iMouse Pro 自动化中心 - {name}")

    # ═══════════════════════════════════════════════
    # 错误上报
    # ═══════════════════════════════════════════════

    def _test_email(self):
        self._log("正在发送测试消息到飞书...")
        self._ui.button_test_email.setEnabled(False)

        def _do_test():
            ok, msg = self._reporter.send_test()
            self._signal_log.emit(f"测试: {msg}")
            self._ui.button_test_email.setEnabled(True)

        threading.Thread(target=_do_test, daemon=True).start()

    def _global_except_hook(self, exc_type, exc_value, exc_tb):
        """全局未捕获异常 -> 上报邮件"""
        try:
            self._reporter.report_error(exc_value, context="全局未捕获异常")
        except Exception:
            pass
        if self._orig_excepthook:
            self._orig_excepthook(exc_type, exc_value, exc_tb)

    # ═══════════════════════════════════════════════
    # 窗口事件
    # ═══════════════════════════════════════════════

    def closeEvent(self, event):
        if self._is_running:
            reply = QMessageBox.question(
                self, "确认退出",
                "养号任务正在运行，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            self._stop_nurture()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = AutomationApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
