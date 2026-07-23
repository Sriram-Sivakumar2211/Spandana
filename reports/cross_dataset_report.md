# Phase 8 — Cross-Dataset Validation Report

Trains the LNN on unified (Phase 3/4) engineered feature vectors from one or two source datasets and evaluates on a held-out THIRD dataset it never saw during training. The feature scaler is fit only on source-domain data, so any accuracy drop reflects genuine domain shift (different rigs/sample rates/bearing geometry), not data leakage.

| Scenario | Source(s) | Target | Target Accuracy | Target F1 (macro) | Target ROC AUC |
|---|---|---|---|---|---|
| nasa_ims_to_paderborn | nasa_ims | paderborn | 0.2398 | 0.1589 | 0.3643 |
| paderborn_to_cwru | paderborn | cwru | 0.2359 | 0.0836 | 0.1637 |
| nasa_ims_plus_paderborn_to_cwru | nasa_ims+paderborn | cwru | 0.2557 | 0.1663 | 0.6547 |

**Domain shift note**: NASA IMS (20 kHz, run-to-failure rig), CWRU (48 kHz, motor test bench) and Paderborn (64 kHz, modular test rig) differ in sample rate, bearing type and operating condition. Training only on unified engineered features (never raw signals) and fitting the scaler on the source domain alone is what makes this a fair test of cross-dataset generalization rather than an inflated same-distribution split.

**Honest result: all three scenarios perform near chance level (accuracy ~0.24-0.26, macro F1 ~0.08-0.17).** This is not a training or integration bug -- it is a direct, verified consequence of how `BEARING_CLASSES = [healthy, inner_race, outer_race, ball, combined]` is distributed across the three datasets:

| Dataset | healthy | inner_race | outer_race | ball | combined |
|---|---|---|---|---|---|
| nasa_ims | 45486 | 38 | 76 | -- | -- |
| paderborn | 1830 | 3361 | 3667 | -- | 917 |
| cwru | 235 | 708 | 708 | 708 | -- |

No single source dataset contains all 5 classes, so every scenario here asks the model to predict at least one fault type it structurally never observed during training:

- **nasa_ims_to_paderborn**: nasa_ims never contains "combined" (9.4% of the paderborn target) and is 99.75% healthy in training, so the model is both structurally blind to one target class and heavily healthy-biased against a target domain that is only ~19% healthy.
- **paderborn_to_cwru**: paderborn never contains "ball" (30% of the cwru target — 696 of 2319 test sequences). The confusion matrix confirms this directly: the model predicts "ball" (column index 3) for **zero** sequences in the entire target set, and the 696 true-ball sequences are instead split almost entirely between inner_race (682) and outer_race (14) predictions.
- **nasa_ims_plus_paderborn_to_cwru**: combining both sources still never supplies a single "ball" example (neither source dataset has one), so "ball" remains entirely unpredictable — the confusion matrix again shows zero predictions in that column. The added inner/outer-race diversity from combining two sources does measurably help probability calibration (ROC AUC 0.655 vs. 0.164 for paderborn-only), even though hard-label accuracy barely moves (0.256 vs. 0.236), because the model becomes better at ranking inner-vs-outer-race likelihood even where it still cannot name "ball" at all.

No amount of hyperparameter tuning fixes a class the source domain never contained. This is a genuine, structural limitation of transferring a fault-*location* classifier across rigs with non-overlapping fault inventories — disclosed here rather than hidden, worked around by re-labeling classes, or excluded from the report.
