import sys
import asyncio
import websockets
import json
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QHBoxLayout, QFrame
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt, QSize
import threading


MICROCOMPUTER_IP = "127.0.0.1"
WS_PORT = 8080
CAMERA_INDEX = 0

class RobotControlGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.cap = cv2.VideoCapture(CAMERA_INDEX)  # Use USB Arducam
        self.initUI()

        self.websocket_thread = threading.Thread(target=self.start_websocket_listener, daemon=True)
        self.websocket_thread.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_camera_feed)
        self.timer.start(30)

    def initUI(self):
        main_layout = QVBoxLayout()

        
        self.camera_label = QLabel("Camera Feed Not Available")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setFixedSize(600, 480)  # Set fixed size to prevent distortion
        main_layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Bottom Half Layout
        bottom_layout = QHBoxLayout()

        # Connection Status (Left Side)
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(self.status_label)

        # D-Pad Controls (Right Side)
        dpad_layout = QVBoxLayout()
        self.up_button = QPushButton("▲")
        self.down_button = QPushButton("▼")
        self.left_button = QPushButton("◀")
        self.right_button = QPushButton("▶")
        self.stop_button = QPushButton("■")

        move_layout = QVBoxLayout()
        move_layout.addWidget(self.up_button, alignment=Qt.AlignmentFlag.AlignCenter)
        move_layout.addWidget(self.stop_button, alignment=Qt.AlignmentFlag.AlignCenter)
        move_layout.addWidget(self.down_button, alignment=Qt.AlignmentFlag.AlignCenter)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.left_button)
        control_layout.addLayout(move_layout)
        control_layout.addWidget(self.right_button)

        dpad_layout.addLayout(control_layout)
        bottom_layout.addLayout(dpad_layout)
        main_layout.addLayout(bottom_layout)

        # Set Main Layout
        self.setLayout(main_layout)
        self.setWindowTitle("Remote Robot Arm Control")
        self.setGeometry(100, 100, 800, 600)

        # Connect buttons to functions
        self.up_button.clicked.connect(lambda: self.send_command("UP"))
        self.down_button.clicked.connect(lambda: self.send_command("DOWN"))
        self.left_button.clicked.connect(lambda: self.send_command("LEFT"))
        self.right_button.clicked.connect(lambda: self.send_command("RIGHT"))
        self.stop_button.clicked.connect(lambda: self.send_command("STOP"))

    def update_camera_feed(self):
        """Fetches a frame from the Arducam and updates the QLabel"""
        if self.cap is None or not self.cap.isOpened():
            self.camera_label.setText("Camera not available")
            return

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (600, 480))  # Resize frame to fixed size
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.camera_label.setPixmap(pixmap)
        else:
            self.camera_label.setText("Failed to load camera feed")

    def send_command(self, command):
        """Send movement commands to the microcomputer"""
        asyncio.run(self.websocket_send(command))


    def start_websocket_listener(self):
        """Starts a WebSocket listener in a separate thread"""
        asyncio.run(self.websocket_receive())

    async def websocket_receive(self):
        """Receives real-time sensor data from the microcomputer"""
        while True:
            try:
                async with websockets.connect(f"ws://{MICROCOMPUTER_IP}:{WS_PORT}") as websocket:
                    # Update connection status to Connected with IP
                    self.update_status_label(f"Connected to: {MICROCOMPUTER_IP}:{WS_PORT}")
                    print(f"Connected to server: {MICROCOMPUTER_IP}:{WS_PORT}")
                    
                    while True:
                        data = await websocket.recv()
                        print("Received:", data)
            except Exception as e:
                # Update connection status to Disconnected
                self.update_status_label(f"Disconnected: {str(e)}")
                print("Connection Lost:", str(e))
                await asyncio.sleep(5)  # Wait 5 seconds before trying to reconnect

    def update_status_label(self, status_text):
        """Update connection status display on GUI (thread-safe)"""
        # We need to use a thread-safe method to update the GUI from another thread
        if hasattr(self, 'status_label'):
            # Use invokeMethod or equivalent to update label from non-GUI thread
            self.status_label.setText(status_text)

    async def websocket_send(self, command):  # Fix: Proper indentation + add self parameter
        """WebSocket client to send data to the microcomputer"""
        try:
            async with websockets.connect(f"ws://{MICROCOMPUTER_IP}:{WS_PORT}") as websocket:
                await websocket.send(command)
                print("Command Sent:", command)
        except Exception as e:
            print("Connection Failed:", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RobotControlGUI()
    window.show()
    sys.exit(app.exec())
