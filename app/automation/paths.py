# -*- coding: utf-8 -*-
# 统一路径管理 - 兼容开发环境和 PyInstaller 打包
#
# 打包后的两类路径:
#   可写数据(配置/任务/日志/用户名) -> exe 所在目录(用户能看到、能改)
#   只读资源(icon 模板图)          -> 打包进程序内部(_MEIPASS)

import os
import sys


def is_frozen():
    """是否运行在 PyInstaller 打包后的环境"""
    return getattr(sys, "frozen", False)


def _pkg_parent():
    """automation 包的上级目录：开发=项目根，打包=exe同级的 app 目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_dir():
    """只读资源目录（icon 等，与 automation 同级放）：
    开发=项目根，打包=app 目录。资源随业务代码一起热更新。"""
    return _pkg_parent()


def app_data_dir():
    """可写数据目录（配置/日志/任务，不参与热更）：
    打包=exe 所在目录，开发=项目根。"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return _pkg_parent()


def data_path(name):
    """可写文件的完整路径（配置、任务、用户名等）"""
    return os.path.join(app_data_dir(), name)


def resource_path(rel):
    """只读资源的完整路径（icon 等）"""
    return os.path.join(resource_dir(), rel)
