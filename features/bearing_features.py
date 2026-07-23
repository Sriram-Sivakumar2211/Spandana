import numpy as np
from collections import OrderedDict

from features.vibration_features import extract_vibration_features, wavelet_band_energy

# Fixed, ordered feature schema shared by NASA IMS, CWRU and Paderborn.
# Every dataset's preprocessor must call `extract_bearing_feature_vector` on a
# single primary vibration channel per window so the resulting feature vector
# has an identical length/ordering regardless of how many raw channels the
# source dataset happens to record (NASA IMS: up to 8, Paderborn: 1, CWRU: up
# to 3). This is what makes Phase 4 (unified dataset) possible.
TIME_DOMAIN_KEYS = [
    "mean", "std", "rms", "variance", "peak", "peak_to_peak",
    "crest_factor", "skewness", "kurtosis"
]
FREQ_DOMAIN_KEYS = ["dominant_frequency", "spectral_energy", "spectral_entropy"]
WAVELET_LEVEL = 4
WAVELET_KEYS = [f"wavelet_energy_a{WAVELET_LEVEL}"] + [f"wavelet_energy_d{i}" for i in range(1, WAVELET_LEVEL + 1)]

BEARING_FEATURE_KEYS = TIME_DOMAIN_KEYS + FREQ_DOMAIN_KEYS + WAVELET_KEYS


def extract_bearing_feature_vector(signal: np.ndarray, fs: float, wavelet: str = "db4") -> OrderedDict:
    """
    Builds the unified time + frequency + wavelet feature vector for one
    vibration-signal window. Returns an OrderedDict following
    BEARING_FEATURE_KEYS so downstream numpy export order is deterministic.
    """
    signal = np.asarray(signal, dtype=np.float64)
    vib = extract_vibration_features(signal, fs=fs)
    wav = wavelet_band_energy(signal, wavelet=wavelet, level=WAVELET_LEVEL)

    out = OrderedDict()
    for k in TIME_DOMAIN_KEYS + FREQ_DOMAIN_KEYS:
        out[k] = vib.get(k, 0.0)
    for k in WAVELET_KEYS:
        out[k] = wav.get(k, 0.0)
    return out


def feature_vector_to_array(feat_dict: dict) -> np.ndarray:
    """Converts a feature dict into a fixed-order float32 numpy array."""
    return np.array([feat_dict[k] for k in BEARING_FEATURE_KEYS], dtype=np.float32)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    demo_signal = rng.normal(0, 1.0, 4096)
    feats = extract_bearing_feature_vector(demo_signal, fs=48000.0)
    print(f"Feature dimension: {len(feats)}")
    for k, v in feats.items():
        print(f"  {k}: {v}")
