from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSpinBox, QCheckBox, QComboBox, QPushButton,
    QGroupBox, QDialogButtonBox, QLabel,
)
from PyQt5.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle("设置")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 时长设置
        time_group = QGroupBox("时间设置 (分钟)")
        time_form = QFormLayout(time_group)

        self.spin_work = QSpinBox()
        self.spin_work.setRange(1, 120)
        self.spin_work.setValue(self.config["work_duration"])
        time_form.addRow("工作时长:", self.spin_work)

        self.spin_short = QSpinBox()
        self.spin_short.setRange(1, 30)
        self.spin_short.setValue(self.config["short_break"])
        time_form.addRow("短休息:", self.spin_short)

        self.spin_long = QSpinBox()
        self.spin_long.setRange(1, 60)
        self.spin_long.setValue(self.config["long_break"])
        time_form.addRow("长休息:", self.spin_long)

        self.spin_rounds = QSpinBox()
        self.spin_rounds.setRange(1, 10)
        self.spin_rounds.setValue(self.config["pomodoros_before_long"])
        time_form.addRow("长休息间隔:", self.spin_rounds)

        layout.addWidget(time_group)

        # 行为设置
        behavior_group = QGroupBox("行为")
        behavior_layout = QVBoxLayout(behavior_group)

        self.chk_auto_break = QCheckBox("自动开始休息")
        self.chk_auto_break.setChecked(self.config["auto_start_break"])
        behavior_layout.addWidget(self.chk_auto_break)

        self.chk_auto_work = QCheckBox("自动开始工作")
        self.chk_auto_work.setChecked(self.config["auto_start_work"])
        behavior_layout.addWidget(self.chk_auto_work)

        self.chk_notification = QCheckBox("系统通知")
        self.chk_notification.setChecked(self.config["notification_enabled"])
        behavior_layout.addWidget(self.chk_notification)

        self.chk_sound = QCheckBox("提示音")
        self.chk_sound.setChecked(self.config["sound_enabled"])
        behavior_layout.addWidget(self.chk_sound)

        layout.addWidget(behavior_group)

        # 白噪音
        noise_group = QGroupBox("白噪音")
        noise_form = QFormLayout(noise_group)

        self.combo_noise = QComboBox()
        self.combo_noise.addItems(["关闭", "雨声", "咖啡厅", "森林"])
        noise_map = {"none": 0, "rain": 1, "cafe": 2, "forest": 3}
        self.combo_noise.setCurrentIndex(
            noise_map.get(self.config.get("white_noise", "none"), 0)
        )
        noise_form.addRow("音效:", self.combo_noise)

        layout.addWidget(noise_group)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        self.config["work_duration"] = self.spin_work.value()
        self.config["short_break"] = self.spin_short.value()
        self.config["long_break"] = self.spin_long.value()
        self.config["pomodoros_before_long"] = self.spin_rounds.value()
        self.config["auto_start_break"] = self.chk_auto_break.isChecked()
        self.config["auto_start_work"] = self.chk_auto_work.isChecked()
        self.config["notification_enabled"] = self.chk_notification.isChecked()
        self.config["sound_enabled"] = self.chk_sound.isChecked()

        noise_map = {0: "none", 1: "rain", 2: "cafe", 3: "forest"}
        self.config["white_noise"] = noise_map.get(self.combo_noise.currentIndex(), "none")

        return self.config
