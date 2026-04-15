# -*- coding: utf-8 -*-
# iMouse Pro V2.0 - UI Form (iMouseXP style layout)

from PyQt6 import QtCore, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1280, 780)
        MainWindow.setMinimumSize(QtCore.QSize(1100, 700))
        MainWindow.setStyleSheet("""
            QMainWindow { background-color: #F5F5F5; }
            QGroupBox { font-weight: bold; border: 1px solid #CCCCCC; border-radius: 4px;
                        margin-top: 8px; padding-top: 12px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { padding: 5px 12px; border: 1px solid #BBBBBB; border-radius: 3px;
                          background-color: #FFFFFF; min-height: 24px; }
            QPushButton:hover { background-color: #E3F2FD; border-color: #2196F3; }
            QPushButton:pressed { background-color: #BBDEFB; }
            QTableView { border: 1px solid #CCCCCC; gridline-color: #E0E0E0;
                         selection-background-color: #1565C0; selection-color: white;
                         alternate-row-colors: true; }
            QTableView::item:alternate { background-color: #FAFAFA; }
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
            QSpinBox, QLineEdit, QComboBox { border: 1px solid #CCCCCC; border-radius: 3px;
                                              padding: 3px; background: white; }
        """)

        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # ===== Main horizontal layout =====
        main_layout = QtWidgets.QHBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ===== LEFT PANEL (device list + log) =====
        left_panel = QtWidgets.QVBoxLayout()
        left_panel.setSpacing(6)

        # -- Title bar --
        title_bar = QtWidgets.QHBoxLayout()
        self.label_title = QtWidgets.QLabel("iMouse Pro \u81ea\u52a8\u5316\u5de5\u5177 V2.0")
        self.label_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1565C0; padding: 4px;")
        title_bar.addWidget(self.label_title)
        title_bar.addStretch()
        self.button_reconnect = QtWidgets.QPushButton("\u91cd\u65b0\u8fde\u63a5")
        self.button_reconnect.setObjectName("button_reconnect")
        self.button_reconnect.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; font-weight: bold; "
            "padding: 6px 16px; border-radius: 3px; border: none; }")
        title_bar.addWidget(self.button_reconnect)
        self.label_status = QtWidgets.QLabel("\u5df2\u8fde\u63a5")
        self.label_status.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 4px;")
        title_bar.addWidget(self.label_status)
        left_panel.addLayout(title_bar)

        # -- Device list header --
        dev_header = QtWidgets.QHBoxLayout()
        dev_header_label = QtWidgets.QLabel("\u8bbe\u5907\u5217\u8868")
        dev_header_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        dev_header.addWidget(dev_header_label)
        dev_header.addStretch()

        self.button_get_device_list = QtWidgets.QPushButton("\u5237\u65b0\u8bbe\u5907")
        self.button_get_device_list.setObjectName("button_get_device_list")
        self.button_get_device_list.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; font-weight: bold; "
            "padding: 5px 14px; border: none; border-radius: 3px; }")
        dev_header.addWidget(self.button_get_device_list)

        self.button_select_invert = QtWidgets.QPushButton("\u53cd\u9009")
        self.button_select_invert.setObjectName("button_select_invert")
        self.button_select_invert.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; padding: 5px 10px; border: none; border-radius: 3px; }")
        dev_header.addWidget(self.button_select_invert)

        self.button_select_all = QtWidgets.QPushButton("\u5168\u9009")
        self.button_select_all.setObjectName("button_select_all")
        self.button_select_all.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; padding: 5px 10px; border: none; border-radius: 3px; }")
        dev_header.addWidget(self.button_select_all)
        left_panel.addLayout(dev_header)

        # -- Device table --
        self.tableView_devlist = QtWidgets.QTableView()
        self.tableView_devlist.setObjectName("tableView_devlist")
        self.tableView_devlist.setAlternatingRowColors(True)
        self.tableView_devlist.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView_devlist.horizontalHeader().setStretchLastSection(True)
        left_panel.addWidget(self.tableView_devlist, stretch=3)

        # -- Log area --
        log_label = QtWidgets.QLabel("\u64cd\u4f5c\u65e5\u5fd7")
        log_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 4px;")
        left_panel.addWidget(log_label)
        self.textEdit_log = QtWidgets.QTextEdit()
        self.textEdit_log.setObjectName("textEdit_log")
        self.textEdit_log.setReadOnly(True)
        left_panel.addWidget(self.textEdit_log, stretch=1)

        main_layout.addLayout(left_panel, stretch=5)

        # ===== RIGHT PANEL (tabs) =====
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(6)

        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.setObjectName("tabWidget")

        # ── Tab 1: TikTok Publish ──
        self.tab_publish = QtWidgets.QWidget()
        tab1_layout = QtWidgets.QVBoxLayout(self.tab_publish)
        tab1_layout.setContentsMargins(12, 12, 12, 12)
        tab1_layout.setSpacing(8)

        # Content type
        type_layout = QtWidgets.QHBoxLayout()
        type_layout.addWidget(QtWidgets.QLabel("\u5185\u5bb9\u7c7b\u578b:"))
        self.radioButton_img = QtWidgets.QRadioButton("\u56fe\u7247")
        self.radioButton_img.setChecked(True)
        self.radioButton_video = QtWidgets.QRadioButton("\u89c6\u9891")
        type_layout.addWidget(self.radioButton_img)
        type_layout.addWidget(self.radioButton_video)
        type_layout.addStretch()
        tab1_layout.addLayout(type_layout)

        # File select
        file_layout = QtWidgets.QHBoxLayout()
        file_layout.addWidget(QtWidgets.QLabel("\u7d20\u6750\u6587\u4ef6:"))
        self.lineEdit_file = QtWidgets.QLineEdit()
        self.lineEdit_file.setObjectName("lineEdit_file")
        file_layout.addWidget(self.lineEdit_file)
        self.button_select_file = QtWidgets.QPushButton("\u9009\u62e9")
        self.button_select_file.setObjectName("button_select_file")
        self.button_select_file.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border: none; border-radius: 3px; padding: 5px 14px; }")
        file_layout.addWidget(self.button_select_file)
        tab1_layout.addLayout(file_layout)

        # Music URL
        url_layout = QtWidgets.QHBoxLayout()
        url_layout.addWidget(QtWidgets.QLabel("\u97f3\u4e50URL:"))
        self.lineEdit_url = QtWidgets.QLineEdit()
        self.lineEdit_url.setObjectName("lineEdit_url")
        self.lineEdit_url.setPlaceholderText("(\u53ef\u9009)")
        url_layout.addWidget(self.lineEdit_url)
        tab1_layout.addLayout(url_layout)

        # Title
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.addWidget(QtWidgets.QLabel("\u6807  \u9898:"))
        self.lineEdit_title = QtWidgets.QLineEdit()
        self.lineEdit_title.setObjectName("lineEdit_title")
        title_layout.addWidget(self.lineEdit_title)
        tab1_layout.addLayout(title_layout)

        # Description
        desc_layout = QtWidgets.QHBoxLayout()
        desc_layout.addWidget(QtWidgets.QLabel("\u63cf\u8ff0\u6807\u7b7e:"))
        self.textEdit_desc = QtWidgets.QTextEdit()
        self.textEdit_desc.setObjectName("textEdit_desc")
        self.textEdit_desc.setMaximumHeight(80)
        desc_layout.addWidget(self.textEdit_desc)
        tab1_layout.addLayout(desc_layout)

        # Publish params
        param_group = QtWidgets.QGroupBox("\u53d1\u5e03\u53c2\u6570")
        param_layout = QtWidgets.QHBoxLayout(param_group)
        param_layout.addWidget(QtWidgets.QLabel("\u6b65\u9aa4\u95f4\u9694(\u79d2):"))
        self.spinBox_step = QtWidgets.QSpinBox()
        self.spinBox_step.setValue(3)
        self.spinBox_step.setMinimum(1)
        self.spinBox_step.setMaximum(30)
        param_layout.addWidget(self.spinBox_step)
        param_layout.addWidget(QtWidgets.QLabel("\u8bc6\u522b\u7b49\u5f85(\u79d2):"))
        self.spinBox_wait = QtWidgets.QSpinBox()
        self.spinBox_wait.setValue(15)
        self.spinBox_wait.setMinimum(1)
        self.spinBox_wait.setMaximum(120)
        param_layout.addWidget(self.spinBox_wait)
        param_layout.addWidget(QtWidgets.QLabel("\u8bbe\u5907\u95f4\u9694(\u79d2):"))
        self.spinBox_device_gap = QtWidgets.QSpinBox()
        self.spinBox_device_gap.setValue(2)
        self.spinBox_device_gap.setMinimum(0)
        self.spinBox_device_gap.setMaximum(60)
        param_layout.addWidget(self.spinBox_device_gap)
        tab1_layout.addWidget(param_group)

        # Excel import
        excel_group = QtWidgets.QGroupBox("Excel\u6279\u91cf\u5bfc\u5165")
        excel_layout = QtWidgets.QHBoxLayout(excel_group)
        self.button_import_excel = QtWidgets.QPushButton("\u5bfc\u5165Excel\u4efb\u52a1")
        self.button_import_excel.setObjectName("button_import_excel")
        self.button_import_excel.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; font-weight: bold; "
            "padding: 6px 14px; border: none; border-radius: 3px; }")
        excel_layout.addWidget(self.button_import_excel)
        excel_layout.addWidget(QtWidgets.QLabel("\u683c\u5f0f: devices | file | type | url | title | description | status"))
        excel_layout.addStretch()
        tab1_layout.addWidget(excel_group)

        # Publish buttons
        pub_btn_layout = QtWidgets.QHBoxLayout()
        self.button_open_tiktok = QtWidgets.QPushButton("\u4e00\u952e\u53d1\u5e03\u5230\u6240\u6709\u5728\u7ebf\u8bbe\u5907")
        self.button_open_tiktok.setObjectName("button_open_tiktok")
        self.button_open_tiktok.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; font-weight: bold; "
            "font-size: 14px; padding: 10px; border: none; border-radius: 4px; }")
        pub_btn_layout.addWidget(self.button_open_tiktok, stretch=2)

        self.button_publish_selected = QtWidgets.QPushButton("\u53d1\u5e03\u5230\u9009\u4e2d\u8bbe\u5907")
        self.button_publish_selected.setObjectName("button_publish_selected")
        self.button_publish_selected.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        pub_btn_layout.addWidget(self.button_publish_selected, stretch=1)

        self.button_stop_publish = QtWidgets.QPushButton("\u505c\u6b62\u53d1\u5e03")
        self.button_stop_publish.setObjectName("button_stop_publish")
        self.button_stop_publish.setStyleSheet(
            "QPushButton { background-color: white; color: #F44336; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: 2px solid #F44336; border-radius: 4px; }")
        pub_btn_layout.addWidget(self.button_stop_publish)
        tab1_layout.addLayout(pub_btn_layout)

        tab1_layout.addStretch()
        self.tabWidget.addTab(self.tab_publish, "\u4e00\u952e\u53d1\u5e03")

        # ── Tab 2: Device Manage ──
        self.tab_manage = QtWidgets.QWidget()
        tab2_layout = QtWidgets.QVBoxLayout(self.tab_manage)
        tab2_layout.setContentsMargins(12, 12, 12, 12)
        tab2_layout.setSpacing(10)

        # Device model
        model_layout = QtWidgets.QHBoxLayout()
        self.button_get_devicemodel_list = QtWidgets.QPushButton("\u83b7\u53d6\u652f\u6301\u578b\u53f7\u5217\u8868")
        self.button_get_devicemodel_list.setObjectName("button_get_devicemodel_list")
        model_layout.addWidget(self.button_get_devicemodel_list)
        model_layout.addStretch()
        tab2_layout.addLayout(model_layout)

        # USB / Hardware
        usb_layout = QtWidgets.QHBoxLayout()
        self.button_get_usb_list = QtWidgets.QPushButton("\u83b7\u53d6USB\u786c\u4ef6\u5217\u8868")
        self.button_get_usb_list.setObjectName("button_get_usb_list")
        usb_layout.addWidget(self.button_get_usb_list)
        self.comboBox_3 = QtWidgets.QComboBox()
        self.comboBox_3.setObjectName("comboBox_3")
        self.comboBox_3.setMinimumSize(QtCore.QSize(150, 0))
        usb_layout.addWidget(self.comboBox_3)
        self.button_set_dev_usb_id = QtWidgets.QPushButton("\u8bbe\u7f6e\u786c\u4ef6ID")
        self.button_set_dev_usb_id.setObjectName("button_set_dev_usb_id")
        usb_layout.addWidget(self.button_set_dev_usb_id)
        tab2_layout.addLayout(usb_layout)

        # Delete / Rename
        name_layout = QtWidgets.QHBoxLayout()
        self.button_del_dev = QtWidgets.QPushButton("\u5220\u9664\u8bbe\u5907")
        self.button_del_dev.setObjectName("button_del_dev")
        self.button_del_dev.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; border: none; border-radius: 3px; }")
        name_layout.addWidget(self.button_del_dev)
        self.lineEdit = QtWidgets.QLineEdit()
        self.lineEdit.setObjectName("lineEdit")
        self.lineEdit.setPlaceholderText("\u65b0\u8bbe\u5907\u540d\u79f0")
        name_layout.addWidget(self.lineEdit)
        self.button_set_dev_name = QtWidgets.QPushButton("\u4fee\u6539\u540d\u79f0")
        self.button_set_dev_name.setObjectName("button_set_dev_name")
        name_layout.addWidget(self.button_set_dev_name)
        tab2_layout.addLayout(name_layout)

        # Screenshot area
        screen_group = QtWidgets.QGroupBox("\u5c4f\u5e55")
        screen_layout = QtWidgets.QVBoxLayout(screen_group)

        ss_btn_layout = QtWidgets.QHBoxLayout()
        self.button_get_device_screenshot = QtWidgets.QPushButton("\u622a\u5c4f")
        self.button_get_device_screenshot.setObjectName("button_get_device_screenshot")
        ss_btn_layout.addWidget(self.button_get_device_screenshot)
        self.checkBox_gzip = QtWidgets.QCheckBox("\u538b\u7f29")
        self.checkBox_gzip.setObjectName("checkBox_gzip")
        ss_btn_layout.addWidget(self.checkBox_gzip)
        self.checkBox_binary = QtWidgets.QCheckBox("\u4e8c\u8fdb\u5236")
        self.checkBox_binary.setObjectName("checkBox_binary")
        ss_btn_layout.addWidget(self.checkBox_binary)
        self.checkBox_sync = QtWidgets.QCheckBox("\u540c\u6b65")
        self.checkBox_sync.setObjectName("checkBox_sync")
        ss_btn_layout.addWidget(self.checkBox_sync)
        self.button_loop_device_screenshot = QtWidgets.QPushButton("\u5faa\u73af\u622a\u5c4f")
        self.button_loop_device_screenshot.setObjectName("button_loop_device_screenshot")
        ss_btn_layout.addWidget(self.button_loop_device_screenshot)
        self.spinBox_delayed = QtWidgets.QSpinBox()
        self.spinBox_delayed.setObjectName("spinBox_delayed")
        self.spinBox_delayed.setMinimum(10)
        self.spinBox_delayed.setMaximum(1000)
        self.spinBox_delayed.setSingleStep(10)
        self.spinBox_delayed.setValue(100)
        self.spinBox_delayed.setSuffix(" \u6beb\u79d2")
        ss_btn_layout.addWidget(self.spinBox_delayed)
        self.button_stop_screenshot = QtWidgets.QPushButton("\u505c\u6b62\u622a\u53d6")
        self.button_stop_screenshot.setObjectName("button_stop_screenshot")
        ss_btn_layout.addWidget(self.button_stop_screenshot)
        screen_layout.addLayout(ss_btn_layout)

        self.graphicsView = QtWidgets.QGraphicsView()
        self.graphicsView.setObjectName("graphicsView")
        self.graphicsView.setMinimumHeight(300)
        screen_layout.addWidget(self.graphicsView)
        tab2_layout.addWidget(screen_group, stretch=1)

        # Keyboard
        key_group = QtWidgets.QGroupBox("\u952e\u76d8\u64cd\u4f5c")
        key_layout = QtWidgets.QHBoxLayout(key_group)
        key_layout.addWidget(QtWidgets.QLabel("\u8f93\u5165\u5b57\u7b26(\u4e0d\u652f\u6301\u4e2d\u6587):"))
        self.lineEdit_2 = QtWidgets.QLineEdit()
        self.lineEdit_2.setObjectName("lineEdit_2")
        key_layout.addWidget(self.lineEdit_2)
        self.button_send_key = QtWidgets.QPushButton("\u53d1\u9001")
        self.button_send_key.setObjectName("button_send_key")
        key_layout.addWidget(self.button_send_key)
        tab2_layout.addWidget(key_group)

        # Mouse
        mouse_group = QtWidgets.QGroupBox("\u9f20\u6807\u64cd\u4f5c")
        mouse_layout = QtWidgets.QVBoxLayout(mouse_group)

        mouse_row1 = QtWidgets.QHBoxLayout()
        self.radioButton_1 = QtWidgets.QRadioButton("\u5355\u51fb")
        self.radioButton_1.setObjectName("radioButton_1")
        self.radioButton_1.setChecked(True)
        mouse_row1.addWidget(self.radioButton_1)
        self.radioButton_3 = QtWidgets.QRadioButton("\u6309\u4e0b")
        self.radioButton_3.setObjectName("radioButton_3")
        mouse_row1.addWidget(self.radioButton_3)
        self.radioButton_5 = QtWidgets.QRadioButton("\u79fb\u52a8")
        self.radioButton_5.setObjectName("radioButton_5")
        mouse_row1.addWidget(self.radioButton_5)
        self.radioButton_2 = QtWidgets.QRadioButton("\u6ed1\u52a8")
        self.radioButton_2.setObjectName("radioButton_2")
        mouse_row1.addWidget(self.radioButton_2)
        self.radioButton_4 = QtWidgets.QRadioButton("\u5f39\u8d77")
        self.radioButton_4.setObjectName("radioButton_4")
        mouse_row1.addWidget(self.radioButton_4)
        self.radioButton_6 = QtWidgets.QRadioButton("\u590d\u4f4d")
        self.radioButton_6.setObjectName("radioButton_6")
        mouse_row1.addWidget(self.radioButton_6)
        self.button_mouse_events = QtWidgets.QPushButton("\u6267\u884c")
        self.button_mouse_events.setObjectName("button_mouse_events")
        self.button_mouse_events.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border: none; border-radius: 3px; padding: 5px 14px; }")
        mouse_row1.addWidget(self.button_mouse_events)
        mouse_layout.addLayout(mouse_row1)

        mouse_row2 = QtWidgets.QHBoxLayout()
        mouse_row2.addWidget(QtWidgets.QLabel("\u6309\u952e:"))
        self.comboBox_4 = QtWidgets.QComboBox()
        self.comboBox_4.setObjectName("comboBox_4")
        mouse_row2.addWidget(self.comboBox_4)
        mouse_row2.addWidget(QtWidgets.QLabel("X:"))
        self.lineEdit_3 = QtWidgets.QLineEdit()
        self.lineEdit_3.setObjectName("lineEdit_3")
        self.lineEdit_3.setMaximumWidth(60)
        mouse_row2.addWidget(self.lineEdit_3)
        mouse_row2.addWidget(QtWidgets.QLabel("Y:"))
        self.lineEdit_4 = QtWidgets.QLineEdit()
        self.lineEdit_4.setObjectName("lineEdit_4")
        self.lineEdit_4.setMaximumWidth(60)
        mouse_row2.addWidget(self.lineEdit_4)
        mouse_row2.addWidget(QtWidgets.QLabel("\u6ed1\u52a8\u65b9\u5411:"))
        self.comboBox_5 = QtWidgets.QComboBox()
        self.comboBox_5.setObjectName("comboBox_5")
        mouse_row2.addWidget(self.comboBox_5)
        mouse_layout.addLayout(mouse_row2)
        tab2_layout.addWidget(mouse_group)

        self.tabWidget.addTab(self.tab_manage, "\u8bbe\u5907\u7ba1\u7406")

        # ── Tab 3: Batch Tools ──
        self.tab_tools = QtWidgets.QWidget()
        tab3_layout = QtWidgets.QVBoxLayout(self.tab_tools)
        tab3_layout.setContentsMargins(12, 12, 12, 12)
        tab3_layout.setSpacing(12)

        # 检查更新按钮
        update_row = QtWidgets.QHBoxLayout()
        self.button_check_update = QtWidgets.QPushButton("🔄 检查更新")
        self.button_check_update.setObjectName("button_check_update")
        self.button_check_update.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; font-weight: bold; "
            "font-size: 13px; padding: 8px 16px; border: none; border-radius: 4px; }")
        update_row.addWidget(self.button_check_update)
        self.label_version = QtWidgets.QLabel("本地版本: -")
        self.label_version.setStyleSheet("color: #666; padding: 0 10px;")
        update_row.addWidget(self.label_version)
        update_row.addStretch()
        tab3_layout.addLayout(update_row)

        # 图片上传（图文分组）
        transfer_group = QtWidgets.QGroupBox("图片上传（图文分组）")
        transfer_layout = QtWidgets.QVBoxLayout(transfer_group)

        folder_row = QtWidgets.QHBoxLayout()
        folder_row.addWidget(QtWidgets.QLabel("图片文件夹:"))
        self.lineEdit_upload_folder = QtWidgets.QLineEdit()
        self.lineEdit_upload_folder.setObjectName("lineEdit_upload_folder")
        self.lineEdit_upload_folder.setPlaceholderText("选择图片所在文件夹")
        folder_row.addWidget(self.lineEdit_upload_folder)
        self.button_select_upload_folder = QtWidgets.QPushButton("浏览")
        self.button_select_upload_folder.setObjectName("button_select_upload_folder")
        self.button_select_upload_folder.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; border: none; border-radius: 3px; padding: 5px 14px; }")
        folder_row.addWidget(self.button_select_upload_folder)
        transfer_layout.addLayout(folder_row)

        upload_info = QtWidgets.QLabel(
            "文件名格式: 1-1-1（1）.jpg、2-3-1.png 等\n"
            "开头数字\"1\"传到图文分组第1台设备，\"2\"传到第2台（按分组内顺序）")
        upload_info.setStyleSheet("color: #666; font-size: 11px; padding: 2px;")
        upload_info.setWordWrap(True)
        transfer_layout.addWidget(upload_info)

        self.button_batch_upload = QtWidgets.QPushButton("一键上传图片（图文分组）")
        self.button_batch_upload.setObjectName("button_batch_upload")
        self.button_batch_upload.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; font-weight: bold; "
            "font-size: 14px; padding: 12px; border: none; border-radius: 4px; }")
        transfer_layout.addWidget(self.button_batch_upload)

        tab3_layout.addWidget(transfer_group)

        # 视频上传（视频分组）
        video_upload_group = QtWidgets.QGroupBox("视频上传（视频分组）")
        video_upload_layout = QtWidgets.QVBoxLayout(video_upload_group)

        video_folder_row = QtWidgets.QHBoxLayout()
        video_folder_row.addWidget(QtWidgets.QLabel("视频文件夹:"))
        self.lineEdit_upload_video_folder = QtWidgets.QLineEdit()
        self.lineEdit_upload_video_folder.setObjectName("lineEdit_upload_video_folder")
        self.lineEdit_upload_video_folder.setPlaceholderText("选择视频所在文件夹")
        video_folder_row.addWidget(self.lineEdit_upload_video_folder)
        self.button_select_upload_video_folder = QtWidgets.QPushButton("浏览")
        self.button_select_upload_video_folder.setObjectName("button_select_upload_video_folder")
        self.button_select_upload_video_folder.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; border: none; border-radius: 3px; padding: 5px 14px; }")
        video_folder_row.addWidget(self.button_select_upload_video_folder)
        video_upload_layout.addLayout(video_folder_row)

        video_upload_info = QtWidgets.QLabel(
            "文件名格式: 1.mp4、2.mov 等\n"
            "开头数字\"1\"传到视频分组第1台设备，\"2\"传到第2台（按分组内顺序）")
        video_upload_info.setStyleSheet("color: #666; font-size: 11px; padding: 2px;")
        video_upload_info.setWordWrap(True)
        video_upload_layout.addWidget(video_upload_info)

        self.button_batch_upload_video = QtWidgets.QPushButton("一键上传视频（视频分组）")
        self.button_batch_upload_video.setObjectName("button_batch_upload_video")
        self.button_batch_upload_video.setStyleSheet(
            "QPushButton { background-color: #6A1B9A; color: white; font-weight: bold; "
            "font-size: 14px; padding: 12px; border: none; border-radius: 4px; }")
        video_upload_layout.addWidget(self.button_batch_upload_video)

        tab3_layout.addWidget(video_upload_group)

        # Delete album
        album_group = QtWidgets.QGroupBox("\u76f8\u518c\u7ba1\u7406")
        album_layout = QtWidgets.QVBoxLayout(album_group)
        self.button_delete_album = QtWidgets.QPushButton("\u4e00\u952e\u5220\u9664\u6240\u6709\u8bbe\u5907\u76f8\u518c")
        self.button_delete_album.setObjectName("button_delete_album")
        self.button_delete_album.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        album_layout.addWidget(self.button_delete_album)
        tab3_layout.addWidget(album_group)

        # Switch account
        switch_group = QtWidgets.QGroupBox("\u5207\u53f7")
        switch_layout = QtWidgets.QHBoxLayout(switch_group)
        self.button_switch_account_all = QtWidgets.QPushButton("\u4e00\u952e\u5207\u53f7(\u6240\u6709\u8bbe\u5907)")
        self.button_switch_account_all.setObjectName("button_switch_account_all")
        self.button_switch_account_all.setStyleSheet(
            "QPushButton { background-color: #E91E63; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        switch_layout.addWidget(self.button_switch_account_all)
        self.button_switch_account_selected = QtWidgets.QPushButton("\u9009\u8bbe\u5907\u5207\u53f7")
        self.button_switch_account_selected.setObjectName("button_switch_account_selected")
        self.button_switch_account_selected.setStyleSheet(
            "QPushButton { background-color: #9C27B0; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        switch_layout.addWidget(self.button_switch_account_selected)
        tab3_layout.addWidget(switch_group)

        # Ad code / Stream key
        adcode_group = QtWidgets.QGroupBox("TikTok\u63a8\u6d41\u7801")
        adcode_layout = QtWidgets.QVBoxLayout(adcode_group)

        adcode_btn_row = QtWidgets.QHBoxLayout()
        self.button_fetch_video_data = QtWidgets.QPushButton("\u83b7\u53d6\u5f53\u5929\u89c6\u9891\u6570\u636e")
        self.button_fetch_video_data.setObjectName("button_fetch_video_data")
        self.button_fetch_video_data.setStyleSheet(
            "QPushButton { background-color: #FF8F00; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        adcode_btn_row.addWidget(self.button_fetch_video_data)

        self.button_adcode_by_name = QtWidgets.QPushButton("获取推流码(自定义名)")
        self.button_adcode_by_name.setObjectName("button_adcode_by_name")
        self.button_adcode_by_name.setStyleSheet(
            "QPushButton { background-color: #1565C0; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        adcode_btn_row.addWidget(self.button_adcode_by_name)

        self.button_adcode_by_group = QtWidgets.QPushButton("获取推流码(设备名)")
        self.button_adcode_by_group.setObjectName("button_adcode_by_group")
        self.button_adcode_by_group.setStyleSheet(
            "QPushButton { background-color: #7B1FA2; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        adcode_btn_row.addWidget(self.button_adcode_by_group)
        adcode_layout.addLayout(adcode_btn_row)

        adcode_btn_row2 = QtWidgets.QHBoxLayout()
        self.button_gen_fail_report = QtWidgets.QPushButton("生成未成功信息")
        self.button_gen_fail_report.setObjectName("button_gen_fail_report")
        self.button_gen_fail_report.setStyleSheet(
            "QPushButton { background-color: #E65100; color: white; font-weight: bold; "
            "font-size: 12px; padding: 8px; border: none; border-radius: 4px; }")
        adcode_btn_row2.addWidget(self.button_gen_fail_report)
        adcode_btn_row2.addStretch()
        adcode_layout.addLayout(adcode_btn_row2)

        # ── 选定日期视频数据 + 推流码 ──
        adcode_date_row = QtWidgets.QHBoxLayout()
        self.button_fetch_video_selected = QtWidgets.QPushButton("获取选定日期视频数据")
        self.button_fetch_video_selected.setObjectName("button_fetch_video_selected")
        self.button_fetch_video_selected.setStyleSheet(
            "QPushButton { background-color: #FF8F00; color: white; font-weight: bold; "
            "font-size: 12px; padding: 8px; border: none; border-radius: 4px; }")
        adcode_date_row.addWidget(self.button_fetch_video_selected)

        self.button_adcode_selected_name = QtWidgets.QPushButton("获取某天推流码(自定义名)")
        self.button_adcode_selected_name.setObjectName("button_adcode_selected_name")
        self.button_adcode_selected_name.setStyleSheet(
            "QPushButton { background-color: #1565C0; color: white; font-weight: bold; "
            "font-size: 12px; padding: 8px; border: none; border-radius: 4px; }")
        adcode_date_row.addWidget(self.button_adcode_selected_name)

        self.button_adcode_selected_devname = QtWidgets.QPushButton("获取某天推流码(设备名)")
        self.button_adcode_selected_devname.setObjectName("button_adcode_selected_devname")
        self.button_adcode_selected_devname.setStyleSheet(
            "QPushButton { background-color: #7B1FA2; color: white; font-weight: bold; "
            "font-size: 12px; padding: 8px; border: none; border-radius: 4px; }")
        adcode_date_row.addWidget(self.button_adcode_selected_devname)
        adcode_layout.addLayout(adcode_date_row)

        adcode_info = QtWidgets.QLabel(
            "步骤1: 点击「获取当天视频数据」从 TikHub 拉取当天视频写入飞书\n"
            "步骤2: 点击「获取推流码」从飞书读取数据，通过 iMouse 自动化获取推流码\n"
            "选定日期: 在飞书完播率Tab选好日期后，点击对应按钮获取该日期的数据/推流码")
        adcode_info.setStyleSheet("color: #666666; font-size: 11px; padding: 4px;")
        adcode_info.setWordWrap(True)
        adcode_layout.addWidget(adcode_info)
        tab3_layout.addWidget(adcode_group)

        tab3_layout.addStretch()
        self.tabWidget.addTab(self.tab_tools, "\u6279\u91cf\u5de5\u5177")

        # ── Tab 4: 完播率分析 ──
        self.tab_analytics = QtWidgets.QWidget()
        tab4_layout = QtWidgets.QVBoxLayout(self.tab_analytics)
        tab4_layout.setContentsMargins(12, 12, 12, 12)
        tab4_layout.setSpacing(10)

        # Excel文件选择
        excel_file_group = QtWidgets.QGroupBox("\u6570\u636e\u6587\u4ef6")
        excel_file_layout = QtWidgets.QVBoxLayout(excel_file_group)

        ef_row = QtWidgets.QHBoxLayout()
        ef_row.addWidget(QtWidgets.QLabel("Excel\u6587\u4ef6:"))
        self.lineEdit_analytics_excel = QtWidgets.QLineEdit()
        self.lineEdit_analytics_excel.setObjectName("lineEdit_analytics_excel")
        self.lineEdit_analytics_excel.setPlaceholderText("\u9009\u62e9\u5305\u542b\u89c6\u9891\u94fe\u63a5\u7684Excel\u6587\u4ef6")
        ef_row.addWidget(self.lineEdit_analytics_excel)
        self.button_select_analytics_excel = QtWidgets.QPushButton("\u6d4f\u89c8")
        self.button_select_analytics_excel.setObjectName("button_select_analytics_excel")
        self.button_select_analytics_excel.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; border: none; border-radius: 3px; padding: 5px 14px; }")
        ef_row.addWidget(self.button_select_analytics_excel)
        excel_file_layout.addLayout(ef_row)

        ef_info = QtWidgets.QLabel(
            "Excel\u683c\u5f0f: \u9700\u5305\u542b\u300c\u89c6\u9891\u94fe\u63a5\u300d\u5217\uff0c\u53ef\u9009\u300c\u64ad\u653e\u91cf\u300d\u300c\u70b9\u8d5e\u91cf\u300d\u300c\u5b8c\u64ad\u7387\u300d\u5217")
        ef_info.setStyleSheet("color: #666; font-size: 11px; padding: 2px;")
        ef_info.setWordWrap(True)
        excel_file_layout.addWidget(ef_info)
        tab4_layout.addWidget(excel_file_group)

        # 操作按钮
        analytics_btn_group = QtWidgets.QGroupBox("\u64cd\u4f5c")
        analytics_btn_layout = QtWidgets.QVBoxLayout(analytics_btn_group)

        btn_row1 = QtWidgets.QHBoxLayout()
        self.button_fetch_stats = QtWidgets.QPushButton("\u6b65\u9aa41: \u83b7\u53d6\u64ad\u653e\u91cf/\u70b9\u8d5e\u91cf")
        self.button_fetch_stats.setObjectName("button_fetch_stats")
        self.button_fetch_stats.setStyleSheet(
            "QPushButton { background-color: #FF8F00; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        btn_row1.addWidget(self.button_fetch_stats)
        analytics_btn_layout.addLayout(btn_row1)

        btn_row2 = QtWidgets.QHBoxLayout()
        self.button_fetch_completion_rate = QtWidgets.QPushButton("\u6b65\u9aa42: \u83b7\u53d6\u5b8c\u64ad\u7387")
        self.button_fetch_completion_rate.setObjectName("button_fetch_completion_rate")
        self.button_fetch_completion_rate.setStyleSheet(
            "QPushButton { background-color: #1565C0; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        btn_row2.addWidget(self.button_fetch_completion_rate)
        analytics_btn_layout.addLayout(btn_row2)

        analytics_note = QtWidgets.QLabel(
            "\u6b65\u9aa41: \u901a\u8fc7TikHub API\u83b7\u53d6\u6240\u6709\u89c6\u9891\u7684\u64ad\u653e\u91cf\u548c\u70b9\u8d5e\u91cf\uff0c\u5199\u5165Excel\n"
            "\u6b65\u9aa42: \u5339\u914d\u5728\u7ebf\u8bbe\u5907\uff0c\u81ea\u52a8\u6253\u5f00\u89c6\u9891\u2192Analytics\u2192\u62d6\u52a8\u6ed1\u5757\u2192\u8bfb\u53d6\u5b8c\u64ad\u7387\n"
            "\u540c\u65f6\u83b7\u53d6\u63a8\u6d41\u7801\uff0c\u7ed3\u679c\u5168\u90e8\u5199\u56deExcel\n\n"
            "\u56fe\u6807\u6587\u4ef6\u8981\u6c42 (\u653e\u5728 icon/ \u76ee\u5f55):\n"
            "  analytics.bmp - Analytics\u6309\u94ae\u622a\u56fe\n"
            "  white_ball.bmp - \u767d\u8272\u7403\u4f53\u622a\u56fe")
        analytics_note.setStyleSheet("color: #666; font-size: 11px; padding: 4px;")
        analytics_note.setWordWrap(True)
        analytics_btn_layout.addWidget(analytics_note)
        tab4_layout.addWidget(analytics_btn_group)

        tab4_layout.addStretch()
        self.tabWidget.addTab(self.tab_analytics, "\u5b8c\u64ad\u7387\u5206\u6790")

        # ── Tab 5: 飞书完播率 ──
        self.tab_feishu_analytics = QtWidgets.QWidget()
        tab5_layout = QtWidgets.QVBoxLayout(self.tab_feishu_analytics)
        tab5_layout.setContentsMargins(12, 12, 12, 12)
        tab5_layout.setSpacing(10)

        # 日期选择区域
        date_group = QtWidgets.QGroupBox("\u9009\u62e9\u65e5\u671f")
        date_main_layout = QtWidgets.QVBoxLayout(date_group)

        # 年月选择行
        ym_row = QtWidgets.QHBoxLayout()
        ym_row.addWidget(QtWidgets.QLabel("\u5e74:"))
        self.spinBox_year = QtWidgets.QSpinBox()
        self.spinBox_year.setMinimum(2024)
        self.spinBox_year.setMaximum(2030)
        self.spinBox_year.setValue(2026)
        ym_row.addWidget(self.spinBox_year)
        ym_row.addWidget(QtWidgets.QLabel("\u6708:"))
        self.spinBox_month = QtWidgets.QSpinBox()
        self.spinBox_month.setMinimum(1)
        self.spinBox_month.setMaximum(12)
        self.spinBox_month.setValue(3)
        ym_row.addWidget(self.spinBox_month)
        self.button_select_all_days = QtWidgets.QPushButton("\u9009\u53d6\u5f53\u6708\u5168\u90e8")
        self.button_select_all_days.setObjectName("button_select_all_days")
        self.button_select_all_days.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; border: none; border-radius: 3px; padding: 5px 10px; }")
        ym_row.addWidget(self.button_select_all_days)
        self.button_clear_days = QtWidgets.QPushButton("\u6e05\u7a7a\u9009\u62e9")
        self.button_clear_days.setObjectName("button_clear_days")
        self.button_clear_days.setStyleSheet(
            "QPushButton { background-color: #757575; color: white; border: none; border-radius: 3px; padding: 5px 10px; }")
        ym_row.addWidget(self.button_clear_days)
        ym_row.addStretch()
        date_main_layout.addLayout(ym_row)

        # 日历网格 (7列 x 6行)
        self.calendar_grid = QtWidgets.QGridLayout()
        self.calendar_grid.setSpacing(2)
        # 星期标题
        for i, day_name in enumerate(["\u65e5", "\u4e00", "\u4e8c", "\u4e09", "\u56db", "\u4e94", "\u516d"]):
            lbl = QtWidgets.QLabel(day_name)
            lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: #333; font-size: 11px;")
            self.calendar_grid.addWidget(lbl, 0, i)
        # 日按钮 (最多42个格子 = 6行7列)
        self.day_buttons = []
        for row in range(6):
            for col in range(7):
                btn = QtWidgets.QPushButton("")
                btn.setCheckable(True)
                btn.setFixedSize(36, 28)
                btn.setStyleSheet(
                    "QPushButton { background: #f0f0f0; border: 1px solid #ccc; border-radius: 3px; font-size: 11px; }"
                    "QPushButton:checked { background: #1976D2; color: white; border: 1px solid #1565C0; }"
                    "QPushButton:hover { background: #BBDEFB; }")
                self.calendar_grid.addWidget(btn, row + 1, col)
                self.day_buttons.append(btn)
        date_main_layout.addLayout(self.calendar_grid)

        # 已选日期显示
        self.label_selected_dates = QtWidgets.QLabel("\u5df2\u9009: \u65e0")
        self.label_selected_dates.setStyleSheet("color: #1565C0; font-size: 11px; padding: 2px;")
        self.label_selected_dates.setWordWrap(True)
        date_main_layout.addWidget(self.label_selected_dates)

        tab5_layout.addWidget(date_group)

        # 操作按钮
        feishu_btn_group = QtWidgets.QGroupBox("\u64cd\u4f5c")
        feishu_btn_layout = QtWidgets.QVBoxLayout(feishu_btn_group)

        feishu_btn_row = QtWidgets.QHBoxLayout()
        self.button_feishu_rate_by_name = QtWidgets.QPushButton("获取完播率(自定义名)")
        self.button_feishu_rate_by_name.setObjectName("button_feishu_rate_by_name")
        self.button_feishu_rate_by_name.setStyleSheet(
            "QPushButton { background-color: #1565C0; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        feishu_btn_row.addWidget(self.button_feishu_rate_by_name)

        self.button_feishu_rate_by_group = QtWidgets.QPushButton("获取完播率(设备名)")
        self.button_feishu_rate_by_group.setObjectName("button_feishu_rate_by_group")
        self.button_feishu_rate_by_group.setStyleSheet(
            "QPushButton { background-color: #7B1FA2; color: white; font-weight: bold; "
            "font-size: 13px; padding: 10px; border: none; border-radius: 4px; }")
        feishu_btn_row.addWidget(self.button_feishu_rate_by_group)
        feishu_btn_layout.addLayout(feishu_btn_row)

        feishu_note = QtWidgets.QLabel(
            "\u6d41\u7a0b: \u9009\u62e9\u65e5\u671f \u2192 \u4ece\u98de\u4e66\u8868\u8bfb\u53d6\u5bf9\u5e94\u65e5\u671f\u89c6\u9891 \u2192 TikHub\u66f4\u65b0\u64ad\u653e/\u70b9\u8d5e \u2192 \u5339\u914d\u8bbe\u5907 \u2192 \u83b7\u53d6\u5b8c\u64ad\u7387 \u2192 \u5199\u56de\u98de\u4e66\n\n"
            "\u56fe\u6807\u6587\u4ef6\u8981\u6c42 (icon/ \u76ee\u5f55):\n"
            "  analytics.bmp - Analytics\u6309\u94ae\n"
            "  white_ball.bmp - \u767d\u8272\u7403\u4f53\n"
            "  dont_allow.bmp - Don't allow\u5f39\u7a97(\u53ef\u9009)")
        feishu_note.setStyleSheet("color: #666; font-size: 11px; padding: 4px;")
        feishu_note.setWordWrap(True)
        feishu_btn_layout.addWidget(feishu_note)
        tab5_layout.addWidget(feishu_btn_group)

        tab5_layout.addStretch()
        self.tabWidget.addTab(self.tab_feishu_analytics, "\u98de\u4e66\u5b8c\u64ad\u7387")

        right_panel.addWidget(self.tabWidget)
        main_layout.addLayout(right_panel, stretch=5)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        pass  # All text is set inline during setupUi
