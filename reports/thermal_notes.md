# Thermal Image Dataset for Induction Motors — Technical Notes

## 1. Executive Summary
The Thermal Image Dataset for Induction Motors consists of infrared thermal images capturing thermal signatures across key motor subcomponents (coupling, rotor, bearings, stator body) under startup, steady-state, mechanical misalignment, and electrical load variations.

## 2. Dataset Structure
- **Root Directory**: `data/raw/thermal_motor/`
- **Total Samples**: 12,152 PNG image files
- **Image Sensors & Modes**:
  - FLIR Lepton 3.5: 16-bit Grayscale (`I;16`), 160 x 120 resolution
  - Workswell WIC 640: 16-bit Grayscale (`I;16`), 640 x 512 resolution
- **Primary Operational Conditions**:
  - `start-up-current-load-0A`: 3,102 frames (transient heating phase)
  - `current-load-4A`: 990 frames (healthy baseline under 4A load)
  - `misalignment-current-load-6A`: 803 frames (shaft misalignment under 6A load)
  - `current-load-6A`: 713 frames (healthy baseline under max load)
  - `misalignment-current-load-0A`: 698 frames (unloaded misalignment)
  - `current-load-2A`: 669 frames (healthy baseline under 2A load)
  - `misalignment-current-load-4A`: 635 frames
  - `misalignment-current-load-2A`: 604 frames
  - `misalignment-2` and `misalignment-3` series under 0A, 2A, 4A, 6A loads (varying angular/parallel offset severity).

## 3. Label Classification Mapping
- `healthy`: `current-load-2A`, `current-load-4A`, `current-load-6A`
- `warning`: `start-up-current-load-0A`, `misalignment-current-load-0A`, `misalignment-current-load-2A`
- `faulty`: `misalignment-current-load-4A`, `misalignment-current-load-6A`, `misalignment-2-*`, `misalignment-3-*`

## 4. Extraction & Normalization Strategy
- Resized to standard model input dimensions (128x128 pixels).
- Min-Max scaling per frame to preserve localized thermal gradients and hotspot contrast.
- Extracted features:
  - Mean thermal intensity (`thermal_mean`)
  - Max thermal intensity (`thermal_max`)
  - Hotspot ratio (% pixels > 85th percentile intensity)
  - Hotspot intensity (`thermal_hotspot_intensity`)
  - Intensity standard deviation (`thermal_std`)
