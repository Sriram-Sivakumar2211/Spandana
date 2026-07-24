# Rotor Imbalance & Dynamic Balancing Standard

## Overview & Fault Description
Rotor unbalance occurs when the center of mass of a rotating motor assembly does not coincide with its center of rotation. This produces a centrifugal force that rotates at the shaft speed, causing mechanical fatigue on bearings and motor housing.

## Diagnostic Evidence & Sensor Signatures
- **1X Peak Dominance**: Dominant sinusoidal vibration peak at exactly 1X shaft running frequency (e.g. 29.8 Hz for 1790 RPM motor).
- **Phase Relationship**: 90-degree phase shift between radial horizontal and radial vertical vibration measurements.
- **Directionality**: Vibration amplitude is significantly higher in the radial direction than in the axial direction.
- **Proportionality**: Vibration amplitude increases with the square of motor speed ($F = m \cdot r \cdot \omega^2$).

## Root Causes
1. **Material Deposit / Dirt Accumulation**: Uneven buildup of dust, resin, or dirt on fan blades or rotor arms.
2. **Missing Balance Weights**: Dislodged correction weights from fan or rotor rim.
3. **Eccentric Machining / Keyway Errors**: Improper shaft machining or improper key fit.
4. **Thermal Distortion**: Bowing of rotor shaft due to uneven thermal expansion under heavy electrical load.

## Inspection & Remediation Protocol
1. **Visual Cleanliness Inspection**: Inspect fan blades, rotor surfaces, and cooling channels; clean thoroughly and re-test vibration.
2. **Dynamic Balancing Procedure**:
   - Perform 1-plane or 2-plane dynamic field balancing using portable vibration analyzer and trial weights.
   - Target residual unbalance quality grade ISO 1940 G2.5 for general electric motors.
3. **Tightness Check**: Check rotor locking collar, keyways, and set screws.
