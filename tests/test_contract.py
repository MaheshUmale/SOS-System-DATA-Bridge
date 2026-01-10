import asyncio
import json
import websockets
import unittest

class TestContract(unittest.TestCase):
    def test_candle_update(self):
        async def run_test():
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Send a mock CANDLE_UPDATE message
                await websocket.send(json.dumps({
                    "type": "CANDLE_UPDATE",
                    "timestamp": 1704711600000,
                    "data": {
                        "symbol": "NIFTY_BANK",
                        "candle": {
                            "open": 48100.50,
                            "high": 48250.00,
                            "low": 48050.25,
                            "close": 48150.75,
                            "volume": 150000
                        }
                    }
                }))
                # For this test, we are just checking if the message is sent without error.
                # A more advanced test could check for a response or a state change in the core engine.
                self.assertTrue(True)
        asyncio.run(run_test())

    def test_sentiment_update(self):
        async def run_test():
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Send a mock SENTIMENT_UPDATE message
                await websocket.send(json.dumps({
                    "type": "SENTIMENT_UPDATE",
                    "timestamp": 1704711660000,
                    "data": {
                        "regime": "BEARISH"
                    }
                }))
                # For this test, we are just checking if the message is sent without error.
                self.assertTrue(True)
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
