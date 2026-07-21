import os
import glob
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

class ThermalMotorPreprocessor:
    """
    Preprocessor for the Thermal Image Dataset for Induction Motors.
    Loads infrared thermal images, resizes, normalizes, and categorizes motor status.
    """
    def __init__(self, raw_dir: str = None):
        if raw_dir is None:
            raw_dir = os.path.join("data", "raw", "thermal_motor")
        self.raw_dir = raw_dir

    def map_label(self, subfolder_name: str) -> str:
        """
        Maps thermal experiment subfolder names to health categories.
        """
        sub = subfolder_name.lower()
        if "misalignment-2" in sub or "misalignment-3" in sub or ("misalignment" in sub and ("load-4a" in sub or "load-6a" in sub)):
            return "faulty"
        elif "misalignment" in sub or "start-up" in sub:
            return "warning"
        elif "current-load" in sub:
            return "healthy"
        return "healthy"

    def _process_single_image(self, p, target_size):
        rel = os.path.relpath(p, self.raw_dir)
        parts = rel.split(os.sep)
        experiment = parts[0] if len(parts) > 1 else "default"
        label = self.map_label(experiment)

        try:
            with Image.open(p) as img:
                img_resized = img.resize(target_size, Image.Resampling.BILINEAR)
                arr = np.array(img_resized, dtype=np.float32)

                min_val, max_val = arr.min(), arr.max()
                if max_val > min_val:
                    arr_norm = (arr - min_val) / (max_val - min_val)
                else:
                    arr_norm = np.zeros_like(arr)

                meta = {
                    "file_path": p,
                    "source": "thermal_motor",
                    "experiment": experiment,
                    "label": label,
                    "raw_min": float(min_val),
                    "raw_max": float(max_val)
                }
                return arr_norm, meta
        except Exception as e:
            return None, None

    def load_samples(self, target_size=(128, 128), max_samples=None):
        """
        Loads raw thermal images in parallel from disk.
        """
        if not os.path.exists(self.raw_dir):
            raise FileNotFoundError(f"Thermal motor raw directory not found: {self.raw_dir}")

        image_paths = glob.glob(os.path.join(self.raw_dir, "**", "*.png"), recursive=True)
        if max_samples:
            image_paths = image_paths[:max_samples]

        images_list = []
        metadata_list = []

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(self._process_single_image, p, target_size) for p in image_paths]
            for f in futures:
                arr_norm, meta = f.result()
                if arr_norm is not None:
                    images_list.append(arr_norm)
                    metadata_list.append(meta)

        images_np = np.array(images_list, dtype=np.float32) if images_list else np.empty((0, *target_size))
        return images_np, metadata_list

if __name__ == "__main__":
    prep = ThermalMotorPreprocessor()
    imgs, meta = prep.load_samples(max_samples=100)
    print(f"Loaded {len(imgs)} thermal motor samples with shape {imgs.shape}")
