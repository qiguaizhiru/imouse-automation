# -*- coding: utf-8 -*-
# 多节点管理 - 同时连接多台电脑的 iMouse，聚合所有设备
#
# 每个"节点"代表一台运行 iMouse 的电脑（含本机）。
# 主控软件配置节点列表，统一调度所有节点上连接的手机。

import json
import logging
import os
import threading

from .device import DeviceManager

logger = logging.getLogger("automation.nodes")

from .paths import data_path

NODES_FILE = data_path("nodes.json")

DEFAULT_NODES = [
    {"name": "本机", "host": "127.0.0.1", "port": 9912},
]


def load_nodes():
    if os.path.exists(NODES_FILE):
        try:
            with open(NODES_FILE, "r", encoding="utf-8-sig") as f:
                nodes = json.load(f)
            if nodes:
                return nodes
        except Exception as e:
            logger.warning(f"加载节点配置失败: {e}")
    return [dict(n) for n in DEFAULT_NODES]


def save_nodes(nodes):
    with open(NODES_FILE, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)


class MultiNodeManager:
    """聚合多个 iMouse 节点的设备管理器

    提供与 DeviceManager 相同的接口（get_devices / get_device_by_name），
    引擎可以无缝替换使用。
    """

    def __init__(self, nodes=None):
        self.nodes = nodes if nodes is not None else load_nodes()
        self._managers = {}  # node_name -> DeviceManager
        self._rebuild()

    def _rebuild(self):
        self._managers = {}
        for node in self.nodes:
            name = node.get("name", node.get("host", "?"))
            self._managers[name] = DeviceManager(
                host=node.get("host", "127.0.0.1"),
                port=node.get("port", 9912),
                node_name=name,
            )

    def set_nodes(self, nodes):
        self.nodes = nodes
        self._rebuild()
        save_nodes(nodes)

    def get_devices(self):
        """聚合所有节点的设备（并发查询，单节点失败不影响其它）"""
        all_devices = []
        results = {}
        threads = []

        def _fetch(name, mgr):
            try:
                results[name] = mgr.get_devices()
            except Exception as e:
                logger.warning(f"节点 [{name}] 获取设备失败: {e}")
                results[name] = []

        for name, mgr in self._managers.items():
            t = threading.Thread(target=_fetch, args=(name, mgr), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=15)

        for name in self._managers:
            all_devices.extend(results.get(name, []))

        logger.info(f"共 {len(self._managers)} 个节点，聚合到 {len(all_devices)} 台设备")
        return all_devices

    def get_device_by_name(self, name):
        """按名称查找设备，支持 '节点/设备名' 或纯设备名"""
        devices = self.get_devices()
        # 先精确匹配 full_name
        for d in devices:
            if d.full_name == name:
                return d
        # 再匹配纯设备名
        for d in devices:
            if d.name == name:
                return d
        return None

    def get_node_status(self):
        """返回每个节点的连接状态和设备数（并发探测，离线节点不互相阻塞）"""
        status = {}
        threads = []

        def _probe(name, mgr):
            online, count = mgr.probe()
            status[name] = {
                "host": mgr.host, "port": mgr.port,
                "online": online, "device_count": count,
            }

        for name, mgr in self._managers.items():
            t = threading.Thread(target=_probe, args=(name, mgr), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=10)

        # 兜底：未返回的节点标记离线
        for name, mgr in self._managers.items():
            if name not in status:
                status[name] = {"host": mgr.host, "port": mgr.port,
                                "online": False, "device_count": 0}
        return status

    def test_node(self, host, port):
        """测试单个节点连通性，返回设备数或 -1"""
        try:
            mgr = DeviceManager(host=host, port=port, node_name="test")
            return len(mgr.get_devices())
        except Exception:
            return -1
