# Electrical Current Anomalies & Stator/Rotor Faults

## Overview & Fault Description
Electrical faults in induction motors include stator winding short circuits, phase current unbalance, broken rotor bars, and high resistance connections. Motor Current Signature Analysis (MCSA) captures sideband modulation around the fundamental line frequency (50 Hz / 60 Hz).

## Diagnostic Evidence & Sensor Signatures
- **Current Signature (MCSA)**: Sideband frequencies around line frequency $f_L$ at $f_{rb} = f_L (1 \pm 2s)$, where $s$ is motor slip.
- **Current Unbalance**: Phase current RMS deviation exceeding 5% between phases (L1, L2, L3).
- **Vibration Modulation**: Twice line frequency ($2 f_L$, 100 Hz / 120 Hz) vibration peak that vanishes instantly when motor power is cut off.

## Root Causes
1. **Broken / Cracked Rotor Bars**: Thermal stress and frequent across-the-line starting duty cycles.
2. **Turn-to-Turn Stator Short**: Insulation breakdown due to thermal aging, moisture, or surge voltages.
3. **Loose Terminal Box Connections**: Contact resistance creating localized heating and voltage drop.

## Maintenance & Inspection Protocol
1. **Power Off Vibration Cut Check**: Record vibration spectrum while tripping motor breaker. If 100/120 Hz peak collapses immediately, fault is purely electrical/magnetic.
2. **Current Spectrum Audit**: Perform FFT on stator current signal; verify sideband peak amplitude is >45 dB below fundamental line peak.
3. **Corrective Actions**:
   - Re-torque terminal lug bolts to manufacturer specification.
   - Perform Surge Test and Resistance Balance Test on stator phases.
