"""
main.py — Entry point for Hand & Eye HCI Controller
Run: python main.py
"""
import sys
import os

# Make sure project root is in Python path
PROJECT_ROOT = os.path.dirname(__file__)
sys.path.insert(0, PROJECT_ROOT)

# MediaPipe's native DLLs can fail to initialize if PyQt loads first on Windows.
MPLCONFIGDIR = os.path.join(PROJECT_ROOT, ".matplotlib")
os.makedirs(MPLCONFIGDIR, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", MPLCONFIGDIR)
import mediapipe  # noqa: F401

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI HCI Controller")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
