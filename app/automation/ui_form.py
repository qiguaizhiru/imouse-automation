# -*- coding: utf-8 -*-
# iMouse Pro 自动化中心 - UI 布局

from PyQt6 import QtCore, QtWidgets


class Ui_AutomationWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("AutomationWindow")
        MainWindow.resize(1300, 800)
        MainWindow.setMinimumSize(QtCore.QSize(1100, 700))
        MainWindow.setWindowTitle("iMouse Pro 自动化中心")
        MainWindow.setStyleSheet("""
            QMainWindow { background-color: #F5F5F5; }
            QGroupBox { font-weight: bold; border: 1px solid #CCCCCC; border-radius: 4px;
                        margin-top: 8px; padding-top: 12px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { padding: 5px 12px; border: 1px solid #BBBBBB; border-radius: 3px;
                          background-color: #FFFFFF; min-height: 24px; }
            QPushButton:hover { background-color: #E3F2FD; border-color: #2196F3; }
            QPushButton:pressed { background-color: #BBDEFB; }
            QPushButton:disabled { background-color: #E0E0E0; color: #999; border-color: #CCC; }
            QTableWidget { border: 1px solid #CCCCCC; gridline-color: #E0E0E0;
                         selection-background-color: #1565C0; selection-color: white;
                         alternate-row-colors: true; }
            QTableWidget::item:alternate { background-color: #FAFAFA; }
            QHeaderView::section { background-color: #1976D2; color: white; padding: 4px;
                                   border: none; font-weight: bold; }
            QTextEdit { border: 1px solid #CCCCCC; background-color: #1A1A2E; color: #00FF00;
                        font-family: Consolas, monospace; font-size: 12px; }
            QTabWidget::pane { border: 1px solid #CCCCCC; background: white; }
            QTabBar::tab { padding: 8px 20px; border: 1px solid #CCCCCC;
                           border-bottom: none; border-radius: 4px 4px 0 0;
                           background: #E8E8E8; margin-right: 2px; }
            QTabBar::tab:selected { background: white; border-bottom: 2px solid #1976D2;
                                    font-weight: bold; }
            QTabBar::tab:hover { background: #BBDEFB; }
            QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox {
                border: 1px solid #CCCCCC; border-radius: 3px; padding: 3px; background: white; }
            QCheckBox { spacing: 5px; }
            QSlider::groove:horizontal { height: 6px; background: #DDD; border-radius: 3px; }
            QSlider::handle:horizontal { width: 16px; height: 16px; margin: -5px 0;
                background: #1976D2; border-radius: 8px; }
            QSlider::sub-page:horizontal { background: #1976D2; border-radius: 3px; }
        """)

        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        main_layout = QtWidgets.QHBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ═══════════════════════════════════════════
        # 左侧面板: 标题 + 设备列表 + 日志
        # ═══════════════════════════════════════════
        left_panel = QtWidgets.QVBoxLayout()
        left_panel.setSpacing(6)

        # ── 标题栏 ──
        title_bar = QtWidgets.QHBoxLayout()
        self.label_title = QtWidgets.QLabel("iMouse Pro 自动化中心")
        self.label_title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #1565C0; padding: 4px;")
        title_bar.addWidget(self.label_title)
        self.label_version = QtWidgets.QLabel("v1.0.0")
        self.label_version.setStyleSheet("color: #666; font-size: 12px; padding: 0 6px;")
        title_bar.addWidget(self.label_version)
        self.button_check_update = QtWidgets.QPushButton("检查更新")
        self.button_check_update.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; font-size: 12px; "
            "padding: 4px 10px; border: none; border-radius: 3px; }"
            "QPushButton:hover { background-color: #388E3C; }"
            "QPushButton:disabled { background-color: #A5D6A7; }")
        title_bar.addWidget(self.button_check_update)
        title_bar.addStretch()
        self.label_user = QtWidgets.QLabel("")
        self.label_user.setStyleSheet(
            "color: #1565C0; font-weight: bold; font-size: 12px; padding: 4px; "
            "background: #E3F2FD; border-radius: 3px;")
        title_bar.addWidget(self.label_user)
        self.label_status = QtWidgets.QLabel("未连接")
        self.label_status.setStyleSheet("color: #F44336; font-weight: bold; padding: 4px;")
        title_bar.addWidget(self.label_status)
        left_panel.addLayout(title_bar)

        # ── 设备列表头 ──
        dev_header = QtWidgets.QHBoxLayout()
        dev_header_label = QtWidgets.QLabel("设备列表")
        dev_header_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        dev_header.addWidget(dev_header_label)
        dev_header.addStretch()

        self.button_refresh = QtWidgets.QPushButton("刷新设备")
        self.button_refresh.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; font-weight: bold; "
            "padding: 5px 14px; border: none; border-radius: 3px; }")
        dev_header.addWidget(self.button_refresh)

        self.button_select_all = QtWidgets.QPushButton("全选")
        self.button_select_all.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; padding: 5px 10px; "
            "border: none; border-radius: 3px; }")
        dev_header.addWidget(self.button_select_all)

        self.button_select_none = QtWidgets.QPushButton("取消")
        self.button_select_none.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; padding: 5px 10px; "
            "border: none; border-radius: 3px; }")
        dev_header.addWidget(self.button_select_none)
        left_panel.addLayout(dev_header)

        # ── 设备表格 (带勾选) ──
        self.table_devices = QtWidgets.QTableWidget()
        self.table_devices.setColumnCount(6)
        self.table_devices.setHorizontalHeaderLabels(
            ["", "节点", "设备名称", "设备ID", "型号", "状态"])
        self.table_devices.setColumnWidth(0, 30)
        self.table_devices.setColumnWidth(1, 80)
        self.table_devices.setColumnWidth(2, 105)
        self.table_devices.setColumnWidth(3, 95)
        self.table_devices.setColumnWidth(4, 125)
        self.table_devices.setColumnWidth(5, 55)
        self.table_devices.horizontalHeader().setStretchLastSection(True)
        self.table_devices.verticalHeader().hide()
        self.table_devices.setAlternatingRowColors(True)
        self.table_devices.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_devices.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        left_panel.addWidget(self.table_devices, stretch=3)

        # ── 日志区 ──
        log_header = QtWidgets.QHBoxLayout()
        log_label = QtWidgets.QLabel("运行日志")
        log_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 4px;")
        log_header.addWidget(log_label)
        log_header.addStretch()
        self.button_clear_log = QtWidgets.QPushButton("清空")
        self.button_clear_log.setStyleSheet(
            "QPushButton { padding: 2px 8px; font-size: 11px; }")
        log_header.addWidget(self.button_clear_log)
        left_panel.addLayout(log_header)

        self.textEdit_log = QtWidgets.QTextEdit()
        self.textEdit_log.setReadOnly(True)
        left_panel.addWidget(self.textEdit_log, stretch=2)

        main_layout.addLayout(left_panel, stretch=4)

        # ═══════════════════════════════════════════
        # 右侧面板: Tab 页
        # ═══════════════════════════════════════════
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(6)

        self.tabWidget = QtWidgets.QTabWidget()

        # ══════════════ Tab 1: 自动养号 ══════════════
        self.tab_nurture = QtWidgets.QWidget()
        tab1 = QtWidgets.QVBoxLayout(self.tab_nurture)
        tab1.setContentsMargins(12, 12, 12, 12)
        tab1.setSpacing(10)

        # ── 基本设置 ──
        basic_group = QtWidgets.QGroupBox("基本设置")
        basic_layout = QtWidgets.QGridLayout(basic_group)
        basic_layout.setSpacing(8)

        basic_layout.addWidget(QtWidgets.QLabel("养号时长(分钟):"), 0, 0)
        self.spin_duration = QtWidgets.QSpinBox()
        self.spin_duration.setRange(0, 1440)
        self.spin_duration.setValue(30)
        self.spin_duration.setSpecialValueText("无限")
        self.spin_duration.setToolTip("0 = 无限运行直到手动停止")
        basic_layout.addWidget(self.spin_duration, 0, 1)

        basic_layout.addWidget(QtWidgets.QLabel("每轮视频数:"), 0, 2)
        self.spin_videos = QtWidgets.QSpinBox()
        self.spin_videos.setRange(1, 200)
        self.spin_videos.setValue(15)
        basic_layout.addWidget(self.spin_videos, 0, 3)

        basic_layout.addWidget(QtWidgets.QLabel("总轮次(0=不限):"), 0, 4)
        self.spin_sessions = QtWidgets.QSpinBox()
        self.spin_sessions.setRange(0, 100)
        self.spin_sessions.setValue(0)
        self.spin_sessions.setSpecialValueText("不限")
        basic_layout.addWidget(self.spin_sessions, 0, 5)

        # 随机时长（开启后每次养号时长在范围内随机，每次不同）
        self.check_random_duration = QtWidgets.QCheckBox("随机时长")
        self.check_random_duration.setToolTip(
            "勾选后忽略上面的固定时长，每次开始养号在下面范围内随机一个时长")
        basic_layout.addWidget(self.check_random_duration, 1, 0)

        self.label_rand_dur = QtWidgets.QLabel("范围(分钟):")
        basic_layout.addWidget(self.label_rand_dur, 1, 1)
        rand_dur_box = QtWidgets.QHBoxLayout()
        self.spin_duration_min = QtWidgets.QSpinBox()
        self.spin_duration_min.setRange(1, 1440)
        self.spin_duration_min.setValue(20)
        rand_dur_box.addWidget(self.spin_duration_min)
        rand_dur_box.addWidget(QtWidgets.QLabel("~"))
        self.spin_duration_max = QtWidgets.QSpinBox()
        self.spin_duration_max.setRange(1, 1440)
        self.spin_duration_max.setValue(60)
        rand_dur_box.addWidget(self.spin_duration_max)
        basic_layout.addLayout(rand_dur_box, 1, 2, 1, 2)

        tab1.addWidget(basic_group)

        # ── 观看行为 ──
        watch_group = QtWidgets.QGroupBox("观看行为")
        watch_layout = QtWidgets.QGridLayout(watch_group)
        watch_layout.setSpacing(8)

        watch_layout.addWidget(QtWidgets.QLabel("观看时长(秒):"), 0, 0)
        self.spin_watch_min = QtWidgets.QSpinBox()
        self.spin_watch_min.setRange(1, 60)
        self.spin_watch_min.setValue(3)
        watch_layout.addWidget(self.spin_watch_min, 0, 1)
        watch_layout.addWidget(QtWidgets.QLabel("~"), 0, 2)
        self.spin_watch_max = QtWidgets.QSpinBox()
        self.spin_watch_max.setRange(1, 120)
        self.spin_watch_max.setValue(30)
        watch_layout.addWidget(self.spin_watch_max, 0, 3)

        watch_layout.addWidget(QtWidgets.QLabel("长观看概率:"), 0, 4)
        self.spin_long_watch = QtWidgets.QDoubleSpinBox()
        self.spin_long_watch.setRange(0, 1)
        self.spin_long_watch.setSingleStep(0.05)
        self.spin_long_watch.setValue(0.20)
        self.spin_long_watch.setDecimals(2)
        watch_layout.addWidget(self.spin_long_watch, 0, 5)

        watch_layout.addWidget(QtWidgets.QLabel("完整观看概率:"), 1, 0)
        self.spin_full_watch = QtWidgets.QDoubleSpinBox()
        self.spin_full_watch.setRange(0, 1)
        self.spin_full_watch.setSingleStep(0.05)
        self.spin_full_watch.setValue(0.10)
        self.spin_full_watch.setDecimals(2)
        watch_layout.addWidget(self.spin_full_watch, 1, 1)

        tab1.addWidget(watch_group)

        # ── 简单模式开关（安全）──
        self.check_simple_mode = QtWidgets.QCheckBox(
            "简单模式（推荐）：只做 看视频 + 上滑 + 点赞，不切页面，最不容易跑到购物页/相册")
        self.check_simple_mode.setChecked(True)
        self.check_simple_mode.setStyleSheet("font-weight: bold; color: #2E7D32;")
        tab1.addWidget(self.check_simple_mode)

        # ── 互动设置 ──
        interact_group = QtWidgets.QGroupBox("互动概率（简单模式下只有点赞生效，其余需取消简单模式）")
        interact_layout = QtWidgets.QGridLayout(interact_group)
        interact_layout.setSpacing(8)

        self._interact_spins = {}
        interact_items = [
            ("like_chance", "点赞概率:", 0.8, 0, 0),
            ("follow_chance", "关注概率:", 0.03, 0, 2),
            ("comment_chance", "评论概率:", 0.00, 0, 4),
            ("profile_view_chance", "查看主页:", 0.05, 1, 0),
            ("scroll_comments_chance", "浏览评论:", 0.05, 1, 2),
            ("switch_tab_chance", "切换Tab:", 0.03, 1, 4),
        ]
        for key, label, default, row, col in interact_items:
            interact_layout.addWidget(QtWidgets.QLabel(label), row, col)
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(0, 1)
            spin.setSingleStep(0.01)
            spin.setValue(default)
            spin.setDecimals(2)
            interact_layout.addWidget(spin, row, col + 1)
            self._interact_spins[key] = spin

        tab1.addWidget(interact_group)

        # ── 搜索设置 ──
        search_group = QtWidgets.QGroupBox("搜索行为")
        search_layout = QtWidgets.QGridLayout(search_group)
        search_layout.setSpacing(8)

        self.check_search = QtWidgets.QCheckBox("启用搜索")
        self.check_search.setChecked(True)
        search_layout.addWidget(self.check_search, 0, 0)

        search_layout.addWidget(QtWidgets.QLabel("每隔N个视频:"), 0, 1)
        self.spin_search_interval = QtWidgets.QSpinBox()
        self.spin_search_interval.setRange(5, 100)
        self.spin_search_interval.setValue(20)
        search_layout.addWidget(self.spin_search_interval, 0, 2)

        search_layout.addWidget(QtWidgets.QLabel("搜索关键词(逗号分隔):"), 1, 0, 1, 1)
        self.lineEdit_keywords = QtWidgets.QLineEdit()
        self.lineEdit_keywords.setPlaceholderText("例: funny cats, cooking, dance")
        search_layout.addWidget(self.lineEdit_keywords, 1, 1, 1, 3)

        tab1.addWidget(search_group)

        # ── 休息设置 ──
        rest_group = QtWidgets.QGroupBox("休息设置")
        rest_layout = QtWidgets.QHBoxLayout(rest_group)

        self.check_rest = QtWidgets.QCheckBox("启用休息")
        self.check_rest.setChecked(True)
        rest_layout.addWidget(self.check_rest)

        rest_layout.addWidget(QtWidgets.QLabel("每隔N个视频:"))
        self.spin_rest_interval = QtWidgets.QSpinBox()
        self.spin_rest_interval.setRange(5, 200)
        self.spin_rest_interval.setValue(30)
        rest_layout.addWidget(self.spin_rest_interval)

        rest_layout.addWidget(QtWidgets.QLabel("休息(秒):"))
        self.spin_rest_min = QtWidgets.QSpinBox()
        self.spin_rest_min.setRange(1, 300)
        self.spin_rest_min.setValue(10)
        rest_layout.addWidget(self.spin_rest_min)
        rest_layout.addWidget(QtWidgets.QLabel("~"))
        self.spin_rest_max = QtWidgets.QSpinBox()
        self.spin_rest_max.setRange(1, 600)
        self.spin_rest_max.setValue(30)
        rest_layout.addWidget(self.spin_rest_max)

        rest_layout.addStretch()
        tab1.addWidget(rest_group)

        # ── 操作按钮 ──
        btn_layout = QtWidgets.QHBoxLayout()

        self.button_start_nurture = QtWidgets.QPushButton("开始养号")
        self.button_start_nurture.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "font-size: 15px; padding: 12px; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: #388E3C; }"
            "QPushButton:disabled { background-color: #A5D6A7; }")
        btn_layout.addWidget(self.button_start_nurture, stretch=2)

        self.button_pause_nurture = QtWidgets.QPushButton("暂停")
        self.button_pause_nurture.setEnabled(False)
        self.button_pause_nurture.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; "
            "font-size: 14px; padding: 12px; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: #F57C00; }"
            "QPushButton:disabled { background-color: #FFCC80; }")
        btn_layout.addWidget(self.button_pause_nurture, stretch=1)

        self.button_stop_nurture = QtWidgets.QPushButton("停止养号")
        self.button_stop_nurture.setEnabled(False)
        self.button_stop_nurture.setStyleSheet(
            "QPushButton { background-color: white; color: #F44336; font-weight: bold; "
            "font-size: 14px; padding: 12px; border: 2px solid #F44336; border-radius: 4px; }"
            "QPushButton:hover { background-color: #FFEBEE; }"
            "QPushButton:disabled { color: #EF9A9A; border-color: #EF9A9A; }")
        btn_layout.addWidget(self.button_stop_nurture, stretch=1)

        tab1.addLayout(btn_layout)

        # ── 进度显示 ──
        progress_group = QtWidgets.QGroupBox("运行状态")
        progress_layout = QtWidgets.QVBoxLayout(progress_group)

        self.table_progress = QtWidgets.QTableWidget()
        self.table_progress.setColumnCount(7)
        self.table_progress.setHorizontalHeaderLabels(
            ["设备", "状态", "已观看", "已点赞", "已关注", "已搜索", "耗时"])
        self.table_progress.horizontalHeader().setStretchLastSection(True)
        self.table_progress.verticalHeader().hide()
        self.table_progress.setAlternatingRowColors(True)
        self.table_progress.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_progress.setMaximumHeight(180)
        progress_layout.addWidget(self.table_progress)

        tab1.addWidget(progress_group)

        tab1.addStretch()
        self.tabWidget.addTab(self.tab_nurture, "自动养号")

        # ══════════════ Tab 2: 定时发布 ══════════════
        self.tab_publish = QtWidgets.QWidget()
        tabp = QtWidgets.QVBoxLayout(self.tab_publish)
        tabp.setContentsMargins(12, 12, 12, 12)
        tabp.setSpacing(10)

        # ── 添加任务 ──
        add_group = QtWidgets.QGroupBox("添加发布任务")
        add_layout = QtWidgets.QGridLayout(add_group)
        add_layout.setSpacing(8)

        add_layout.addWidget(QtWidgets.QLabel("设备名称:"), 0, 0)
        self.lineEdit_pub_device = QtWidgets.QLineEdit()
        self.lineEdit_pub_device.setPlaceholderText("设备名，留空=对所有勾选设备")
        add_layout.addWidget(self.lineEdit_pub_device, 0, 1)

        add_layout.addWidget(QtWidgets.QLabel("类型:"), 0, 2)
        self.combo_pub_type = QtWidgets.QComboBox()
        self.combo_pub_type.addItems(["图文", "视频"])
        add_layout.addWidget(self.combo_pub_type, 0, 3)

        add_layout.addWidget(QtWidgets.QLabel("素材文件名:"), 1, 0)
        self.lineEdit_pub_file = QtWidgets.QLineEdit()
        self.lineEdit_pub_file.setPlaceholderText("不含扩展名，文件在 设备名 文件夹下")
        add_layout.addWidget(self.lineEdit_pub_file, 1, 1)

        add_layout.addWidget(QtWidgets.QLabel("发布时间:"), 1, 2)
        self.dateTime_pub = QtWidgets.QDateTimeEdit()
        self.dateTime_pub.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dateTime_pub.setCalendarPopup(True)
        add_layout.addWidget(self.dateTime_pub, 1, 3)

        # 随机时间（勾选后在 发布时间 ~ 结束时间 之间为每条任务随机一个时刻）
        self.check_random_time = QtWidgets.QCheckBox("随机时间")
        self.check_random_time.setToolTip(
            "勾选后，每条任务在「发布时间」到「结束时间」之间随机一个发布时刻，每条都不同")
        add_layout.addWidget(self.check_random_time, 2, 0)

        self.label_pub_end = QtWidgets.QLabel("结束时间:")
        add_layout.addWidget(self.label_pub_end, 2, 2)
        self.dateTime_pub_end = QtWidgets.QDateTimeEdit()
        self.dateTime_pub_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dateTime_pub_end.setCalendarPopup(True)
        add_layout.addWidget(self.dateTime_pub_end, 2, 3)

        add_layout.addWidget(QtWidgets.QLabel("音乐URL:"), 3, 0)
        self.lineEdit_pub_url = QtWidgets.QLineEdit()
        self.lineEdit_pub_url.setPlaceholderText("图文模式必填，视频可留空")
        add_layout.addWidget(self.lineEdit_pub_url, 3, 1, 1, 3)

        add_layout.addWidget(QtWidgets.QLabel("标题:"), 4, 0)
        self.lineEdit_pub_title = QtWidgets.QLineEdit()
        add_layout.addWidget(self.lineEdit_pub_title, 4, 1, 1, 3)

        add_layout.addWidget(QtWidgets.QLabel("描述标签:"), 5, 0)
        self.lineEdit_pub_desc = QtWidgets.QLineEdit()
        self.lineEdit_pub_desc.setPlaceholderText("#标签 描述内容")
        add_layout.addWidget(self.lineEdit_pub_desc, 5, 1, 1, 3)

        pub_add_btn_layout = QtWidgets.QHBoxLayout()
        self.button_add_job = QtWidgets.QPushButton("添加到任务列表")
        self.button_add_job.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; font-weight: bold; "
            "padding: 6px 14px; border: none; border-radius: 3px; }")
        pub_add_btn_layout.addWidget(self.button_add_job)

        self.button_import_jobs = QtWidgets.QPushButton("从Excel导入")
        self.button_import_jobs.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; font-weight: bold; "
            "padding: 6px 14px; border: none; border-radius: 3px; }")
        pub_add_btn_layout.addWidget(self.button_import_jobs)

        self.label_excel_fmt = QtWidgets.QLabel(
            "Excel列: devices | file | type | url | title | description | scheduled_time")
        self.label_excel_fmt.setStyleSheet("color: #888; font-size: 11px;")
        pub_add_btn_layout.addWidget(self.label_excel_fmt)
        pub_add_btn_layout.addStretch()
        add_layout.addLayout(pub_add_btn_layout, 6, 0, 1, 4)

        tabp.addWidget(add_group)

        # ── 任务列表 ──
        jobs_group = QtWidgets.QGroupBox("定时任务列表")
        jobs_layout = QtWidgets.QVBoxLayout(jobs_group)

        self.table_jobs = QtWidgets.QTableWidget()
        self.table_jobs.setColumnCount(8)
        self.table_jobs.setHorizontalHeaderLabels(
            ["设备", "类型", "素材", "发布时间", "标题", "状态", "信息", ""])
        self.table_jobs.setColumnWidth(0, 90)
        self.table_jobs.setColumnWidth(1, 50)
        self.table_jobs.setColumnWidth(2, 90)
        self.table_jobs.setColumnWidth(3, 140)
        self.table_jobs.setColumnWidth(5, 70)
        self.table_jobs.horizontalHeader().setStretchLastSection(True)
        self.table_jobs.verticalHeader().hide()
        self.table_jobs.setAlternatingRowColors(True)
        self.table_jobs.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        jobs_layout.addWidget(self.table_jobs)

        jobs_btn_layout = QtWidgets.QHBoxLayout()
        self.button_start_scheduler = QtWidgets.QPushButton("启动定时发布")
        self.button_start_scheduler.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "font-size: 14px; padding: 10px; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: #388E3C; }"
            "QPushButton:disabled { background-color: #A5D6A7; }")
        jobs_btn_layout.addWidget(self.button_start_scheduler, stretch=2)

        self.button_stop_scheduler = QtWidgets.QPushButton("停止")
        self.button_stop_scheduler.setEnabled(False)
        self.button_stop_scheduler.setStyleSheet(
            "QPushButton { background-color: white; color: #F44336; font-weight: bold; "
            "font-size: 14px; padding: 10px; border: 2px solid #F44336; border-radius: 4px; }"
            "QPushButton:disabled { color: #EF9A9A; border-color: #EF9A9A; }")
        jobs_btn_layout.addWidget(self.button_stop_scheduler, stretch=1)

        self.button_del_job = QtWidgets.QPushButton("删除选中")
        self.button_del_job.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; "
            "padding: 10px; border: none; border-radius: 4px; }")
        jobs_btn_layout.addWidget(self.button_del_job)

        self.button_clear_jobs = QtWidgets.QPushButton("清空已完成")
        jobs_btn_layout.addWidget(self.button_clear_jobs)

        jobs_layout.addLayout(jobs_btn_layout)
        tabp.addWidget(jobs_group)

        self.tabWidget.addTab(self.tab_publish, "定时发布")

        # ══════════════ Tab 3: 设置 ══════════════
        self.tab_settings = QtWidgets.QWidget()
        tab2 = QtWidgets.QVBoxLayout(self.tab_settings)
        tab2.setContentsMargins(12, 12, 12, 12)
        tab2.setSpacing(10)

        # ── 用户信息 ──
        user_group = QtWidgets.QGroupBox("用户信息")
        user_layout = QtWidgets.QHBoxLayout(user_group)

        user_layout.addWidget(QtWidgets.QLabel("用户名:"))
        self.lineEdit_username = QtWidgets.QLineEdit()
        self.lineEdit_username.setPlaceholderText("请输入你的名字/工号，用于标识错误来源")
        self.lineEdit_username.setMinimumWidth(200)
        user_layout.addWidget(self.lineEdit_username)

        self.button_save_username = QtWidgets.QPushButton("保存用户名")
        self.button_save_username.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "padding: 6px 14px; border: none; border-radius: 3px; }")
        user_layout.addWidget(self.button_save_username)

        user_layout.addStretch()
        tab2.addWidget(user_group)

        # ── 节点管理（多台电脑） ──
        node_group = QtWidgets.QGroupBox("节点管理（控制多台电脑）")
        node_v = QtWidgets.QVBoxLayout(node_group)

        node_hint = QtWidgets.QLabel(
            "每个节点 = 一台运行 iMouse 的电脑。要控制其他电脑：下方填它的【名称+局域网IP+端口9912】→"
            "点【测试】确认能连 → 点【添加节点】。添加后「状态」列显示每台在线/离线及设备数"
            "（点【测试】但IP留空=刷新所有节点状态）。其他电脑需开着 iMouse、与本机同一局域网。")
        node_hint.setStyleSheet("color: #888; font-size: 11px;")
        node_hint.setWordWrap(True)
        node_v.addWidget(node_hint)

        # 节点列表表格
        self.table_nodes = QtWidgets.QTableWidget()
        self.table_nodes.setColumnCount(4)
        self.table_nodes.setHorizontalHeaderLabels(["节点名称", "IP地址", "端口", "状态"])
        self.table_nodes.setColumnWidth(0, 120)
        self.table_nodes.setColumnWidth(1, 140)
        self.table_nodes.setColumnWidth(2, 70)
        self.table_nodes.horizontalHeader().setStretchLastSection(True)
        self.table_nodes.verticalHeader().hide()
        self.table_nodes.setAlternatingRowColors(True)
        self.table_nodes.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_nodes.setMaximumHeight(140)
        node_v.addWidget(self.table_nodes)

        # 添加节点行
        node_add = QtWidgets.QHBoxLayout()
        node_add.addWidget(QtWidgets.QLabel("名称:"))
        self.lineEdit_node_name = QtWidgets.QLineEdit()
        self.lineEdit_node_name.setPlaceholderText("如 电脑B")
        self.lineEdit_node_name.setMaximumWidth(100)
        node_add.addWidget(self.lineEdit_node_name)

        node_add.addWidget(QtWidgets.QLabel("IP:"))
        self.lineEdit_host = QtWidgets.QLineEdit()
        self.lineEdit_host.setPlaceholderText("192.168.1.x")
        self.lineEdit_host.setMaximumWidth(130)
        node_add.addWidget(self.lineEdit_host)

        node_add.addWidget(QtWidgets.QLabel("端口:"))
        self.spin_port = QtWidgets.QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(9912)
        self.spin_port.setMaximumWidth(80)
        node_add.addWidget(self.spin_port)

        self.button_test_conn = QtWidgets.QPushButton("测试")
        self.button_test_conn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border: none; "
            "border-radius: 3px; padding: 5px 12px; }")
        node_add.addWidget(self.button_test_conn)

        self.button_add_node = QtWidgets.QPushButton("添加节点")
        self.button_add_node.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "border: none; border-radius: 3px; padding: 5px 12px; }")
        node_add.addWidget(self.button_add_node)

        self.button_del_node = QtWidgets.QPushButton("删除选中")
        self.button_del_node.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; "
            "border: none; border-radius: 3px; padding: 5px 12px; }")
        node_add.addWidget(self.button_del_node)

        node_add.addStretch()
        node_v.addLayout(node_add)

        tab2.addWidget(node_group)

        # ── 错误上报 ──
        report_group = QtWidgets.QGroupBox("错误上报")
        report_layout = QtWidgets.QHBoxLayout(report_group)

        self.label_report_info = QtWidgets.QLabel(
            "运行出错时自动推送到飞书群通知管理员（已内置，无需配置）")
        self.label_report_info.setStyleSheet("color: #555; font-size: 12px;")
        report_layout.addWidget(self.label_report_info)

        report_layout.addStretch()

        self.button_test_email = QtWidgets.QPushButton("发送测试消息")
        self.button_test_email.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; "
            "padding: 6px 14px; border: none; border-radius: 3px; }")
        report_layout.addWidget(self.button_test_email)

        self.label_smtp_status = QtWidgets.QLabel("已启用")
        self.label_smtp_status.setStyleSheet(
            "color: #4CAF50; font-weight: bold; font-size: 12px; padding: 4px;")
        report_layout.addWidget(self.label_smtp_status)

        tab2.addWidget(report_group)

        # ── 配置导入导出 ──
        cfg_group = QtWidgets.QGroupBox("养号配置")
        cfg_layout = QtWidgets.QHBoxLayout(cfg_group)

        self.button_save_config = QtWidgets.QPushButton("保存当前配置")
        self.button_save_config.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; font-weight: bold; "
            "padding: 6px 14px; border: none; border-radius: 3px; }")
        cfg_layout.addWidget(self.button_save_config)

        self.button_load_config = QtWidgets.QPushButton("加载配置文件")
        self.button_load_config.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; font-weight: bold; "
            "padding: 6px 14px; border: none; border-radius: 3px; }")
        cfg_layout.addWidget(self.button_load_config)

        self.button_reset_config = QtWidgets.QPushButton("恢复默认")
        cfg_layout.addWidget(self.button_reset_config)

        cfg_layout.addStretch()
        tab2.addWidget(cfg_group)

        tab2.addStretch()
        self.tabWidget.addTab(self.tab_settings, "设置")

        right_panel.addWidget(self.tabWidget)
        main_layout.addLayout(right_panel, stretch=6)

        MainWindow.setCentralWidget(self.centralwidget)
