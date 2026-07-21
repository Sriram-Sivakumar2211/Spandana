import numpy as np

def extract_thermal_features(image: np.ndarray, hotspot_percentile: float = 85.0) -> dict:
    """
    Extracts summary thermal distribution metrics from a 2D numpy array representing a thermal frame.
    
    Parameters:
        image: 2D numpy array (height, width) of pixel intensities or temperatures.
        hotspot_percentile: Percentile threshold to define thermal hotspots.
        
    Returns:
        Dictionary of extracted thermal features.
    """
    img_arr = np.asarray(image, dtype=np.float64)
    if img_arr.size == 0:
        return {
            "temperature_mean": 0.0,
            "temperature_max": 0.0,
            "hotspot_ratio": 0.0,
            "hotspot_intensity": 0.0,
            "temperature_std": 0.0
        }

    mean_val = float(np.mean(img_arr))
    max_val = float(np.max(img_arr))
    std_val = float(np.std(img_arr))

    # Calculate hotspot threshold
    thresh = float(np.percentile(img_arr, hotspot_percentile))
    hotspot_pixels = img_arr[img_arr >= thresh]

    hotspot_ratio = float(len(hotspot_pixels) / img_arr.size) if img_arr.size > 0 else 0.0
    hotspot_intensity = float(np.mean(hotspot_pixels)) if len(hotspot_pixels) > 0 else max_val

    return {
        "temperature_mean": round(mean_val, 4),
        "temperature_max": round(max_val, 4),
        "hotspot_ratio": round(hotspot_ratio, 4),
        "hotspot_intensity": round(hotspot_intensity, 4),
        "temperature_std": round(std_val, 4)
    }

if __name__ == "__main__":
    dummy_img = np.random.rand(128, 128)
    dummy_img[40:60, 40:60] += 2.0  # Simulated hotspot
    feats = extract_thermal_features(dummy_img)
    print("Extracted sample thermal features:")
    for k, v in feats.items():
        print(f"  {k}: {v}")
