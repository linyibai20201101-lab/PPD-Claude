from PyQt5.QtGui import QColor


# 色彩定义
class Colors:
    # 工作状态 - 番茄红
    WORK_PRIMARY = QColor(231, 76, 60)
    WORK_BG = QColor(253, 237, 236)

    # 短休息 - 清新绿
    BREAK_PRIMARY = QColor(46, 204, 113)
    BREAK_BG = QColor(234, 250, 241)

    # 长休息 - 宁静蓝
    LONG_BREAK_PRIMARY = QColor(52, 152, 219)
    LONG_BREAK_BG = QColor(232, 245, 253)

    # 空闲状态
    IDLE_PRIMARY = QColor(149, 165, 166)
    IDLE_BG = QColor(236, 240, 241)

    # 通用
    TEXT_PRIMARY = QColor(50, 50, 50)
    TEXT_SECONDARY = QColor(120, 120, 120)
    TEXT_LIGHT = QColor(180, 180, 180)
    WHITE = QColor(255, 255, 255)
    SURFACE = QColor(255, 255, 255)
    BORDER = QColor(230, 230, 230)
    DANGER = QColor(231, 76, 60)


def get_state_colors(state: str):
    if state == "work":
        return Colors.WORK_PRIMARY, Colors.WORK_BG
    elif state == "short_break":
        return Colors.BREAK_PRIMARY, Colors.BREAK_BG
    elif state == "long_break":
        return Colors.LONG_BREAK_PRIMARY, Colors.LONG_BREAK_BG
    return Colors.IDLE_PRIMARY, Colors.IDLE_BG


LIGHT_STYLE = """
QMainWindow {
    background-color: #fafafa;
}
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    color: #323232;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
    color: #323232;
}
QPushButton:hover {
    background-color: #f5f5f5;
    border-color: #ccc;
}
QPushButton:pressed {
    background-color: #e8e8e8;
}
QPushButton#primary_btn {
    background-color: #e74c3c;
    color: white;
    border: none;
}
QPushButton#primary_btn:hover {
    background-color: #c0392b;
}
QPushButton#danger_btn {
    background-color: #e74c3c;
    color: white;
    border: none;
}
QPushButton#danger_btn:hover {
    background-color: #c0392b;
}
QPushButton#success_btn {
    background-color: #2ecc71;
    color: white;
    border: none;
}
QPushButton#success_btn:hover {
    background-color: #27ae60;
}
QLineEdit {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    background: white;
}
QLineEdit:focus {
    border-color: #3498db;
}
QListWidget {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: white;
    outline: none;
}
QListWidget::item {
    padding: 10px 14px;
    border-bottom: 1px solid #f0f0f0;
}
QListWidget::item:selected {
    background: #f0f7ff;
    color: #323232;
}
QListWidget::item:hover {
    background: #f8f8f8;
}
QLabel {
    color: #323232;
}
QLabel#secondary_label {
    color: #787878;
    font-size: 12px;
}
QSpinBox {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
}
QGroupBox {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QCheckBox {
    spacing: 8px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
QComboBox {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
"""
