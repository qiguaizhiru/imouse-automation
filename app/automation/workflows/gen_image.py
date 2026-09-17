# -*- coding: utf-8 -*-
# 生图工作流（测试）：
#   读取飞书表里 [创建人=测试 且 状态=完成生图] 的记录 → 下载"贴图图片"到本地
#   → 上传到随机一台在线手机的相册 → 把状态改成"完成下载"

import json
import os
import random
import re

from .base import WorkflowBase
from ..feishu import FeishuBitable, cell_url
from ..paths import data_path

MEDIA_BASE = r"D:\iMousePro\Shortcut\Media"

# 飞书凭据不写在代码里（程序包和 GitHub 热更新都是公开分发的），
# 存本机 workflow_config.json（工作流Tab「飞书表配置」保存），格式：
#   {"gen_image": {"app_id": "...", "app_secret": "...", "app_token": "...", "table_id": "..."}}
WORKFLOW_CONFIG_FILE = data_path("workflow_config.json")
CRED_KEYS = ("app_id", "app_secret", "app_token", "table_id")


def load_workflow_config():
    """读本机 workflow_config.json，读不到返回 {}"""
    try:
        with open(WORKFLOW_CONFIG_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_workflow_config(section, values):
    """把某个工作流的配置合并写回 workflow_config.json"""
    d = load_workflow_config()
    d[section] = {**d.get(section, {}), **values}
    os.makedirs(os.path.dirname(WORKFLOW_CONFIG_FILE), exist_ok=True)
    with open(WORKFLOW_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    return WORKFLOW_CONFIG_FILE


def parse_bitable_link(text):
    """从飞书多维表格分享链接解析 (app_token, table_id)；直接给 token 也行。
    链接形如 https://xxx.feishu.cn/base/<app_token>?table=<table_id>&view=...
    或 wiki 链接 /wiki/<node_token>（wiki 节点 token 需另换 app_token，这里原样返回）"""
    text = (text or "").strip()
    if not text:
        return "", ""
    m = re.search(r"/(?:base|wiki)/([A-Za-z0-9]+)", text)
    token = m.group(1) if m else text.split("?")[0].strip("/")
    m2 = re.search(r"[?&]table=([A-Za-z0-9]+)", text)
    return token, (m2.group(1) if m2 else "")


# 表结构默认值（不含凭据）；以后不同工作流可用不同表
GEN_IMAGE_CFG = {
    "app_id": "",
    "app_secret": "",
    "app_token": "",
    "table_id": "",
    "creator_field": "创建人",
    "creator_value": "测试",
    "status_field": "状态",
    "status_from": "完成生图",
    "status_to": "完成下载",
    "status_fail": "下载失败",
    "image_field": "贴图图片",
    "poll_interval": 30,     # 每轮处理完后隔多少秒再查一次
}


class GenImageWorkflow(WorkflowBase):
    name = "gen_image"
    display = "生图工作流"

    def __init__(self, device_manager, log_callback=None, error_reporter=None, config=None):
        super().__init__(device_manager, log_callback, error_reporter)
        self.cfg = dict(GEN_IMAGE_CFG)
        self.cfg.update(load_workflow_config().get("gen_image", {}))   # 本机凭据
        if config:
            self.cfg.update(config)
        self.bitable = None
        missing = [k for k in CRED_KEYS if not str(self.cfg.get(k, "")).strip()]
        if not missing:
            self.bitable = FeishuBitable(
                self.cfg["app_id"], self.cfg["app_secret"],
                self.cfg["app_token"], self.cfg["table_id"])
        self._missing = missing

    def run(self):
        if self.bitable is None:
            self._log(f"未配置飞书凭据（缺 {', '.join(self._missing)}）："
                      f"请在「工作流」Tab 的「飞书表配置」填写 App ID / App Secret / 表格链接 后保存，"
                      f"再启动。配置文件: {WORKFLOW_CONFIG_FILE}")
            return
        self._log("已启动，开始轮询飞书表（创建人=测试 且 状态=完成生图）")
        while not self.should_stop:
            try:
                self._process_batch()
            except Exception as e:
                self._log(f"本轮处理异常: {e}")
            if self.should_stop:
                break
            self.wait(self.cfg["poll_interval"])
        self._log("已停止")

    def _process_batch(self):
        c = self.cfg
        filter_obj = {
            "conjunction": "and",
            "conditions": [
                {"field_name": c["creator_field"], "operator": "is",
                 "value": [c["creator_value"]]},
                {"field_name": c["status_field"], "operator": "is",
                 "value": [c["status_from"]]},
            ],
        }
        records = self.bitable.search_records(filter_obj)
        if not records:
            self._log("暂无待下载记录")
            return

        devices = self.dm.get_devices()
        if not devices:
            self._log("没有在线设备，等待设备上线")
            return

        self._log(f"找到 {len(records)} 条待处理，在线设备 {len(devices)} 台")
        done = 0
        for rec in records:
            if self.should_stop:
                return
            rid = rec.get("record_id")
            fields = rec.get("fields", {})
            url = cell_url(fields.get(c["image_field"]))
            if not url:
                self._log(f"记录 {rid} 没有图片链接，跳过")
                continue

            dev = random.choice(devices)
            # 1. 下载到 该设备的 Media 文件夹
            dev_dir = os.path.join(MEDIA_BASE, dev.name)
            try:
                os.makedirs(dev_dir, exist_ok=True)
            except Exception:
                pass
            local = os.path.join(dev_dir, f"{rid}.jpg")
            try:
                self.bitable.download_url(url, local)
            except Exception as e:
                self._log(f"记录 {rid} 图片下载失败: {e}")
                self._safe_update(rid, c["status_fail"])
                continue

            # 2. 上传到随机手机的相册
            ret = dev.album_upload([local])
            ok = bool(ret and ret.get("status") in (0, 200))

            # 3. 改状态
            new_status = c["status_to"] if ok else c["status_fail"]
            self._safe_update(rid, new_status)
            self._log(f"记录 {rid}: 下载OK，上传到 [{dev.name}] "
                      f"{'成功' if ok else '失败'}，状态→{new_status}")
            if ok:
                done += 1
        self._log(f"本轮完成，成功处理 {done} 条")

    def _safe_update(self, record_id, status):
        try:
            self.bitable.update_record(record_id, {self.cfg["status_field"]: status})
        except Exception as e:
            self._log(f"记录 {record_id} 改状态失败: {e}")
