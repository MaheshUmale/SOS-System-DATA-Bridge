import asyncio
import json
import websockets
import unittest

class TestContract(unittest.TestCase):
    def assert_base_structure(self, data):
        self.assertIn("type", data)
        self.assertIn("timestamp", data)
        self.assertIsInstance(data["timestamp"], int)
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], dict)

    def assert_candle_structure(self, candle):
        self.assertIn("open", candle)
        self.assertIn("high", candle)
        self.assertIn("low", candle)
        self.assertIn("close", candle)
        self.assertIn("volume", candle)
        self.assertIsInstance(candle["open"], float)
        self.assertIsInstance(candle["high"], float)
        self.assertIsInstance(candle["low"], float)
        self.assertIsInstance(candle["close"], float)
        self.assertIsInstance(candle["volume"], int)

    def assert_candle_update_structure(self, data):
        self.assert_base_structure(data)
        self.assertEqual(data["type"], "CANDLE_UPDATE")
        data_payload = data["data"]
        self.assertIn("symbol", data_payload)
        self.assertIn("candle", data_payload)
        self.assert_candle_structure(data_payload["candle"])

    def assert_sentiment_update_structure(self, data):
        self.assert_base_structure(data)
        self.assertEqual(data["type"], "SENTIMENT_UPDATE")
        data_payload = data["data"]
        self.assertIn("regime", data_payload)
        self.assertIn("pcr", data_payload)
        self.assertIn("advances", data_payload)
        self.assertIn("declines", data_payload)
        self.assertIsInstance(data_payload["regime"], str)
        self.assertIsInstance(data_payload["pcr"], float)
        self.assertIsInstance(data_payload["advances"], int)
        self.assertIsInstance(data_payload["declines"], int)

    def assert_market_update_structure(self, data):
        self.assert_base_structure(data)
        self.assertEqual(data["type"], "MARKET_UPDATE")
        data_payload = data["data"]
        self.assertIn("symbol", data_payload)
        self.assertIn("candle", data_payload)
        self.assertIn("sentiment", data_payload)
        self.assert_candle_structure(data_payload["candle"])
        sentiment_payload = data_payload["sentiment"]
        self.assertIn("pcr", sentiment_payload)
        self.assertIn("regime", sentiment_payload)
        self.assertIsInstance(sentiment_payload["pcr"], float)
        self.assertIsInstance(sentiment_payload["regime"], str)

    def assert_option_chain_update_structure(self, data):
        self.assert_base_structure(data)
        self.assertEqual(data["type"], "OPTION_CHAIN_UPDATE")
        data_payload = data["data"]
        self.assertIn("symbol", data_payload)
        self.assertIn("chain", data_payload)
        self.assertIsInstance(data_payload["chain"], list)
        if data_payload["chain"]:
            strike = data_payload["chain"][0]
            self.assertIn("strike", strike)
            self.assertIn("call_oi_chg", strike)
            self.assertIn("put_oi_chg", strike)
            self.assertIsInstance(strike["strike"], (int, float))
            self.assertIsInstance(strike["call_oi_chg"], int)
            self.assertIsInstance(strike["put_oi_chg"], int)

    def test_candle_update(self):
        async def run_test():
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Wait for a CANDLE_UPDATE message
                for _ in range(10):  # Try a few times
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("type") == "CANDLE_UPDATE":
                        self.assert_candle_update_structure(data)
                        return
                self.fail("Did not receive CANDLE_UPDATE message in time.")

        asyncio.run(run_test())

    def test_option_chain_update(self):
        async def run_test():
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Wait for a OPTION_CHAIN_UPDATE message
                for _ in range(10):  # Try a few times
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("type") == "OPTION_CHAIN_UPDATE":
                        self.assert_option_chain_update_structure(data)
                        return
                self.fail("Did not receive OPTION_CHAIN_UPDATE message in time.")

        asyncio.run(run_test())

    def test_sentiment_update(self):
        async def run_test():
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Wait for a SENTIMENT_UPDATE message
                for _ in range(10):  # Try a few times
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("type") == "SENTIMENT_UPDATE":
                        self.assert_sentiment_update_structure(data)
                        return
                self.fail("Did not receive SENTIMENT_UPDATE message in time.")

        asyncio.run(run_test())

    def test_market_update(self):
        async def run_test():
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Wait for a MARKET_UPDATE message
                for _ in range(10):  # Try a few times
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("type") == "MARKET_UPDATE":
                        self.assert_market_update_structure(data)
                        return
                self.fail("Did not receive MARKET_UPDATE message in time.")

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
