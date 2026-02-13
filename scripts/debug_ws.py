
import asyncio

import websockets


async def test_ws():
    print(f"websockets version: {websockets.__version__}")
    url = "wss://echo.websocket.org"
    try:
        async with websockets.connect(url) as ws:
            print(f"Type of ws: {type(ws)}")
            print(f"Dir of ws: {dir(ws)}")
            print(f"Has 'open' attr: {hasattr(ws, 'open')}")
            print(f"State: {ws.state}")
            from websockets.protocol import State
            print(f"Is Open? {ws.state == State.OPEN}")
    except Exception as e:
        print(f"Connection failed (expected if no internet/proxy): {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
