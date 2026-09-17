# -*- coding: utf-8 -*-
# 飞书多维表格(Bitable)客户端 - 工作流读写飞书表用

import logging
import time

try:
    import requests as _requests
except ImportError:
    _requests = None

logger = logging.getLogger("automation.feishu")

BASE_URL = "https://open.feishu.cn"


class FeishuBitable:
    """飞书多维表格客户端：搜索记录、更新记录、下载图片URL。"""

    def __init__(self, app_id, app_secret, app_token, table_id):
        self.app_id = app_id
        self.app_secret = app_secret
        self.app_token = app_token
        self.table_id = table_id
        self._token = None
        self._token_exp = 0
        self._s = _requests.Session() if _requests else None

    def _tenant_token(self):
        now = time.time()
        if self._token and now < self._token_exp - 60:
            return self._token
        r = self._s.post(
            f"{BASE_URL}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=20).json()
        if r.get("code") != 0:
            raise RuntimeError(f"飞书token失败: {r.get('msg')}")
        self._token = r["tenant_access_token"]
        self._token_exp = now + r.get("expire", 7200)
        return self._token

    def _headers(self):
        return {"Authorization": f"Bearer {self._tenant_token()}",
                "Content-Type": "application/json"}

    def search_records(self, filter_obj=None, view_id=None, page_size=500):
        """按 filter 搜索记录，自动翻页，返回记录列表 [{record_id, fields}]"""
        records = []
        page_token = None
        while True:
            params = [("page_size", str(page_size))]
            if page_token:
                params.append(("page_token", page_token))
            body = {}
            if filter_obj:
                body["filter"] = filter_obj
            if view_id:
                body["view_id"] = view_id
            r = self._s.post(
                f"{BASE_URL}/open-apis/bitable/v1/apps/{self.app_token}"
                f"/tables/{self.table_id}/records/search",
                headers=self._headers(), params=params, json=body, timeout=30).json()
            if r.get("code") != 0:
                raise RuntimeError(f"飞书搜索失败: {r.get('msg')}")
            d = r.get("data", {})
            records.extend(d.get("items") or [])
            page_token = d.get("page_token")
            if not d.get("has_more") or not page_token:
                break
        return records

    def update_record(self, record_id, fields):
        """更新单条记录的字段"""
        r = self._s.put(
            f"{BASE_URL}/open-apis/bitable/v1/apps/{self.app_token}"
            f"/tables/{self.table_id}/records/{record_id}",
            headers=self._headers(), json={"fields": fields}, timeout=30).json()
        if r.get("code") != 0:
            raise RuntimeError(f"飞书更新失败: {r.get('msg')}")
        return True

    @staticmethod
    def download_url(url, out_path, timeout=60):
        """下载一个URL到本地文件（用于阿里云OSS图片链接）"""
        r = _requests.get(url, timeout=timeout, stream=True)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
        return out_path


def cell_url(value):
    """从单元格取URL：URL字段是 {'link':.., 'text':..}；也兼容纯字符串。"""
    if isinstance(value, dict):
        return value.get("link") or value.get("text")
    if isinstance(value, list) and value:
        v0 = value[0]
        if isinstance(v0, dict):
            return v0.get("link") or v0.get("text") or v0.get("url")
    return value if isinstance(value, str) else None
