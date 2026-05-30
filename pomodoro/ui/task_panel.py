import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QLabel,
    QFrame, QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal

TASKS_FILE = Path.home() / ".pomodoro" / "tasks.json"


class TaskPanel(QWidget):
    task_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = []
        self._current_index = -1
        self._load_tasks()
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 8, 16)
        layout.setSpacing(10)

        title = QLabel("📋 任务列表")
        title.setStyleSheet("font-size: 15px; font-weight: bold; margin-bottom: 4px;")
        layout.addWidget(title)

        # 输入框 + 添加按钮
        input_layout = QHBoxLayout()
        self.input_task = QLineEdit()
        self.input_task.setPlaceholderText("添加新任务...")
        self.input_task.returnPressed.connect(self._add_task)

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(36, 36)
        self.btn_add.setObjectName("primary_btn")
        self.btn_add.clicked.connect(self._add_task)

        input_layout.addWidget(self.input_task)
        input_layout.addWidget(self.btn_add)
        layout.addLayout(input_layout)

        # 任务列表
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        # 底部按钮
        btn_layout = QHBoxLayout()

        self.btn_complete = QPushButton("✓ 完成")
        self.btn_complete.setObjectName("success_btn")
        self.btn_complete.setEnabled(False)
        self.btn_complete.clicked.connect(self._complete_task)

        self.btn_delete = QPushButton("✕ 删除")
        self.btn_delete.setObjectName("danger_btn")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_task)

        btn_layout.addWidget(self.btn_complete)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def _load_tasks(self):
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if TASKS_FILE.exists():
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                self._tasks = json.load(f)
        else:
            self._tasks = []

    def _save_tasks(self):
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._tasks, f, ensure_ascii=False, indent=2)

    def _refresh_list(self):
        self.list_widget.clear()
        for task in self._tasks:
            status = "✓ " if task.get("done") else ""
            pomodoros = task.get("pomodoros", 0)
            count_text = f"  [{pomodoros}🍅]" if pomodoros > 0 else ""
            item = QListWidgetItem(f"{status}{task['name']}{count_text}")
            if task.get("done"):
                item.setForeground(Qt.gray)
            self.list_widget.addItem(item)

    def _add_task(self):
        name = self.input_task.text().strip()
        if not name:
            return
        self._tasks.append({"name": name, "done": False, "pomodoros": 0})
        self.input_task.clear()
        self._save_tasks()
        self._refresh_list()
        self.list_widget.setCurrentRow(len(self._tasks) - 1)
        self.task_changed.emit()

    def _complete_task(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._tasks):
            self._tasks[row]["done"] = not self._tasks[row].get("done", False)
            self._save_tasks()
            self._refresh_list()
            self.task_changed.emit()

    def _delete_task(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._tasks):
            self._tasks.pop(row)
            self._save_tasks()
            self._refresh_list()
            self._current_index = -1
            self._update_buttons()
            self.task_changed.emit()

    def _on_selection_changed(self, row: int):
        self._current_index = row
        self._update_buttons()

    def _update_buttons(self):
        has_selection = self._current_index >= 0
        self.btn_complete.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def get_current_task_name(self) -> str:
        if 0 <= self._current_index < len(self._tasks):
            return self._tasks[self._current_index]["name"]
        return ""

    def increment_current_task_pomodoro(self):
        if 0 <= self._current_index < len(self._tasks):
            self._tasks[self._current_index]["pomodoros"] = (
                self._tasks[self._current_index].get("pomodoros", 0) + 1
            )
            self._save_tasks()
            self._refresh_list()
