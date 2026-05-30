from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSplitter, QMessageBox, QAction, QMenu,
    QSystemTrayIcon, QApplication, QGraphicsOpacityEffect,
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor, QPixmap, QPainter, QFont

from .circular_progress import CircularProgress
from .task_panel import TaskPanel
from .stats_panel import StatsPanel
from .settings_dialog import SettingsDialog
from .styles import Colors, get_state_colors, LIGHT_STYLE
from timer import PomodoroTimer, TimerState
from config import load_config, save_config
from history import record_pomodoro, get_today_count


def _create_icon(color: QColor) -> QIcon:
    """生成一个纯色圆形图标"""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(color)
    p.setPen(Qt.NoPen)
    p.drawEllipse(4, 4, 56, 56)
    p.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.timer = PomodoroTimer(self.config, self)

        self.setWindowTitle("番茄钟")
        self.setMinimumSize(800, 550)
        self.resize(900, 600)
        self.setStyleSheet(LIGHT_STYLE)

        self._setup_ui()
        self._connect_signals()
        self._update_state_visuals()
        self._update_pomodoro_display()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧面板 - 任务
        self.task_panel = TaskPanel()
        self.task_panel.setMinimumWidth(220)
        self.task_panel.setMaximumWidth(320)

        # 中间 - 计时器
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setSpacing(20)
        center_layout.setContentsMargins(40, 30, 40, 30)

        self.progress = CircularProgress()
        center_layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_start = QPushButton("开始专注")
        self.btn_start.setObjectName("primary_btn")
        self.btn_start.setFixedHeight(44)
        self.btn_start.setMinimumWidth(100)

        self.btn_skip = QPushButton("跳过")
        self.btn_skip.setFixedHeight(44)

        self.btn_reset = QPushButton("重置")
        self.btn_reset.setFixedHeight(44)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_skip)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        center_layout.addLayout(btn_layout)

        # 番茄计数
        self.pomodoro_label = QLabel("🍅 今日: 0 个番茄")
        self.pomodoro_label.setObjectName("secondary_label")
        self.pomodoro_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.pomodoro_label)

        center_layout.addStretch()

        # 右侧面板 - 统计
        self.stats_panel = StatsPanel()
        self.stats_panel.setMinimumWidth(200)
        self.stats_panel.setMaximumWidth(300)

        # 使用 QSplitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.task_panel)
        splitter.addWidget(center_widget)
        splitter.addWidget(self.stats_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 1)
        splitter.setHandleWidth(1)

        main_layout.addWidget(splitter)

        # 底部工具栏
        self._setup_toolbar()

    def _setup_toolbar(self):
        toolbar = self.addToolBar("工具")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))

        self.action_settings = QAction("⚙ 设置", self)
        toolbar.addAction(self.action_settings)

        self.action_noise = QAction("🔊 白噪音: 关", self)
        toolbar.addAction(self.action_noise)

        toolbar.addSeparator()

        self.action_always_top = QAction("📌 置顶: 关", self)
        toolbar.addAction(self.action_always_top)

    def _connect_signals(self):
        # 按钮
        self.btn_start.clicked.connect(self._on_start_click)
        self.btn_skip.clicked.connect(self._on_skip_click)
        self.btn_reset.clicked.connect(self._on_reset_click)

        # 计时器信号
        self.timer.tick.connect(self._on_tick)
        self.timer.state_changed.connect(self._on_state_changed)
        self.timer.pomodoro_completed.connect(self._on_pomodoro_completed)
        self.timer.session_completed.connect(self._on_session_completed)

        # 工具栏
        self.action_settings.triggered.connect(self._show_settings)
        self.action_noise.triggered.connect(self._toggle_noise)
        self.action_always_top.triggered.connect(self._toggle_always_top)

    def _on_start_click(self):
        state = self.timer.state
        if state == TimerState.IDLE:
            self.timer.start_work()
        elif state == TimerState.PAUSED:
            self.timer.resume()
        elif state in (TimerState.WORK, TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            self.timer.pause()

    def _on_skip_click(self):
        if self.timer.state != TimerState.IDLE:
            self.timer.skip()

    def _on_reset_click(self):
        self.timer.reset()

    def _on_tick(self, remaining: int, total: int):
        self.progress.set_time(remaining, total)

    def _on_state_changed(self, state_str: str):
        self._update_state_visuals()
        self._update_buttons()

    def _on_pomodoro_completed(self):
        task_name = self.task_panel.get_current_task_name()
        record_pomodoro(task_name)
        self._update_pomodoro_display()
        self.stats_panel.refresh()

    def _on_session_completed(self, session_type: str):
        if session_type == "work":
            self._show_notification("专注完成！", "休息一下吧~")
        else:
            self._show_notification("休息结束", "开始新的专注吧！")

    def _update_state_visuals(self):
        state = self.timer.state
        state_str = state.value if state != TimerState.PAUSED else (
            "work" if self.timer._paused_state == TimerState.WORK else "break"
        )

        primary, bg = get_state_colors(state_str)
        self.progress.set_colors(primary)

        state_texts = {
            TimerState.IDLE: "准备开始",
            TimerState.WORK: "专注中...",
            TimerState.SHORT_BREAK: "短休息",
            TimerState.LONG_BREAK: "长休息",
            TimerState.PAUSED: "已暂停",
        }
        self.progress.set_state_text(state_texts.get(state, ""))

    def _update_buttons(self):
        state = self.timer.state
        if state == TimerState.IDLE:
            self.btn_start.setText("开始专注")
            self.btn_start.setObjectName("primary_btn")
            self.btn_skip.setEnabled(False)
        elif state == TimerState.PAUSED:
            self.btn_start.setText("继续")
            self.btn_start.setObjectName("primary_btn")
            self.btn_skip.setEnabled(True)
        elif state == TimerState.WORK:
            self.btn_start.setText("暂停")
            self.btn_start.setObjectName("")
            self.btn_skip.setEnabled(True)
        else:
            self.btn_start.setText("暂停")
            self.btn_start.setObjectName("")
            self.btn_skip.setEnabled(True)

        # 重新应用样式
        self.btn_start.style().unpolish(self.btn_start)
        self.btn_start.style().polish(self.btn_start)

    def _update_pomodoro_display(self):
        count = get_today_count()
        self.pomodoro_label.setText(f"🍅 今日: {count} 个番茄")

    def _show_notification(self, title: str, message: str):
        if self.config.get("notification_enabled", True):
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon = QSystemTrayIcon(_create_icon(Colors.WORK_PRIMARY), self)
                self.tray_icon.show()
                self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)
            else:
                QMessageBox.information(self, title, message)

    def _show_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_():
            self.config = dialog.get_config()
            save_config(self.config)
            self.timer.config = self.config

    def _toggle_noise(self):
        current = self.config.get("white_noise", "none")
        noises = ["none", "rain", "cafe", "forest"]
        idx = noises.index(current) if current in noises else 0
        next_noise = noises[(idx + 1) % len(noises)]
        self.config["white_noise"] = next_noise
        save_config(self.config)
        labels = {"none": "关", "rain": "雨声", "cafe": "咖啡厅", "forest": "森林"}
        self.action_noise.setText(f"🔊 白噪音: {labels.get(next_noise, '关')}")

    def _toggle_always_top(self):
        self.config["always_on_top"] = not self.config["always_on_top"]
        save_config(self.config)
        flags = self.windowFlags()
        if self.config["always_on_top"]:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self.action_always_top.setText("📌 置顶: 开")
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            self.action_always_top.setText("📌 置顶: 关")
        self.show()

    def closeEvent(self, event):
        if QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            if not hasattr(self, '_tray') or not self._tray.isVisible():
                self._setup_tray()
                self._tray.showMessage(
                    "番茄钟",
                    "应用已最小化到系统托盘",
                    QSystemTrayIcon.Information, 2000
                )
        else:
            event.accept()

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(_create_icon(Colors.WORK_PRIMARY), self)
        menu = QMenu()
        show_action = menu.addAction("显示窗口")
        show_action.triggered.connect(self.show)
        menu.addSeparator()

        start_action = menu.addAction("开始/暂停")
        start_action.triggered.connect(self._on_start_click)

        reset_action = menu.addAction("重置")
        reset_action.triggered.connect(self._on_reset_click)
        menu.addSeparator()

        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(QApplication.quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
