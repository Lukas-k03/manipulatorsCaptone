import sys
import asyncio
import websockets
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QFrame
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt
import threading

MICROCOMPUTER_IP = "10.221.85.33"
WS_PORT = 8080
CAMERA_INDEX = 0  # Kept for fallback but not used by default

class potatoControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.websocket = None
        self.loop = None  # for async commands
        self.latest_frame = None
        self.frame_received = False
        self.initUI()

        self.websocket_thread = threading.Thread(target=self.run_websocket_loop, daemon=True)
        self.websocket_thread.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_camera_feed)
        self.timer.start(30)

    def initUI(self):
        main_layout = QVBoxLayout()

        self.camera_label = QLabel("Waiting for camera feed from potato...")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setFixedSize(600, 480)
        main_layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)

        bottom_layout = QHBoxLayout()

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(self.status_label)

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

        self.setLayout(main_layout)
        self.setWindowTitle("Remote Potato Control")
        self.setGeometry(100, 100, 800, 600)

        self.up_button.clicked.connect(lambda: self.queue_command("UP"))
        self.down_button.clicked.connect(lambda: self.queue_command("DOWN"))
        self.left_button.clicked.connect(lambda: self.queue_command("LEFT"))
        self.right_button.clicked.connect(lambda: self.queue_command("RIGHT"))
        self.stop_button.clicked.connect(lambda: self.queue_command("STOP"))

    def update_camera_feed(self):
        if self.frame_received and self.latest_frame is not None:
            # We already have a frame from websocket, just display it
            self.camera_label.setPixmap(self.latest_frame)
        else:
            # If we haven't received frames from websocket, just display the waiting message
            if not hasattr(self, 'waiting_displayed'):
                self.camera_label.setText("Waiting for video stream from potato...")
                self.waiting_displayed = True

    def run_websocket_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.websocket_handler())

    async def websocket_handler(self):
        while True:
            try:
                async with websockets.connect(f"ws://{MICROCOMPUTER_IP}:{WS_PORT}") as ws:
                    self.websocket = ws
                    self.update_status_label(f"Connected to {MICROCOMPUTER_IP}:{WS_PORT}")
                    print("WebSocket connected.")

                    # Create tasks for sending heartbeats and receiving messages
                    heartbeat_task = asyncio.create_task(self.send_heartbeat(ws))
                    receive_task = asyncio.create_task(self.receive_messages(ws))
                    
                    # Wait for either task to complete (if one fails, we'll reconnect)
                    await asyncio.gather(heartbeat_task, receive_task)
            except Exception as e:
                print("WebSocket error:", e)
                self.websocket = None
                self.update_status_label("Disconnected - Retrying...")
                await asyncio.sleep(5)

    async def receive_messages(self, ws):
        try:
            while True:
                try:
                    message = await ws.recv()
                    
                    # Check if it's binary data (likely video frame)
                    if isinstance(message, bytes):
                        self.process_video_frame(message)
                    else:
                        # Handle text messages (could be status updates from potato)
                        print(f"Received text message: {message}")
                        # Update status if it's a status message
                        if message.startswith("STATUS:"):
                            self.update_status_label(message[7:])  # Remove "STATUS:" prefix
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                    break
        except Exception as e:
            print(f"Error receiving messages: {e}")
            raise  # Re-raise to trigger reconnection

    def process_video_frame(self, frame_data):
        try:
            # Decode the received bytes into an image
            # This assumes JPEG encoding - adjust if your potato sends a different format
            np_arr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (600, 480))
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                
                # Store the frame for the timer to display
                self.latest_frame = pixmap
                self.frame_received = True
        except Exception as e:
            print(f"Error processing video frame: {e}")

    def queue_command(self, command):
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.send_command(command), self.loop)

    async def send_command(self, command):
        try:
            if self.websocket:
                await self.websocket.send(command)
                print("Command sent:", command)
            else:
                print("WebSocket not connected.")
                self.update_status_label("Disconnected - Can't send commands")
        except Exception as e:
            print("Send command failed:", e)

    async def send_heartbeat(self, ws):
        try:
            while True:
                try:
                    await ws.send("PING")
                    print("Heartbeat: PING")
                    await asyncio.sleep(10)
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed during heartbeat")
                    break
        except Exception as e:
            print("Heartbeat failed:", e)
            raise  # Re-raise to trigger reconnection

    def update_status_label(self, text):
        # Use QTimer.singleShot to safely update UI from non-GUI thread
        QTimer.singleShot(0, lambda: self.status_label.setText(f"Status: {text}"))

    def closeEvent(self, event):
        # Clean up when the window is closed
        print("Closing application...")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = potatoControlGUI()
    window.show()
    sys.exit(app.exec())