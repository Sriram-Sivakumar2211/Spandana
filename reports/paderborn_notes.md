# Paderborn Bearing Dataset — Technical Notes

## 1. Executive Summary
Paderborn University (KAt-DataCenter) bearing dataset. 32 bearing codes (6 healthy, 26 damaged) recorded across 4 operating conditions with ~20 repetitions each. Damage is split between artificially induced (EDM/drilling/engraving) and real damage from accelerated lifetime tests — a distinction this project preserves as `damage_mode` metadata even though the classification target only uses `damage_type` (location).

## 2. Folder Structure & Format
- Raw dir: `Paderboen bearing dataset/{bearing_code}/*.mat`, e.g. `K001/N09_M07_F10_K001_1.mat`.
- Filename encodes operating condition (rotational speed `N`, load torque `M`, radial force `F`) + bearing code + run number.
- Each `.mat` file is a MATLAB struct with a `Y` field: an array of ~7 channel structs (`force`, `phase_current_1/2`, `speed`, `temp_2_bearing_module`, `torque`, `vibration_1`). Only `vibration_1` (64 kHz) is used.
- Bearing code → health state is looked up from `configs/paderborn_bearing_codes.json`, derived from the dataset's own documentation (Lessmeier et al. 2016) rather than hardcoded in preprocessing logic, since domain experts may need to correct/extend it.
- Total: 32 codes × ~80 files = 2,560 files. No missing values found in sampled files.
- Fault class distribution (full file count): healthy=480, outer_race=960, inner_race=880, combined=240.

## 3. Windowing
- Window = 8192 samples (~0.128s @ 64kHz), step = 4096 (50% overlap).
- Subsampled to 5 files per bearing code (160 files total) by default to bound processing time — see `configs/preprocessing_config.json::paderborn.max_files_per_code`. Produced 9,775 windows: healthy=1830, inner_race=3361, outer_race=3667, combined=917.

## 4. Notes for Cross-Dataset Use
Paderborn has the widest operating-condition coverage (multiple speed/load/force combinations) of the three datasets, and the most damage categories (including `combined` inner+outer damage, unique to this dataset). It's used as a source domain for the NASA IMS → Paderborn and combined (NASA IMS + Paderborn) → CWRU cross-dataset scenarios in Phase 8.
