import asyncio
import websockets
import cv2
import base64
import json
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8080
connected_clients = set()

# Camera setup
CAMERA_INDEX = 0
FRAME_INTERVAL = 0.1  # seconds between frames (10 FPS)

async def send_video_frames():
    """Captures frames from camera and sends to all connected clients."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    print(f"Camera opened successfully: {CAMERA_INDEX}")
    
    try:
        while True:
            # Skip if no clients connected to save resources
            if not connected_clients:
                await asyncio.sleep(0.5)
                continue
                
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                await asyncio.sleep(0.5)
                continue
                
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            jpeg_bytes = buffer.tobytes()
            
            # Send frame to all connected clients
            websockets_tasks = []
            for websocket in connected_clients:
                websockets_tasks.append(
                    asyncio.create_task(
                        send_frame_to_client(websocket, jpeg_bytes)
                    )
                )
                
            if websockets_tasks:
                await asyncio.gather(*websockets_tasks, return_exceptions=True)
                
            # Control frame rate
            await asyncio.sleep(FRAME_INTERVAL)
    finally:
        cap.release()
        print("Camera released")

async def send_frame_to_client(websocket, frame_data):
    """Sends a frame to a specific client."""
    try:
        await websocket.send(frame_data)
    except websockets.exceptions.ConnectionClosed:
        # The handler will clean up the client
        pass
    except Exception as e:
        print(f"Error sending frame: {e}")

async def handle_client(websocket):
    """Handles incoming WebSocket connections."""
    connected_clients.add(websocket)
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    print(f"New connection from {client_id}")
    
    try:
        # Send welcome message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await websocket.send(f"STATUS:Connected to potato camera server at {timestamp}")
        
        # Handle incoming messages
        async for message in websocket:
            print(f"Received from {client_id}: {message}")
            
            # Process commands
            if message == "PING":
                await websocket.send("PONG")
            elif message in ["UP", "DOWN", "LEFT", "RIGHT", "STOP"]:
                # Here you would control your potato based on the command
                print(f"Processing potato command: {message}")
                await websocket.send(f"STATUS:Command {message} executed")
            else:
                print(f"Unknown command: {message}")
                
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {client_id} disconnected")
    except Exception as e:
        print(f"Error handling client {client_id}: {e}")
    finally:
        connected_clients.remove(websocket)
        print(f"Client {client_id} removed from active connections")

async def main():
    """Starts the WebSocket server and video streaming."""
    # Start video streaming in a separate task
    video_task = asyncio.create_task(send_video_frames())
    
    async with websockets.serve(handle_client, HOST, PORT):
        print(f"WebSocket server started on {HOST}:{PORT}")
        
        # Keep the server running
        try:
            await asyncio.Future()
        finally:
            video_task.cancel()
            try:
                await video_task
            except asyncio.CancelledError:
                print("Video streaming task cancelled")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Server error: {e}")