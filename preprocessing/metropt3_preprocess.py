import os
import pandas as pd
import numpy as np

class MetroPT3Preprocessor:
    """
    Preprocessor for the MetroPT-3 Air Compressor Multivariate Time-Series Dataset.
    """
    def __init__(self, raw_path: str = None):
        if raw_path is None:
            raw_path = os.path.join("data", "raw", "metropt3", "MetroPT3(AirCompressor).csv")
        self.raw_path = raw_path

    def assign_label(self, row) -> str:
        """
        Derives operational health status based on physical pressure, temperature, and current thresholds.
        """
        # Low pressure alert or excessive oil temp -> faulty
        if row.get("LPS", 0) > 0 or row.get("Oil_temperature", 0) > 85.0 or row.get("TP2", 0) < 2.0:
            return "faulty"
        # High oil temp or high motor current under low pressure -> warning
        elif row.get("Oil_temperature", 0) > 70.0 or row.get("Motor_current", 0) > 9.5:
            return "warning"
        return "healthy"

    def load_and_clean(self, nrows: int = None) -> pd.DataFrame:
        """
        Loads raw MetroPT-3 CSV, parses timestamps, sorts chronologically, removes duplicates,
        normalizes sensor channels, and assigns health labels.
        """
        if not os.path.exists(self.raw_path):
            raise FileNotFoundError(f"MetroPT-3 raw CSV not found at {self.raw_path}")

        print(f"Loading MetroPT-3 dataset from {self.raw_path}...")
        df = pd.read_csv(self.raw_path, nrows=nrows)

        # Drop unwanted index column if present
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])

        # Parse timestamps and sort chronologically
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Remove duplicate timestamps
        df = df.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

        # Handle missing values via forward/backward fill
        df = df.ffill().bfill()

        # Define sensor channels
        self.sensor_cols = [
            "TP2", "TP3", "H1", "DV_pressure", "Reservoirs",
            "Oil_temperature", "Motor_current", "COMP", "DV_eletric",
            "Towers", "MPG", "LPS", "Pressure_switch", "Oil_level", "Caudal_impulses"
        ]

        # Filter to available sensor columns
        valid_cols = [c for c in self.sensor_cols if c in df.columns]
        
        # Continuous numeric columns for Z-score / Min-Max normalization
        cont_cols = ["TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current", "Caudal_impulses"]
        cont_cols = [c for c in cont_cols if c in df.columns]

        for col in cont_cols:
            mean = df[col].mean()
            std = df[col].std()
            if std > 0:
                df[f"{col}_norm"] = (df[col] - mean) / std
            else:
                df[f"{col}_norm"] = 0.0

        # Assign health labels
        df["label"] = df.apply(self.assign_label, axis=1)

        print(f"MetroPT-3 loaded successfully: {len(df)} rows across {len(valid_cols)} sensor channels.")
        return df

if __name__ == "__main__":
    prep = MetroPT3Preprocessor()
    df_clean = prep.load_and_clean(nrows=5000)
    print("Cleaned head:")
    print(df_clean[["timestamp", "TP2", "Oil_temperature", "Motor_current", "label"]].head())
    print("\nLabel distribution:")
    print(df_clean["label"].value_counts())
