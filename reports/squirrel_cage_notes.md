# Squirrel-Cage Induction Motor Fault Diagnosis Dataset — Technical Notes

## 1. Executive Summary
The Squirrel-Cage Induction Motor dataset contains high-resolution thermal imaging captured during controlled fault induction experiments on industrial three-phase squirrel-cage induction motors. The focus of this dataset is rotor bar damage detection under varying electrical load conditions.

## 2. Dataset Structure
- **Root Directory**: `data/raw/squirrel_cage/`
- **Total Samples**: 1,610 high-resolution thermal frames (`.png`)
- **Image Format**: 16-bit Grayscale Raw Intensity (`I;16`), Resolution: 640 x 512 pixels (captured using Workswell InfraRed Camera WIC 640).
- **Subdirectories & Class Balance**:
  - `rotor-1-current-load-0A-coupling-tightened`: 211 frames
  - `rotor-6-current-load-2A`: 161 frames
  - `rotor-6-current-load-0A`: 157 frames
  - `rotor-1-current-load-0A`: 126 frames
  - `rotor-3-current-load-0A`: 123 frames
  - `rotor-6-current-load-4A`: 122 frames
  - `rotor-3-current-load-6A`: 119 frames
  - `rotor-3-current-load-2A`: 109 frames
  - `rotor-3-current-load-4A`: 103 frames
  - `rotor-6-current-load-6A`: 100 frames
  - `rotor-1-current-load-4A`: 94 frames
  - `rotor-1-current-load-6A`: 94 frames
  - `rotor-1-current-load-2A`: 91 frames

## 3. Label Schema
- **Healthy / Mild**: `rotor-1` under 0A-2A load
- **Warning**: `rotor-1` under high load (4A-6A), `rotor-3` under low load (0A-2A)
- **Faulty**: `rotor-3` under high load (4A-6A), `rotor-6` under all load conditions (0A-6A)

## 4. Key Considerations for Pipeline
- **Pixel Intensity Normalization**: 16-bit integer values mapped to float [0, 1] via `(pixel - min_val) / (max_val - min_val)`.
- **Feature Extraction**: Mean temperature/intensity, max thermal hotspot intensity, standard deviation, and hotspot surface area ratio.
- **No Temporal Leakage**: Grouping during sliding window creation is performed by experiment run rather than random shuffling across runs.
