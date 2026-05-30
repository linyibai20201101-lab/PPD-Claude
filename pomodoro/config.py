import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".pomodoro"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "work_duration": 25,       # 分钟
    "short_break": 5,
    "long_break": 15,
    "pomodoros_before_long": 4,
    "auto_start_break": True,
    "auto_start_work": False,
    "sound_enabled": True,
    "notification_enabled": True,
    "white_noise": "none",     # none / rain / cafe / forest
    "theme": "light",          # light / dark
    "always_on_top": False,
}


def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        merged = {**DEFAULT_CONFIG, **saved}
        return merged
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
