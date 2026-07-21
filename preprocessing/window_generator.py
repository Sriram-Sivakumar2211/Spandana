import os
import datetime
import pandas as pd
import numpy as np
from features.sensor_features import SensorFeatureExtractor

class SlidingWindowGenerator:
    """
    Sliding Window Generator for industrial time-series and image streams.
    Generates model-ready windows adhering strictly to the unified JSON schema.
    """
    def __init__(self, machine_id: str = "MOTOR_001"):
        self.machine_id = machine_id

    def generate_df_windows(self, df: pd.DataFrame, source: str = "metropt3", window_size: int = 60, step: int = 10):
        """
        Generates overlapping windows from a time-series DataFrame (e.g., MetroPT-3).
        """
        windows = []
        n_rows = len(df)
        window_counter = 1

        for start in range(0, n_rows - window_size + 1, step):
            end = start + window_size
            window_df = df.iloc[start:end]

            # Determine timestamp (use last timestamp of the window)
            if "timestamp" in window_df.columns:
                ts_val = window_df["timestamp"].iloc[-1]
                if isinstance(ts_val, pd.Timestamp):
                    timestamp_str = ts_val.isoformat() + "Z"
                else:
                    timestamp_str = str(ts_val)
            else:
                timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Extract features
            features = SensorFeatureExtractor.extract_from_time_series_window(window_df, source=source)

            # Consensus label (mode label or worst-case label)
            labels = window_df["label"].tolist() if "label" in window_df.columns else ["healthy"]
            if "faulty" in labels:
                consensus_label = "faulty"
            elif "warning" in labels:
                consensus_label = "warning"
            else:
                consensus_label = "healthy"

            window_obj = {
                "machine_id": self.machine_id,
                "timestamp": timestamp_str,
                "source": source,
                "window_id": f"window_{window_counter:04d}",
                "features": features,
                "label": consensus_label
            }

            windows.append(window_obj)
            window_counter += 1

        return windows

    def generate_image_windows(self, images_np: np.ndarray, metadata: list, source: str = "thermal_motor", window_size: int = 10, step: int = 5):
        """
        Generates sliding window aggregations from thermal image frame sequences.
        """
        windows = []
        n_frames = len(images_np)
        window_counter = 1
        base_time = datetime.datetime(2026, 7, 21, 10, 0, 0, tzinfo=datetime.timezone.utc)

        for start in range(0, n_frames - window_size + 1, step):
            end = start + window_size
            window_frames = images_np[start:end]
            window_meta = metadata[start:end]

            # Mean thermal frame in window
            mean_frame = np.mean(window_frames, axis=0)
            features = SensorFeatureExtractor.extract_from_thermal_frame(mean_frame, source=source)

            labels = [m["label"] for m in window_meta]
            if "faulty" in labels:
                consensus_label = "faulty"
            elif "warning" in labels:
                consensus_label = "warning"
            else:
                consensus_label = "healthy"

            timestamp_str = (base_time + datetime.timedelta(seconds=start)).isoformat()

            window_obj = {
                "machine_id": self.machine_id,
                "timestamp": timestamp_str,
                "source": source,
                "window_id": f"window_{window_counter:04d}",
                "features": features,
                "label": consensus_label
            }

            windows.append(window_obj)
            window_counter += 1

        return windows

if __name__ == "__main__":
    df_sample = pd.DataFrame({
        "timestamp": pd.date_range("2026-07-21 10:00:00", periods=200, freq="1s"),
        "Motor_current": np.random.randn(200) * 0.2 + 4.0,
        "Oil_temperature": np.random.randn(200) * 0.5 + 60.0,
        "TP2": np.random.randn(200) * 0.1 + 8.0,
        "label": ["healthy"] * 150 + ["warning"] * 50
    })

    gen = SlidingWindowGenerator(machine_id="MOTOR_001")
    wins = gen.generate_df_windows(df_sample, source="metropt3", window_size=60, step=10)
    print(f"Generated {len(wins)} windows.")
    if wins:
        print("Sample window object:")
        import json
        print(json.dumps(wins[0], indent=2))
