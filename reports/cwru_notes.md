# CWRU Bearing Dataset — Technical Notes

## 1. Executive Summary
Case Western Reserve University Bearing Data Center dataset — the standard benchmark for bearing fault classification. This project's raw folder holds a curated 1 hp (motor load 1) subset: 10 `.mat` recordings covering Normal, Inner Race, Outer Race and Ball faults at three defect diameters (0.007", 0.014", 0.021").

## 2. Folder Structure & Format
- Raw dir: `CWRU bearing dataset/raw/*.mat`.
- Filenames encode ground truth directly, e.g. `IR014_1_175.mat` = Inner Race fault, 0.014" defect, 1 hp load, file id 175; `OR007_6_1_136.mat` additionally encodes the 6 o'clock defect position; `Time_Normal_1_098.mat` = healthy baseline.
- Each `.mat` file stores multiple channels as top-level MATLAB variables, e.g. `X123_DE_time` (drive-end accelerometer), `X123_FE_time` (fan-end), `X123RPM`. `preprocessing/cwru_preprocess.py` prefers DE > FE > BA, matching standard CWRU fault-diagnosis literature.
- Sample rate: 48 kHz (this subset). No missing values found.
- Fault class distribution (raw files): 3 ball, 3 inner_race, 3 outer_race, 1 healthy.

## 3. Windowing
- Window = 4096 samples (~0.085s @ 48kHz), step = 2048 (50% overlap).
- All 10 files processed in full (no subsampling needed — small file count), producing 2,359 windows: 708 each of ball/inner_race/outer_race, 235 healthy (fewer healthy windows simply because there is only 1 healthy recording vs 3 recordings per fault type).

## 4. Notes for Cross-Dataset Use
CWRU is the best-labeled and most balanced of the three datasets (explicit filename ground truth, no heuristic needed), making it a good target-domain choice for cross-dataset validation (Phase 8) — its high label quality avoids confounding domain-shift measurements with label-quality issues from a heuristic dataset like NASA IMS.
