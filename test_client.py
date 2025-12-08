import asyncio
import websockets
import json
from datetime import datetime

# *** Use the CORRECT port 8000 ***
URI = "ws://127.0.0.1:8000/ws/gold_price"

async def listen_for_prices():
    print("Starting WebSocket client...")
    try:
        # Use a timeout to diagnose connection issues
        async with websockets.connect(URI, open_timeout=5) as websocket:
            print("✅ Connection established to FastAPI server. Waiting for price broadcasts...")
            print("-" * 50)
            while True:
                # Use a specific timeout for receiving data (optional, but good practice)
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30) 
                    data = json.loads(message)
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] RECEIVED: Price = {data['price']}")
                
                except asyncio.TimeoutError:
                    # This happens if no new message is sent after 30 seconds
                    print("Still connected, but no new data received in 30 seconds (Market likely static).")
                except websockets.exceptions.ConnectionClosedOK:
                    print("Server closed connection normally.")
                    break

    except ConnectionRefusedError:
        print(f"❌ CONNECTION REFUSED. Is Uvicorn running on port 8000?")
    except websockets.exceptions.InvalidURI:
        print("❌ INVALID URI. Check the ws:// protocol and port 8000.")
    except Exception as e:
        print(f"An unexpected error occurred during connection: {type(e).__name__}: {e}")

if __name__ == "__main__":
    # This runs the async function and keeps the script alive until completion/error
    asyncio.run(listen_for_prices())