import asyncio
import websockets
import json
import sqlite3
import argparse
from datetime import datetime, timedelta

class MinimalReplayEngine:
    def __init__(self, target_date, port=8765, speed=1, start_time="09:15", end_time="15:30"):
        self.target_date = target_date
        self.port = port
        self.speed = speed
        self.start_time = start_time
        self.end_time = end_time
        self.db_path = "backtest_data.db"
        self.clients = set()

    def _load_candles(self, current_time_str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM backtest_candles WHERE date=? AND timestamp=?", (self.target_date, current_time_str))
        rows = cursor.fetchall()
        conn.close()
        
        updates = []
        for row in rows:
            # Schema: symbol, date, ts, open, high, low, close, volume, source
            symbol = row[0]
            # Convert to epoch ms
            dt = datetime.strptime(f"{self.target_date} {current_time_str}", "%Y-%m-%d %H:%M")
            ts_ms = int(dt.timestamp() * 1000)
            
            updates.append({
                "symbol": symbol,
                "timestamp": ts_ms,
                "1m": {
                    "open": row[3],
                    "high": row[4],
                    "low": row[5],
                    "close": row[6],
                    "volume": row[7],
                    "vwap": row[6]
                },
                "pcr": 1.0 # Dummy
            })
        return updates

    async def broadcast(self, update_data, current_ts_ms):
        if not update_data: return
        message = {
            "type": "CANDLE_UPDATE",
            "timestamp": current_ts_ms,
            "data": update_data
        }
        if self.clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in self.clients],
                return_exceptions=True
            )

    async def replay_loop(self):
        print(f"\n[Replay] Starting: {self.start_time} -> {self.end_time} ({self.speed}x)")
        current_dt = datetime.strptime(f"{self.target_date} {self.start_time}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{self.target_date} {self.end_time}", "%Y-%m-%d %H:%M")

        while current_dt <= end_dt:
            ts_str = current_dt.strftime("%H:%M")
            ts_ms = int(current_dt.timestamp() * 1000)
            
            updates = self._load_candles(ts_str)
            for update in updates:
                # Java expects 'data' to be a single object, not a list
                # And expects 'candle' key not '1m'
                payload = {
                    "symbol": update["symbol"],
                    "timestamp": update["timestamp"], # This is technically redundant inside data, but harmless
                    "candle": update["1m"], # Rename 1m -> candle
                    "pcr": update["pcr"]
                }
                
                await self.broadcast(payload, ts_ms)
                print(f"[Replay] {ts_str} | Sent candle for {update['symbol']}")
            
            current_dt += timedelta(minutes=1)
            if self.speed < 999:
                await asyncio.sleep(60 / self.speed)

        print("[Replay] Finished.")

    async def handle_client(self, websocket, path=None):
        self.clients.add(websocket)
        print("[Server] Client connected")
        try:
            async for msg in websocket: pass
        except: pass
        finally:
            self.clients.discard(websocket)

    async def start(self):
        async with websockets.serve(self.handle_client, "localhost", self.port):
            print(f"[Server] Running on ws://localhost:{self.port}")
            while not self.clients:
                await asyncio.sleep(0.5)
            print("[Server] Client detected, starting replay in 1s...")
            await asyncio.sleep(1)
            await self.replay_loop()
            await asyncio.Future() # Keep alive

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default='2026-01-05')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--speed', type=int, default=50)
    parser.add_argument('--start', default='09:15')
    parser.add_argument('--end', default='09:45')
    args = parser.parse_args()
    
    engine = MinimalReplayEngine(args.date, args.port, args.speed, args.start, args.end)
    asyncio.run(engine.start())
