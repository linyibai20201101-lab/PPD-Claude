import sys
import os

# 确保模块可以被找到
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.main_window import MainWindow
from ui.styles import LIGHT_STYLE


def main():
    # 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("番茄钟")
    app.setStyle("Fusion")

    # 设置默认字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    app.setStyleSheet(LIGHT_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
