import numpy as np
from scipy import stats

def extract_vibration_features(signal: np.ndarray, fs: float = 1000.0) -> dict:
    """
    Extracts time-domain and frequency-domain (FFT) features from a 1D vibration/signal array.
    """
    signal = np.asarray(signal, dtype=np.float64)
    if len(signal) == 0:
        return {
            "mean": 0.0, "std": 0.0, "rms": 0.0, "variance": 0.0,
            "peak": 0.0, "peak_to_peak": 0.0, "skewness": 0.0,
            "kurtosis": 0.0, "crest_factor": 0.0, "dominant_frequency": 0.0,
            "spectral_energy": 0.0, "band_energy": 0.0
        }

    # Time-domain features
    mean_val = float(np.mean(signal))
    std_val = float(np.std(signal))
    variance_val = float(np.var(signal))
    rms_val = float(np.sqrt(np.mean(signal ** 2)))
    peak_val = float(np.max(np.abs(signal)))
    peak_to_peak_val = float(np.ptp(signal))

    # Avoid precision warnings on constant signals
    if std_val < 1e-8:
        skewness_val = 0.0
        kurtosis_val = 0.0
    else:
        skewness_val = float(stats.skew(signal)) if len(signal) > 2 else 0.0
        kurtosis_val = float(stats.kurtosis(signal)) if len(signal) > 3 else 0.0

    crest_factor_val = float(peak_val / rms_val) if rms_val > 1e-8 else 0.0

    # Frequency-domain (FFT) features
    n = len(signal)
    fft_vals = np.abs(np.fft.rfft(signal))
    fft_freqs = np.fft.rfftfreq(n, d=1.0/fs)

    if len(fft_vals) > 1:
        dom_idx = np.argmax(fft_vals[1:]) + 1
        dom_freq = float(fft_freqs[dom_idx])
        spectral_energy = float(np.sum(fft_vals ** 2) / n)
        
        band_mask = (fft_freqs >= 10.0) & (fft_freqs <= 300.0)
        band_energy = float(np.sum(fft_vals[band_mask] ** 2) / n) if np.any(band_mask) else 0.0
    else:
        dom_freq = 0.0
        spectral_energy = 0.0
        band_energy = 0.0

    return {
        "mean": round(mean_val, 4),
        "std": round(std_val, 4),
        "rms": round(rms_val, 4),
        "variance": round(variance_val, 4),
        "peak": round(peak_val, 4),
        "peak_to_peak": round(peak_to_peak_val, 4),
        "skewness": round(skewness_val, 4),
        "kurtosis": round(kurtosis_val, 4),
        "crest_factor": round(crest_factor_val, 4),
        "dominant_frequency": round(dom_freq, 2),
        "spectral_energy": round(spectral_energy, 4),
        "band_energy": round(band_energy, 4)
    }
