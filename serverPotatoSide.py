import asyncio
import websockets
import cv2
import serial
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8080
connected_clients = set()

# Camera setup
CAMERA_INDEX = 0
FRAME_INTERVAL = 0.1  # seconds between frames (10 FPS)

# Arduino Serial setup
SERIAL_PORT = "/dev/ttyACM0"  # Change this to your Arduino Mega port
BAUD_RATE = 115200
serial_conn = None

# Movement configuration
MOVEMENT_SPEED = 100  # Default movement speed (mm/min)
MOVEMENT_DISTANCE = 10  # Default movement distance (mm)

async def initialize_serial():
    """Initialize the serial connection to Arduino Mega."""
    global serial_conn
    try:
        serial_conn = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Serial connection established on {SERIAL_PORT}")
        await asyncio.sleep(2)  # Wait for Arduino to reset after connection
        send_gcode("G90")  # Set absolute positioning
        return True
    except Exception as e:
        print(f"Failed to open serial connection: {e}")
        return False

def send_gcode(gcode):
    """Send GCODE command to Arduino."""
    if serial_conn and serial_conn.is_open:
        command = f"{gcode}\n"
        print(f"Sending GCODE: {gcode}")
        serial_conn.write(command.encode())
        response = serial_conn.readline().decode().strip()
        print(f"Arduino response: {response}")
        return response
    else:
        print("Serial connection not available")
        return None

def movement_to_gcode(command):
    """Convert direction command to GCODE."""
    if command == "STOP":
        return "M410"  # Emergency stop
    
    # New axis controls (X+, X-, Y+, Y-, Z+, Z-, A+, A-)
    if len(command) == 2 and command[0] in "XYZA" and command[1] in "+-":
        axis = command[0]
        direction = 1 if command[1] == "+" else -1
        distance = MOVEMENT_DISTANCE * direction
        
        # Create movement command for the specified axis
        return f"G1 {axis}{distance} F{MOVEMENT_SPEED}"
    
    # Keep backward compatibility with old UP, DOWN, LEFT, RIGHT commands
    elif command == "UP":
        return f"G1 Y{MOVEMENT_DISTANCE} F{MOVEMENT_SPEED}"
    elif command == "DOWN":
        return f"G1 Y-{MOVEMENT_DISTANCE} F{MOVEMENT_SPEED}"
    elif command == "LEFT":
        return f"G1 X-{MOVEMENT_DISTANCE} F{MOVEMENT_SPEED}"
    elif command == "RIGHT":
        return f"G1 X{MOVEMENT_DISTANCE} F{MOVEMENT_SPEED}"
    else:
        return None

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
            # Handle axis controls (X+, X-, Y+, Y-, Z+, Z-, A+, A-)
            elif (len(message) == 2 and 
                  message[0] in "XYZA" and 
                  message[1] in "+-"):
                gcode = movement_to_gcode(message)
                if gcode:
                    response = send_gcode(gcode)
                    await websocket.send(f"STATUS:Command {message} executed ({gcode})")
                else:
                    await websocket.send(f"STATUS:Invalid command {message}")
            # Handle legacy movement commands
            elif message in ["UP", "DOWN", "LEFT", "RIGHT", "STOP"]:
                # Convert movement command to GCODE and send to Arduino
                gcode = movement_to_gcode(message)
                if gcode:
                    response = send_gcode(gcode)
                    await websocket.send(f"STATUS:Command {message} executed ({gcode})")
                else:
                    await websocket.send(f"STATUS:Invalid command {message}")
            elif message.startswith("SET_SPEED:"):
                try:
                    global MOVEMENT_SPEED
                    MOVEMENT_SPEED = int(message.split(":")[1])
                    await websocket.send(f"STATUS:Movement speed set to {MOVEMENT_SPEED}")
                except Exception as e:
                    await websocket.send(f"STATUS:Error setting speed: {e}")
            elif message.startswith("SET_DISTANCE:"):
                try:
                    global MOVEMENT_DISTANCE
                    MOVEMENT_DISTANCE = int(message.split(":")[1])
                    await websocket.send(f"STATUS:Movement distance set to {MOVEMENT_DISTANCE}")
                except Exception as e:
                    await websocket.send(f"STATUS:Error setting distance: {e}")
            elif message.startswith("GCODE:"):
                # Allow direct GCODE commands
                try:
                    raw_gcode = message.split(":", 1)[1]
                    response = send_gcode(raw_gcode)
                    await websocket.send(f"STATUS:GCODE executed: {raw_gcode}")
                except Exception as e:
                    await websocket.send(f"STATUS:Error executing GCODE: {e}")
            else:
                print(f"Unknown command: {message}")
                await websocket.send(f"STATUS:Unknown command: {message}")
                
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {client_id} disconnected")
    except Exception as e:
        print(f"Error handling client {client_id}: {e}")
    finally:
        connected_clients.remove(websocket)
        print(f"Client {client_id} removed from active connections")

async def main():
    """Starts the WebSocket server and video streaming."""
    # Initialize serial connection to Arduino
    if not await initialize_serial():
        print("Failed to initialize serial connection. Exiting.")
        return
        
    # Start video streaming in a separate task
    video_task = asyncio.create_task(send_video_frames())
    
    async with websockets.serve(handle_client, HOST, PORT):
        print(f"WebSocket server started on {HOST}:{PORT}")
        
        # Keep the server running
        try:
            await asyncio.Future()
        finally:
            video_task.cancel()
            # Close serial connection
            if serial_conn and serial_conn.is_open:
                serial_conn.close()
                print("Serial connection closed")
            try:
                await video_task
            except asyncio.CancelledError:
                print("Video streaming task cancelled")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user")
        # Ensure serial connection is closed
        if serial_conn and serial_conn.is_open:
            serial_conn.close()
    except Exception as e:
        print(f"Server error: {e}")
        # Ensure serial connection is closed
        if serial_conn and serial_conn.is_open:
            serial_conn.close()