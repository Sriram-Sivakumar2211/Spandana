import numpy as np
import pandas as pd
from features.vibration_features import extract_vibration_features
from features.thermal_features import extract_thermal_features

class SensorFeatureExtractor:
    """
    Unified feature extraction manager for industrial machine signals and thermal images.
    """
    @staticmethod
    def extract_from_time_series_window(df_window: pd.DataFrame, source: str = "metropt3") -> dict:
        """
        Extracts aggregated time-series features from a sliding window DataFrame.
        """
        features = {}

        if source == "metropt3":
            # Extract Motor Current features
            if "Motor_current" in df_window.columns:
                current_signal = df_window["Motor_current"].values
                vib_f = extract_vibration_features(current_signal, fs=1.0)
                features["rms"] = vib_f["rms"]
                features["kurtosis"] = vib_f["kurtosis"]
                features["skewness"] = vib_f["skewness"]
                features["crest_factor"] = vib_f["crest_factor"]
                features["dominant_frequency"] = vib_f["dominant_frequency"]
                features["current"] = round(float(np.mean(current_signal)), 4)
            else:
                features["rms"] = 0.0
                features["kurtosis"] = 0.0
                features["skewness"] = 0.0
                features["crest_factor"] = 0.0
                features["dominant_frequency"] = 0.0
                features["current"] = 0.0

            # Extract Oil Temperature
            if "Oil_temperature" in df_window.columns:
                features["temperature"] = round(float(np.mean(df_window["Oil_temperature"])), 2)
            else:
                features["temperature"] = 0.0

            # Extract RPM / default motor speed
            features["rpm"] = 1480.0

            # Extract key pressure signals
            if "TP2" in df_window.columns:
                features["tp2_pressure"] = round(float(np.mean(df_window["TP2"])), 4)
            if "TP3" in df_window.columns:
                features["tp3_pressure"] = round(float(np.mean(df_window["TP3"])), 4)

        return features

    @staticmethod
    def extract_from_thermal_frame(frame: np.ndarray, source: str = "thermal_motor") -> dict:
        """
        Extracts thermal distribution features from a 2D thermal image frame.
        """
        tf = extract_thermal_features(frame)
        
        features = {
            "rms": tf["temperature_std"],
            "kurtosis": 3.0,
            "skewness": 0.0,
            "crest_factor": round(tf["temperature_max"] / (tf["temperature_mean"] + 1e-6), 4),
            "dominant_frequency": 0.0,
            "temperature": tf["temperature_mean"],
            "current": 4.0 if "squirrel" in source else 2.0,
            "rpm": 1480.0,
            "hotspot_ratio": tf["hotspot_ratio"],
            "hotspot_intensity": tf["hotspot_intensity"]
        }
        return features

if __name__ == "__main__":
    df_dummy = pd.DataFrame({
        "Motor_current": np.random.randn(60) * 0.5 + 4.2,
        "Oil_temperature": np.random.randn(60) * 1.0 + 65.0,
        "TP2": np.random.randn(60) * 0.1 + 8.5
    })
    feats = SensorFeatureExtractor.extract_from_time_series_window(df_dummy, source="metropt3")
    print("MetroPT3 window features:", feats)
