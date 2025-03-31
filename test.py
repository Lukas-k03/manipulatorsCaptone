import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer

class ArduCamViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.cap = cv2.VideoCapture(0)  # Change the index if needed
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update frame every 30ms

    def initUI(self):
        self.setWindowTitle("Arducam Viewer")
        self.setGeometry(100, 100, 640, 480)
        self.label = QLabel(self)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(q_img))

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ArduCamViewer()
    viewer.show()
    sys.exit(app.exec())