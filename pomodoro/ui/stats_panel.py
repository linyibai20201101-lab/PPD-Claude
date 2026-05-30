from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QFont

from history import get_today_count, get_week_count, get_total_count, get_history


class BarChart(QWidget):
    """简单的柱状图组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # list of (label, value)
        self._bar_color = QColor(231, 76, 60)
        self.setMinimumHeight(120)

    def set_data(self, data: list, color: QColor = None):
        self._data = data
        if color:
            self._bar_color = color
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        max_val = max(d[1] for d in self._data) or 1
        bar_count = len(self._data)
        bar_width = max(8, (w - 20) // bar_count - 6)
        gap = 6
        start_x = (w - (bar_width + gap) * bar_count + gap) // 2

        for i, (label, value) in enumerate(self._data):
            x = start_x + i * (bar_width + gap)
            bar_h = int((value / max_val) * (h - 30)) if max_val > 0 else 0
            y = h - 22 - bar_h

            # 柱子
            painter.setBrush(self._bar_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_width, bar_h, 3, 3)

            # 标签
            painter.setPen(QColor(140, 140, 140))
            font = QFont("Segoe UI", 8)
            painter.setFont(font)
            painter.drawText(x - 2, h - 4, bar_width + 4, 16, Qt.AlignCenter, label[-2:])

            # 数值
            if value > 0:
                painter.setPen(QColor(80, 80, 80))
                painter.drawText(x - 2, y - 14, bar_width + 4, 14, Qt.AlignCenter, str(value))

        painter.end()


class StatCard(QFrame):
    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            StatCard {
                background: white;
                border: 1px solid #e8e8e8;
                border-radius: 10px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 10, 12, 10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("secondary_label")
        self.title_label.setStyleSheet("font-size: 11px; color: #999; border: none;")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #323232; border: none;")
        layout.addWidget(self.value_label)

    def update_value(self, value: str):
        self.value_label.setText(value)


class StatsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("📊 统计")
        title.setStyleSheet("font-size: 15px; font-weight: bold; margin-bottom: 4px;")
        layout.addWidget(title)

        self.card_today = StatCard("今日番茄", "0")
        self.card_week = StatCard("本周番茄", "0")
        self.card_total = StatCard("总计番茄", "0")

        layout.addWidget(self.card_today)
        layout.addWidget(self.card_week)
        layout.addWidget(self.card_total)

        # 柱状图
        chart_label = QLabel("近 7 天")
        chart_label.setObjectName("secondary_label")
        chart_label.setStyleSheet("font-size: 12px; color: #999; margin-top: 8px;")
        layout.addWidget(chart_label)

        self.chart = BarChart()
        layout.addWidget(self.chart)

        layout.addStretch()

    def refresh(self):
        today = get_today_count()
        week = get_week_count()
        total = get_total_count()

        self.card_today.update_value(str(today))
        self.card_week.update_value(str(week))
        self.card_total.update_value(str(total))

        history = get_history(7)
        data = [(h["date"], h["count"]) for h in history]
        from .styles import Colors
        self.chart.set_data(data, Colors.WORK_PRIMARY)
