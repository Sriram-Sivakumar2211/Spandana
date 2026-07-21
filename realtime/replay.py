import os
import sys
import time
import json
import argparse
import datetime
from realtime.stream import StreamClient

def run_replay(source: str = "metropt3", delay: float = 0.5, limit: int = 50, post_api: bool = False, endpoint_url: str = None):
    """
    Simulates real-time streaming by reading processed sliding window records sequentially,
    emitting them to stdout with configurable delays, and optionally posting to backend API.
    """
    stream_file = os.path.join("data", "stream_ready", f"{source}_stream.jsonl")
    
    if not os.path.exists(stream_file):
        print(f"Stream file {stream_file} not found. Searching in data/windows/...")
        stream_file = os.path.join("data", "windows", f"{source}_windows.jsonl")
    
    if not os.path.exists(stream_file):
        print(f"Error: Could not locate stream input file for source '{source}'. Run export step first.")
        return

    client = StreamClient(endpoint_url=endpoint_url) if post_api else None
    
    print(f"=== Starting Real-Time Stream Replay for Source: {source.upper()} ===")
    print(f"  Delay: {delay}s | Limit: {limit if limit else 'Unlimited'} | Post to API: {post_api}\n")

    count = 0
    with open(stream_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            
            record = json.loads(line.strip())
            
            # Update timestamp to current live simulation time
            now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
            record["timestamp"] = now_utc

            # Emit record to stdout
            print(f"[{record['timestamp']}] EMIT {record['window_id']} ({record['source'].upper()}) -> Label: {record['label'].upper()} | Features: RMS={record['features'].get('rms', 0):.2f}, Temp={record['features'].get('temperature', 0):.1f}°C, Current={record['features'].get('current', 0):.1f}A")

            if post_api and client:
                posted = client.post_window(record)
                if posted:
                    print("   └── Sent to Backend API Successfully")
                else:
                    print("   └── Backend API Offline (skipping HTTP delivery)")

            count += 1
            if limit and count >= limit:
                print(f"\nReached replay limit of {limit} windows.")
                break

            time.sleep(delay)

    print(f"Replay completed. Total emitted windows: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spandana Real-Time Sensor Replay Simulator")
    parser.add_argument("--source", type=str, default="metropt3", choices=["metropt3", "thermal_motor", "squirrel_cage"], help="Data source")
    parser.add_argument("--delay", type=float, default=0.2, help="Emitting delay in seconds")
    parser.add_argument("--limit", type=int, default=20, help="Max windows to replay")
    parser.add_argument("--post", action="store_true", help="Post windows to backend API")
    args = parser.parse_args()

    run_replay(source=args.source, delay=args.delay, limit=args.limit, post_api=args.post)
