import json
import os

DEFAULT_CONFIG = {
    "imouse_host": "127.0.0.1",
    "imouse_port": 9912,
    "feishu_app_id": "cli_a99b14fa3b7d900d",
    "feishu_app_secret": "ZTawO0DxS1k06DTXYEiDAg8ACWaGCONz",
    "feishu_app_token": "NOulwz2X3i6Eg9kU9L0cnh8Qnyg",
    "account_table_id": "tblqIhS037A7v99R",
    "tikhub_token": "5+UtWGJ7zHdyjAoejG6rpUMM9CsrpZPAvIpF4Dm/vkhx7xAXcu9C+AHsCA==",
    "tiktok_scheme": "snssdk1233://",
}

from .paths import data_path

CONFIG_FILE = data_path("config.json")


def load_config(path=None):
    path = path or CONFIG_FILE
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        cfg.update(user_cfg)
    return cfg


def save_config(cfg, path=None):
    path = path or CONFIG_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
