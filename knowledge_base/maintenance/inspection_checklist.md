# Shopfloor Technician Maintenance Inspection Checklist

## Pre-Inspection Safety Protocol
- [ ] Verify Lockout/Tagout (LOTO) procedures are enforced prior to physical contact.
- [ ] Inspect Personal Protective Equipment (PPE): Safety glasses, steel-toed boots, cut-resistant gloves, ear protection.

## Daily Routine Checklist (Visual & Acoustic)
1. **Acoustic Check**: Listen for abnormal grinding, knocking, or high-pitched whining using ultrasonic stethoscope or mechanical probe.
2. **Thermal Check**: Measure motor housing, drive-end (DE), and non-drive-end (NDE) bearing temperatures using IR pyrometer.
3. **Oil/Grease Leakage**: Inspect baseplate and end-bells for grease leakage or dark oil weeping.
4. **Vibration Alert Verification**: Check if dashboard health score dropped below 85% or anomaly score exceeded 0.35.

## Weekly Vibration & Alignment Audit
1. Measure overall RMS vibration velocity (mm/s) at DE and NDE bearing caps in Horizontal, Vertical, and Axial directions.
2. Compare readings against ISO 10816-3 limits:
   - **Zone A (<1.8 mm/s)**: Good condition.
   - **Zone B (1.8 - 4.5 mm/s)**: Satisfactory continuous operation.
   - **Zone C (4.5 - 11.0 mm/s)**: Unsatisfactory; plan maintenance.
   - **Zone D (>11.0 mm/s)**: Dangerous; stop machine immediately.

## Monthly & Quarterly Preventative Actions
1. Re-torque foundation bolts and coupling bolts to specification.
2. Purge and replenish bearing grease cavity following `lubrication_guide.md`.
3. Measure stator winding insulation resistance ($R_{insulation} > 100 \text{ M}\Omega$).
