# NASA IMS Bearing Dataset — Technical Notes

## 1. Executive Summary
Run-to-failure vibration dataset from the NSF I/UCR Center for Intelligent Maintenance Systems (IMS). Three test runs, each recording 4 rolling-element bearings continuously until one of them failed. Unlike CWRU/Paderborn, IMS ships with **no per-file fault label** — only a post-mortem teardown note of which bearing eventually failed and how.

## 2. Folder Structure & Format
- Raw dir: `Nasa IMS dataset/{1st_test,2nd_test,3rd_test}`.
- Nesting is inconsistent across the three runs on disk (`1st_test/1st_test/`, `2nd_test/2nd_test/`, `3rd_test/4th_test/txt/`); `preprocessing/nasa_ims_preprocess.py::_find_snapshot_dir` walks the tree to find the actual snapshot files rather than assuming a fixed depth.
- Each snapshot is a plain-text, tab-separated file named `YYYY.MM.DD.HH.MM.SS`, containing 20,480 samples (~1.02s) at 20 kHz.
- **1st_test**: 2,156 snapshots, 8 channels (2 accelerometers × 4 bearings). Documented failures: bearing 3 developed an inner-race defect, bearing 4 a roller/ball defect.
- **2nd_test**: 984 snapshots, 4 channels (1 per bearing). Documented failure: bearing 1, outer race.
- **3rd_test**: 6,324 snapshots, 4 channels. Documented failure: bearing 3, outer race.
- No missing values found in sampled files across any run.

## 3. Label Derivation (heuristic — see `_TEST_CONFIG` in `nasa_ims_preprocess.py`)
Since there is no ground-truth failure timestamp, health state is inferred per snapshot:
1. Compute RMS trend of the documented failing channel across the whole run.
2. Baseline = mean RMS over the first 10% of the run (early, presumed-healthy life).
3. Snapshots where RMS > `onset_factor` (default 3×) baseline are labeled with the run's documented eventual fault type; everything before that is `healthy`.
4. Every non-failing channel/bearing in the same run is labeled `healthy` for its entire duration.

This is explicitly a heuristic, not certified ground truth — flagged as such everywhere it's used downstream (EDA report, unified dataset summary).

## 4. Windowing
- Window = 2048 samples (~0.1s @ 20kHz), step = 1024 (50% overlap).
- With the default subsample cap (`max_files_per_test=150`, evenly spaced across each run), this produced 45,600 windows in this project's run, heavily skewed toward `healthy` (>99%) since most of a bearing's life is healthy — expected for run-to-failure data. Raising `max_files_per_test` (or lowering `onset_factor`) increases fault-window coverage at the cost of longer processing time.
