from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient


class CircularProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._max_progress = 100.0
        self._line_width = 12
        self._bg_color = QColor(220, 220, 220)
        self._progress_color = QColor(231, 76, 60)  # 番茄红
        self._text_color = QColor(50, 50, 50)
        self._time_text = "00:00"
        self._state_text = "准备开始"
        self.setMinimumSize(250, 250)

        self._animation = QPropertyAnimation(self, b"progress")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

    def get_progress(self):
        return self._progress

    def set_progress(self, value):
        self._progress = value
        self.update()

    progress = pyqtProperty(float, get_progress, set_progress)

    def set_colors(self, progress_color: QColor, bg_color: QColor = None):
        self._progress_color = progress_color
        if bg_color:
            self._bg_color = bg_color
        self.update()

    def set_time(self, seconds: int, total: int):
        if total > 0:
            new_progress = ((total - seconds) / total) * self._max_progress
            self._animation.stop()
            self._animation.setStartValue(self._progress)
            self._animation.setEndValue(new_progress)
            self._animation.start()
        mins, secs = divmod(max(0, seconds), 60)
        self._time_text = f"{mins:02d}:{secs:02d}"
        self.update()

    def set_state_text(self, text: str):
        self._state_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        size = min(self.width(), self.height())
        margin = self._line_width + 10
        rect = QRectF(
            (self.width() - size) / 2 + margin,
            (self.height() - size) / 2 + margin,
            size - margin * 2,
            size - margin * 2,
        )

        # 背景圆环
        pen = QPen(self._bg_color, self._line_width, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        # 进度圆环
        pen.setColor(self._progress_color)
        painter.setPen(pen)
        span_angle = int(-(self._progress / self._max_progress) * 360 * 16)
        painter.drawArc(rect, 90 * 16, span_angle)

        # 时间文字
        painter.setPen(self._text_color)
        time_font = QFont("Segoe UI", 36, QFont.Bold)
        painter.setFont(time_font)
        text_rect = QRectF(rect)
        text_rect.adjust(0, -15, 0, 0)
        painter.drawText(text_rect, Qt.AlignCenter, self._time_text)

        # 状态文字
        state_font = QFont("Microsoft YaHei", 11)
        painter.setFont(state_font)
        state_rect = QRectF(rect)
        state_rect.adjust(0, 35, 0, 0)
        painter.setPen(QColor(120, 120, 120))
        painter.drawText(state_rect, Qt.AlignCenter, self._state_text)

        painter.end()
