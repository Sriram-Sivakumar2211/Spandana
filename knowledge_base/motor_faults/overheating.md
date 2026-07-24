# Motor Overheating & Thermal Diagnostics Guide

## Overview & Fault Description
Thermal overheating occurs when the internal stator winding or bearing housing temperature exceeds design limits specified by the motor insulation class (Class F: 155°C limit; Class H: 180°C limit). Overheating accelerates insulation degradation exponentially (Arrhenius rate rule: winding life halves for every 10°C thermal increase).

## Diagnostic Evidence & Sensor Signatures
- **Temperature Sensors**: Stator winding RTD or thermal imaging indicating temperature above 90°C under steady operating conditions.
- **Thermal Imaging Signatures**: Hotspot ratio > 1.3, hotspot intensity > 85°C on motor frame or terminal box.
- **Current & Load Correlation**: Elevated current draw exceeding motor Nameplate Full Load Amps (FLA).

## Root Causes
1. **Blocked Ventilation**: Dust buildup, oil sludged cooling fins, or obstructed fan cowl inlet.
2. **Voltage Unbalance / Overvoltage**: Asymmetric 3-phase supply voltage causing negative-sequence currents and excessive rotor heating.
3. **Overloading**: Operating motor beyond rated brake horsepower (BHP) or service factor.
4. **Frequent Starts & Stops**: Exceeding maximum allowable starts per hour (NEMA MG-1 limits).

## Remediation & Action Protocol
1. **Immediate Thermal Reduction**:
   - Inspect external cooling fan rotation direction and cowl clearance.
   - Clean motor cooling fins with compressed air or non-conductive solvent.
2. **Electrical Audit**:
   - Measure 3-phase voltage unbalance using multimeter ($V_{unbalance} = \frac{\Delta V_{max}}{V_{avg}} \times 100\%$). If unbalance > 1%, derate motor load.
3. **Winding Insulation Test**: Perform insulation resistance (IR) test with 500V/1000V Megger; minimum acceptable IR is $R > 100 \text{ M}\Omega$.
