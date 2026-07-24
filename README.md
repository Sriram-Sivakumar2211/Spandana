# Spandana — Affordable Real-Time Predictive Maintenance for MSMEs

This repository unifies two datasets tracks -- Member 1's electro-mechanical sensors (**MetroPT-3** air compressor, **squirrel-cage motor**, **thermal-imaging motor**) and Member 2's bearing-vibration rigs (**NASA IMS**, **CWRU**, **Paderborn**) -- into one shared input/output schema, and serves both a bearing-specific specialist model and a general cross-dataset severity model from that shared foundation.

Spandana's model is **LTC-only**. There is no LSTM anywhere in this codebase or its history going forward -- the model is the official MIT implementation via [`ncps`](https://github.com/mlech26l/ncps) (`ncps.torch.LTC`, wired with `AutoNCP`), not a custom from-scratch ODE layer.

## Getting Started (Backend + Frontend)

This section is the fastest path to a running app -- backend API + React dashboard. The trained model checkpoints are already included, so you do not need to run any training scripts to see the app work.

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (20+ recommended) and npm
- **Git**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Sriram-Sivakumar2211/Spandana.git
cd Spandana

# 2. Install backend (Python) dependencies
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend
npm install
cd ..
```

> **Windows note**: if you're inside a deeply-nested or cloud-synced folder (OneDrive, Dropbox), create the virtualenv somewhere shorter instead (e.g. `C:\dev\spandana-venv`) -- see the path-length caveat under [ML Pipeline Setup](#ml-pipeline-setup) below.

### Environment Variables

The backend's RAG report generator can optionally call the real Gemini LLM API. **This is optional** -- without it, the backend automatically falls back to a deterministic, still-grounded rule-based report generator, and the app works identically either way except the report text is templated instead of LLM-written.

1. Copy the example file:
   ```bash
   # macOS/Linux/Git Bash:
   cp .env.example .env
   # Windows (Command Prompt):
   copy .env.example .env
   ```
2. Get a **free** Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) (sign in with any Google account, click "Create API key").
3. Open `.env` and paste your key:
   ```
   GEMINI_API_KEY=YOUR_API_KEY
   ```
4. Save the file. **Do not commit it** -- `.env` is gitignored; only `.env.example` (with a placeholder, no real key) is tracked in git.

The backend reads this automatically via [`python-dotenv`](https://pypi.org/project/python-dotenv/) at startup (`backend/app.py`) -- no extra flags or steps needed. If `GEMINI_API_KEY` isn't set at all, the backend still starts and runs normally; check `GET /health` to see which report engine is currently active (`"Google Gemini API"` vs `"Grounded Rule Engine (Offline Fallback)"`).

### Running the Project

**Backend** (from the repo root, with your virtualenv activated):

```bash
uvicorn backend.app:app --reload
```

**Frontend** (in a second terminal):

```bash
cd frontend
npm run dev
```

**Expected URLs**:

| Service | URL |
|---|---|
| Frontend (React dashboard) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Backend health check | http://localhost:8000/health |
| Backend interactive API docs | http://localhost:8000/docs |

The frontend's dev server proxies API calls to the backend automatically (`frontend/vite.config.ts`) -- open http://localhost:5173 and the dashboard should load and start showing live data.

### Security

- API keys are **intentionally excluded from this repository** -- `.env` is gitignored, and the full git history was checked to confirm no key has ever been committed.
- Every user/judge should create and use **their own** Gemini API key (free from Google AI Studio) rather than sharing one.
- Store keys **only** in your local `.env` file or your OS's environment variables -- never in source code, never in a commit, never in a screenshot you share.
- If you ever paste a key somewhere it shouldn't be, the safe fix is to regenerate/revoke it in Google AI Studio and swap in a new one -- keys are free and instant to reissue.

## Two models, one schema

| | Bearing specialist | General severity model |
|---|---|---|
| Task | 5-class fault **location**: healthy / inner_race / outer_race / ball / combined | 3-class fault **severity**: healthy / warning / faulty |
| Sources | NASA IMS, CWRU, Paderborn only | All 6 datasets |
| Features | 17-dim bearing-specific (`features/bearing_features.py`) | 24-dim canonical (`utils/schema.py::CANONICAL_FEATURE_KEYS`) |
| Code | `lnn/model.py`, `lnn/train.py`, `configs/lnn_config.json` | same `SpandanaLTC` class, `lnn/train_general.py`, `configs/ltc_general_config.json` |
| Checkpoint | `data/checkpoints/lnn/best_ltc.pt` | `data/checkpoints/ltc_general_augmented/best_ltc_general.pt` |

Both are the same `lnn/model.py::SpandanaLTC` architecture (ncps `LTC` + `AutoNCP`) trained on different feature spaces and label spaces -- there is no separate LSTM benchmark and no custom ODE implementation anywhere.

## Pipeline

```
Raw datasets (6 sources, 2 tracks)
        -> Existing per-source preprocessing (unchanged)     [preprocessing/*_preprocess.py]
        -> Schema adapter: standardize to shared schema       [preprocessing/schema_adapter.py]
        -> Fail-fast validation across all 6 sources          [preprocessing/validate_all_datasets.py]
        -> Bearing-only unified dataset (specialist model)    [preprocessing/build_unified_bearing_dataset.py]
        -> 6-dataset unified dataset (general model)          [preprocessing/build_six_dataset_unified.py]
        -> VAE: healthy-anomaly scorer + minority augmentation [augmentation/]
        -> LTC (ncps, both models)                             [lnn/]
        -> Evaluation + cross-dataset + cross-modality         [evaluation/]
        -> Stateful inference -> prediction JSON               [inference/]
```

The schema adapter reads each track's **existing, already-preprocessed** window JSONL/`.npy` outputs and re-expresses them in the shared schema -- it does not re-preprocess raw signals, per the requirement to reuse existing pipelines rather than rebuild them.

## Shared schema

- **Input schema**: `backend/schemas/sensor_input.json` (JSON Schema draft-07; pre-existing, unmodified -- confirmed to already match the target contract, including `additionalProperties: true` on `features`, which is why bearing-specific feature keys coexist validly alongside the canonical 12).
- **Prediction schema**: `backend/schema/model_prediction.json` (was empty; now populated to mirror the input schema's style).
- **Canonical feature space**: `utils/schema.py::CANONICAL_FEATURE_KEYS` -- 24 dims covering both tracks' feature sets; a record from either track zero-fills whatever fields don't apply to it (`utils/schema.py::fill_feature_vector`).
- **Ground truth**: `utils/schema.py::GROUND_TRUTH_ENUM = ["healthy", "warning", "faulty"]`, the one label space all 6 datasets can genuinely express. The bearing-specific 5-class fault-location label is a separate, finer-grained task on top of this, not merged into it.
- Every standardized record is validated with real `jsonschema.validate` calls (`utils/schema.py::validate_input_record` / `validate_prediction_record`), not just visual inspection.

**Disclosed limitation**: "warning" has **zero real-world examples across all 6 datasets** -- every source labels its data strictly healthy or faulty (or a bearing fault type). No warning-tier mapping was fabricated to fill this gap; the class exists in the schema and the model's output layer, but nothing in the current data justifies claiming it works.

## Statefulness

`lnn/model.py::SpandanaLTC` wraps `ncps.torch.LTC` and exposes its hidden state (`hx`) and elapsed-time (`timespans`) inputs directly. `inference/predict.py::LTCInferenceEngine` keeps one `hx` per `machine_id` and feeds one window at a time -- the machine's operating history lives entirely in its persisted hidden state, not in a replayed lookback buffer. Real elapsed wall-clock time between a machine's readings is passed as `timespans`, so a late or early sensor reading changes the model's internal dynamics instead of being silently treated as on-time. Batched offline training uses `hx=None`/`timespans=None` (uniform dt, matching how sliding-window sequences were built); only streaming inference at batch size 1 uses real `hx`/`timespans`.

## VAE augmentation & anomaly scoring

`augmentation/vae.py::FeatureVAE` is a small VAE over flat 24-dim feature vectors, used two ways:

1. **Minority-class augmentation** (`augmentation/augment_training_data.py`): trains a VAE on real faulty training vectors and generates synthetic faulty samples to reduce the real ~3.2:1 healthy/faulty imbalance in the general model's training set. **Kept because it measurably helped**: macro-F1 improved 0.9877 -> 0.9932 (`reports/general_model_evaluation_baseline.json` vs `_augmented.json`), with fewer errors in both directions on the real, never-augmented test set. This is the honest outcome -- augmentation is not always assumed to help, and here it was checked, not just applied.
2. **Anomaly scoring** (`inference/predict.py::LTCInferenceEngine._vae_anomaly_score`): a separate VAE trained on healthy-only vectors (`data/checkpoints/vae/healthy_vae.pt`) provides `anomaly_score` via reconstruction error, independent of the supervised classifier. Disclosed limitation: because each source only populates its own slice of the 24-dim vector, this error is masked to the bearing-relevant dims (`dims_mask`) to avoid dilution, but still carries residual cross-source confounding -- treat it as a secondary signal alongside `fault_probability`, not a replacement for it.

## Validation

- `preprocessing/validate_all_datasets.py` -- fail-fast schema/label/NaN/timestamp-ordering/split-leakage checks across all 6 standardized sources. **All 6 currently pass** (`reports/preprocessing_validation_report.md`).
- `evaluation/cross_dataset_validation.py` -- bearing-only domain shift (nasa_ims/cwru/paderborn, 3 scenarios). **Honest result: near-chance accuracy (0.24-0.26)**, root-caused and disclosed in `reports/cross_dataset_report.md` as a direct consequence of no single bearing dataset containing all 5 fault classes (e.g. paderborn never contains "ball," which is 30% of cwru) -- not a training bug.
- `evaluation/cross_modality_validation.py` -- Member1<->bearing modality transfer (2 scenarios). **Honest result: total single-class collapse in both directions** (`reports/cross_modality_report.md`), consistent with the general model likely keying on "which sensor rig populated which feature slots" rather than a modality-independent health signal. Documented as a genuine, unresolved limitation of the current cross-modality approach, not smoothed over.

Neither cross-dataset nor cross-modality result was "fixed" by re-weighting, re-thresholding, or re-labeling to produce a better-looking number -- per this project's own anti-fabrication requirement, they are reported as measured.

## Folder Structure (ML-relevant subset)

```
configs/             dataset paths, Paderborn bearing-code table, preprocessing/LTC/general-model hyperparameters
preprocessing/        per-dataset preprocessors, schema_adapter.py (standardize both tracks), validate_all_datasets.py,
                      build_unified_bearing_dataset.py (bearing-only), build_six_dataset_unified.py (all 6),
                      build_member1_splits.py (chronological splits for Member 1 sources)
features/             vibration_features.py (time/freq/wavelet), bearing_features.py (fixed 17-dim schema)
augmentation/         vae.py (FeatureVAE), augment_training_data.py (minority-class synthesis)
lnn/                  model.py (SpandanaLTC, built on ncps.torch.LTC), train.py (bearing specialist), train_general.py (6-dataset)
evaluation/           metrics.py, evaluate_model.py, evaluate_general_model.py, cross_dataset_validation.py, cross_modality_validation.py
inference/            predict.py (LTCInferenceEngine, stateful, optional VAE anomaly scoring), inference_pipeline.py (batch/replay), decision_rules.py
utils/                common.py, checkpoint.py, torch_dataset.py, training_loop.py, schema.py (canonical schema + validation)
backend/schemas/       sensor_input.json (shared input contract, pre-existing)
backend/schema/        model_prediction.json (shared prediction contract)
data/bearing_processed, data/bearing_windows, data/bearing_splits, data/unified, data/unified_schema, data/checkpoints
reports/              EDA report, per-dataset notes, evaluation reports, cross-dataset report, cross-modality report, preprocessing validation report
```

## ML Pipeline Setup

The steps below are for re-running the ML training/evaluation pipeline itself (preprocessing, training, cross-dataset validation, etc.) -- not required just to run the app; see [Getting Started](#getting-started-backend--frontend) above for that.

Python 3.10+ recommended (PyTorch CPU wheels). **On Windows, create the virtualenv outside deeply-nested/OneDrive-synced paths** — PyTorch ships license files with very long relative paths that can exceed Windows' 260-char path limit if the venv itself is nested too deeply (this bit us during development; the fix was simply relocating the venv, e.g. to `C:\Users\<you>\spandana_ml_env`).

```powershell
py -3.10 -m venv C:\path\to\short\spandana_ml_env
C:\path\to\short\spandana_ml_env\Scripts\python.exe -m pip install -r requirements.txt
```

## How to Run

All commands below assume your working directory is the repo root and `$py` points at the venv's `python.exe`.

```powershell
# EDA report (reports/bearing_eda_report.md, bearing_eda_summary.json)
& $py preprocessing\eda_report.py

# Bearing-only preprocessing, features, unified split (specialist model's data)
& $py preprocessing\build_unified_bearing_dataset.py
& $py preprocessing\add_unified_groups.py

# Standardize BOTH tracks into the shared schema (reads existing preprocessed outputs, does not re-preprocess)
& $py preprocessing\build_member1_splits.py
& $py preprocessing\schema_adapter.py
& $py preprocessing\validate_all_datasets.py       # fail-fast; writes reports/preprocessing_validation_report.md
& $py preprocessing\build_six_dataset_unified.py   # 24-dim canonical feature table for the general model

# Bearing specialist model (5-class fault location)
& $py lnn\train.py
& $py evaluation\evaluate_model.py                  # reports/model_evaluation_report.md

# General 6-dataset severity model (3-class), + VAE augmentation
& $py augmentation\augment_training_data.py         # writes six_dataset_unified_augmented.npz + healthy_vae.pt
& $py lnn\train_general.py --data data\unified_schema\six_dataset_unified_augmented.npz --checkpoints-dir data\checkpoints\ltc_general_augmented
& $py evaluation\evaluate_general_model.py --checkpoint data\checkpoints\ltc_general_augmented\best_ltc_general.pt --label augmented

# Cross-dataset (bearing-only) and cross-modality (Member1 <-> bearing) validation
& $py evaluation\cross_dataset_validation.py        # reports/cross_dataset_report.md
& $py evaluation\cross_modality_validation.py       # reports/cross_modality_report.md

# Single-window inference (prints the prediction JSON; loads the bearing specialist + healthy-VAE anomaly scorer by default)
& $py inference\predict.py --signal path\to\signal.npy --fs 48000 --machine-id MOTOR_042

# Replay a whole raw recording window-by-window (stateful, hx/timespans carried across all windows)
& $py inference\inference_pipeline.py --signal path\to\signal.npy --fs 48000 --output predictions.jsonl
```

Dataset paths, window sizes/subsample caps, and model hyperparameters all live in `configs/*.json` — nothing is hardcoded in the scripts.

### TensorBoard

```powershell
& $py -m tensorboard.main --logdir reports\tensorboard
```

## Known Limitations / Honest Caveats

- **NASA IMS labels are heuristic**, not ground truth (see `reports/nasa_ims_notes.md`) — there is no per-file fault label in the source dataset, only a documented final-failure bearing/type per run.
- **Dataset scale is subsampled by default** (`configs/preprocessing_config.json`) to keep end-to-end runs tractable on a single CPU machine. Raise or remove the caps for a full-scale run.
- **"warning" has zero real-world examples across all 6 datasets** — every source is labeled strictly healthy/faulty (or a bearing fault type). The general model's "warning" output is schema-complete but empirically untested.
- **Bearing-only cross-dataset transfer is near-chance** (0.24-0.26 accuracy) because no single bearing dataset contains all 5 fault-location classes -- see `reports/cross_dataset_report.md` for the exact per-dataset class-absence breakdown.
- **Cross-modality transfer (Member1 <-> bearing) completely collapses to a single predicted class in both directions** -- see `reports/cross_modality_report.md`. The general model should be trusted within the modality/modalities it was trained on, not as a zero-shot cross-modality classifier.
- **The VAE anomaly scorer has a known, disclosed residual weakness**: even after masking reconstruction error to bearing-relevant dims, it likely still carries some cross-source confounding since it was trained on a NASA-IMS-dominated healthy mix rather than a bearing-specific-only healthy set. Treat `anomaly_score` as secondary to `fault_probability`.
- **Streaming inference beyond the training rollout length is an extrapolation.** The LTC is trained on 5-window sequences (`configs/lnn_config.json::seq_len` / `configs/ltc_general_config.json::seq_len`) with a fresh zero hidden state per sequence; `LTCInferenceEngine` then runs it continuously for arbitrarily many more steps per machine. This is standard practice for recurrent models deployed beyond their truncated-BPTT training length, but has not been separately validated at very long horizons in this project.
- See `reports/model_evaluation_report.md` (bearing specialist), `reports/general_model_evaluation_augmented.json` (general model), `reports/cross_dataset_report.md`, and `reports/cross_modality_report.md` for current accuracy/latency/size numbers -- reported as measured, not adjusted.
