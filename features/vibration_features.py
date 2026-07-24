import numpy as np
from scipy import stats

try:
    import pywt
    _HAS_PYWT = True
except ImportError:
    _HAS_PYWT = False


def spectral_entropy(fft_magnitudes: np.ndarray) -> float:
    """
    Shannon entropy of the normalized power spectrum. Low entropy indicates
    energy concentrated at few frequencies (e.g. a strong fault harmonic);
    high entropy indicates broadband/noise-like vibration.
    """
    power = fft_magnitudes ** 2
    total = np.sum(power)
    if total <= 1e-12:
        return 0.0
    prob = power / total
    prob = prob[prob > 1e-12]
    ent = -np.sum(prob * np.log2(prob))
    max_ent = np.log2(len(power)) if len(power) > 1 else 1.0
    return float(ent / max_ent) if max_ent > 0 else 0.0


def wavelet_band_energy(signal: np.ndarray, wavelet: str = "db4", level: int = 4) -> dict:
    """
    Discrete wavelet transform decomposition. Returns normalized energy per
    detail level (d1..dN, high-to-low frequency) plus the final approximation
    band (aN), useful for localizing bearing fault transients across scales.
    """
    keys = [f"wavelet_energy_a{level}"] + [f"wavelet_energy_d{i}" for i in range(1, level + 1)]
    if not _HAS_PYWT or len(signal) < 2 ** level:
        return {k: 0.0 for k in keys}

    coeffs = pywt.wavedec(signal, wavelet=wavelet, level=level)
    # coeffs = [cA_n, cD_n, cD_n-1, ..., cD_1]
    energies = [float(np.sum(c ** 2)) for c in coeffs]
    total = sum(energies) + 1e-12

    out = {f"wavelet_energy_a{level}": round(energies[0] / total, 6)}
    # coeffs[1:] are ordered cD_n ... cD_1; expose them as d1..dN (low index = finest/highest freq detail)
    detail_energies = list(reversed(energies[1:]))
    for i, e in enumerate(detail_energies, start=1):
        out[f"wavelet_energy_d{i}"] = round(e / total, 6)
    return out


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
            "spectral_energy": 0.0, "band_energy": 0.0, "spectral_entropy": 0.0
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
        spec_entropy = spectral_entropy(fft_vals)

        band_mask = (fft_freqs >= 10.0) & (fft_freqs <= 300.0)
        band_energy = float(np.sum(fft_vals[band_mask] ** 2) / n) if np.any(band_mask) else 0.0
    else:
        dom_freq = 0.0
        spectral_energy = 0.0
        band_energy = 0.0
        spec_entropy = 0.0

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
        "band_energy": round(band_energy, 4),
        "spectral_entropy": round(spec_entropy, 6)
    }