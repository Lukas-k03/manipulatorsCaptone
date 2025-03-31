import asyncio
import websockets

# Server settings
HOST = "127.0.0.1"  # Restrict the WebSocket server to local connections
PORT = 8080

async def handle_client(websocket):
    """Handles incoming WebSocket connections."""
    print(f"New connection from {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"Received: {message}")  # Print the received command in the terminal
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    """Starts the WebSocket server."""
    async with websockets.serve(handle_client, HOST, PORT):
        print(f"WebSocket server started on {HOST}:{PORT}")
        await asyncio.Future()  # Keep the server running

if __name__ == "__main__":
    asyncio.run(main())