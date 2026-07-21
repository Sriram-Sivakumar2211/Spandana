# MetroPT-3 Dataset — Technical Notes

## 1. Executive Summary
The MetroPT-3 dataset is a multivariate industrial time-series benchmark collected from an Air Production Unit (APU) installed on APoP metro trains. It contains 1,516,948 continuous sensor readings recorded at 1Hz sampling frequency across 15 analog and digital sensor channels.

## 2. File & Column Breakdown
- **Path**: `data/raw/metropt3/MetroPT3(AirCompressor).csv`
- **Total Samples**: 1,516,948 rows
- **Sampling Frequency**: 1 Hz (1 sample per second)
- **Columns**:
  1. `Unnamed: 0`: Raw row index (dropped during preprocessing)
  2. `timestamp`: ISO-8601 formatted datetime string (`YYYY-MM-DD HH:MM:SS`)
  3. `TP2` (float): Pressure measured at the compressor output (bar)
  4. `TP3` (float): Pressure generated at the pneumatic panel (bar)
  5. `H1` (float): Pressure drop across the cyclonic separator filter (bar)
  6. `DV_pressure` (float): Pressure drop when drying towers discharge air (bar)
  7. `Reservoirs` (float): Downstream air reservoir pressure (bar)
  8. `Oil_temperature` (float): Oil temperature on the compressor (°C)
  9. `Motor_current` (float): Electrical current drawn by one phase of the compressor motor (A)
  10. `COMP` (binary/float): Electrical signal controlling the intake valve
  11. `DV_eletric` (binary/float): Electrical signal controlling the compressor outlet valve
  12. `Towers` (binary/float): Active drying tower indicator (tower A vs tower B)
  13. `MPG` (binary/float): Compressor start-up under load signal
  14. `LPS` (binary/float): Low pressure sensor signal (<7.0 bar warning)
  15. `Pressure_switch` (binary/float): Air-drying tower discharge sensor
  16. `Oil_level` (binary/float): Low oil level alert signal
  17. `Caudal_impulses` (float): Air flow rate impulse counts

## 3. Data Cleaning & Label Mapping
- **Missing Values**: 0 missing values across all sensor channels.
- **Chronological Verification**: Timestamps sorted in ascending order; interval checked for gaps.
- **Derived Condition Labels**:
  - `healthy`: Standard operating pressure (TP2/TP3 between 8-10 bar, normal motor current, oil temperature < 70°C).
  - `warning`: Oil temperature elevated (70°C - 85°C) or motor current spikes during load transition.
  - `faulty`: LPS active (<7 bar drop), oil temperature > 85°C, or severe pressure drop in `DV_pressure`.

## 4. Windowing Requirements
- Fixed-width sliding window of 60 seconds (60 samples @ 1Hz) with a step of 10 seconds (50 samples overlap).
- Time order preserved strictly without shuffling.
