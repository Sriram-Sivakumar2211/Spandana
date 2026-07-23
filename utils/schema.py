import json
import os
from typing import Optional

import jsonschema

_SCHEMA_DIR = os.path.join("backend", "schema")
_SCHEMAS_DIR = os.path.join("backend", "schemas")

with open(os.path.join(_SCHEMAS_DIR, "sensor_input.json"), "r", encoding="utf-8") as f:
    SENSOR_INPUT_SCHEMA = json.load(f)

with open(os.path.join(_SCHEMA_DIR, "model_prediction.json"), "r", encoding="utf-8") as f:
    MODEL_PREDICTION_SCHEMA = json.load(f)

# The canonical, ordered feature-key space every standardized record's
# "features" object is filled against. This is the union of:
#   - the 12 keys named explicitly in backend/schemas/sensor_input.json
#     (rms, kurtosis, ..., hotspot_ratio, hotspot_intensity)
#   - the extra time/freq/wavelet keys features/bearing_features.py computes
#     for the 3 vibration datasets (mean, variance, peak, ..., wavelet_energy_*)
# sensor_input.json declares "additionalProperties": true on `features`, so
# carrying the extra bearing-specific keys alongside the 12 named ones is
# schema-valid, not a schema violation -- see Phase 3's feature engineering,
# which is deliberately richer than the minimum contract.
CANONICAL_FEATURE_KEYS = [
    # From backend/schemas/sensor_input.json
    "rms", "kurtosis", "skewness", "crest_factor", "dominant_frequency",
    "temperature", "current", "rpm", "tp2_pressure", "tp3_pressure",
    "hotspot_ratio", "hotspot_intensity",
    # Extra time/freq/wavelet keys from features/bearing_features.py
    "mean", "std", "variance", "peak", "peak_to_peak", "spectral_energy", "spectral_entropy",
    "wavelet_energy_a4", "wavelet_energy_d1", "wavelet_energy_d2", "wavelet_energy_d3", "wavelet_energy_d4",
]

SOURCE_ENUM = SENSOR_INPUT_SCHEMA["properties"]["source"]["enum"]
GROUND_TRUTH_ENUM = SENSOR_INPUT_SCHEMA["properties"]["ground_truth"]["enum"]
OPERATING_MODE_ENUM = SENSOR_INPUT_SCHEMA["properties"]["operating_mode"]["enum"]

# Sources that carry a specific bearing fault-location label internally
# (features.bearing_common.BEARING_CLASSES) instead of a coarse 3-tier
# healthy/warning/faulty label. Any fault location maps to "faulty" here --
# the specific location is preserved separately as the model's training
# target (see preprocessing/build_unified_bearing_dataset.py), not lost.
_BEARING_SOURCES = {"nasa_ims", "cwru", "paderborn"}


def fill_feature_vector(features: dict) -> dict:
    """Returns a dict with every CANONICAL_FEATURE_KEYS key present, filling
    0.0 for keys this record's source doesn't provide. 0.0 means "not
    applicable/available for this sensor modality", not "measured as zero"."""
    return {k: float(features.get(k, 0.0)) for k in CANONICAL_FEATURE_KEYS}


GROUND_TRUTH_TO_INDEX = {c: i for i, c in enumerate(GROUND_TRUTH_ENUM)}
INDEX_TO_GROUND_TRUTH = {i: c for i, c in enumerate(GROUND_TRUTH_ENUM)}


def encode_ground_truth(label: str) -> int:
    return GROUND_TRUTH_TO_INDEX[label]


def decode_ground_truth(index: int) -> str:
    return INDEX_TO_GROUND_TRUTH[int(index)]


def bearing_class_to_ground_truth(bearing_class: str, warning: bool = False) -> str:
    """Coarsens a specific bearing fault-location label down to the shared
    3-tier ground_truth field. `warning` lets callers (e.g. the NASA IMS
    RMS-trend heuristic, which has a genuine early-degradation zone) flag a
    fault that is emerging but not yet past the onset threshold."""
    if bearing_class == "healthy":
        return "warning" if warning else "healthy"
    return "faulty"


def validate_input_record(record: dict) -> Optional[str]:
    """Returns None if valid, else a human-readable error string. Does not raise,
    so a validation script can collect every offending record instead of stopping
    at the first one."""
    try:
        jsonschema.validate(instance=record, schema=SENSOR_INPUT_SCHEMA)
        return None
    except jsonschema.exceptions.ValidationError as e:
        return str(e.message)


def validate_prediction_record(record: dict) -> Optional[str]:
    try:
        jsonschema.validate(instance=record, schema=MODEL_PREDICTION_SCHEMA)
        return None
    except jsonschema.exceptions.ValidationError as e:
        return str(e.message)
