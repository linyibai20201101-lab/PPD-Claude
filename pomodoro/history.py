import json
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_DIR = Path.home() / ".pomodoro"
HISTORY_FILE = HISTORY_DIR / "history.json"


def _load_history() -> dict:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_history(data: dict):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_pomodoro(task_name: str = ""):
    data = _load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in data:
        data[today] = {"count": 0, "tasks": {}}
    data[today]["count"] += 1
    if task_name:
        tasks = data[today]["tasks"]
        tasks[task_name] = tasks.get(task_name, 0) + 1
    _save_history(data)


def get_today_count() -> int:
    data = _load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    return data.get(today, {}).get("count", 0)


def get_week_count() -> int:
    data = _load_history()
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    total = 0
    for i in range(7):
        day = (monday + timedelta(days=i)).strftime("%Y-%m-%d")
        total += data.get(day, {}).get("count", 0)
    return total


def get_total_count() -> int:
    data = _load_history()
    return sum(day.get("count", 0) for day in data.values())


def get_history(days: int = 7) -> list:
    data = _load_history()
    result = []
    now = datetime.now()
    for i in range(days - 1, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        result.append({
            "date": day,
            "count": data.get(day, {}).get("count", 0),
        })
    return result
