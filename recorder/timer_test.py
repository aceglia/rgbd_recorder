# test Qtimer

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtCore import QTimer

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Timer Test")
        self.setGeometry(100, 100, 300, 300)
        self.button = QPushButton("Start Timer", self)
        self.button.move(100, 100)
        self.button.clicked.connect(self.start_timer)
        self.timer = None
    def start_timer(self):
        if self.timer is None:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.on_timeout)
            self.timer.start(1000)
            self.button.setText("Stop Timer")
        else:
            self.timer.stop()
            self.timer = None
            self.button.setText("Start Timer")

    def on_timeout(self):
        print("Timer timeout")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
