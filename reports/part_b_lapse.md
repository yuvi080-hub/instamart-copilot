### B.4 Lapse problem and baseline (cutoff 2025-09-01)

| figure | value |
|---|---|
| cohort customers | 1156.0 |
| lapsed | 443.0 |
| lapsed % | 38.32 |
| train rows | 924.0 |
| test rows | 232.0 |
| baseline accuracy % | 61.6 |
| baseline lapsed F1 | 0.0 |

### B.5 Leak-free preprocessing

Fitted-scaler mean of frequency (training rows only) = 8.115; full-cohort mean of frequency = 8.029. They differ because the scaler has seen only the 924 training rows, so its mean is a sample estimate that excludes the 232 test rows.

Missing values in any feature column: 0 (asserted in code).

### B.6 Tuning and test evaluation (positive class = lapsed)

| model | best params | best CV F1 | test precision | test recall | test F1 | confusion [[TN,FP],[FN,TP]] |
|---|---|---|---|---|---|---|
| LogisticRegression | {'clf__C': 100} | 0.651 | 0.644 | 0.652 | 0.648 | [[111, 32], [31, 58]] |
| RandomForest | {'clf__max_depth': 8, 'clf__min_samples_leaf': 10} | 0.681 | 0.659 | 0.652 | 0.655 | [[113, 30], [31, 58]] |

Selected model: **RandomForest** (higher cross-validated F1). Test F1 = 0.655 (requirement >= 0.55).

### B.7 Class-balance experiment (over-sampling training set only)

Training counts after over-sampling: {1: 570, 0: 570}.

| model | precision | recall | F1 |
|---|---|---|---|
| LR un-balanced | 0.644 | 0.652 | 0.648 |
| LR over-sampled | 0.589 | 0.854 | 0.697 |

### B.8 Interpretation

**Top-5 random-forest feature importances**

| feature | importance |
|---|---|
| num__frequency | 0.28 |
| num__monetary | 0.271 |
| num__recency | 0.115 |
| num__avg_delivery | 0.061 |
| num__cancel_rate | 0.052 |

**Logistic regression coefficients (standardised features)**

| feature | coefficient |
|---|---|
| num__recency | 0.04 |
| num__frequency | -1.698 |
| num__monetary | 0.285 |

Saved `outputs/lapse_model.joblib`; reloaded model reproduces test predictions and probabilities exactly: True.

### B.9 Retention list

Premium customers in the test set: 40. List written to `outputs/retention_list.csv` (10 rows); 1 of 10 truly lapsed.

| customer_id | lapse_probability | actually_lapsed |
|---|---|---|
| C0862 | 0.491 | 0 |
| C1112 | 0.4841 | 0 |
| C0060 | 0.4798 | 0 |
| C0802 | 0.4796 | 0 |
| C1008 | 0.4778 | 0 |
| C1000 | 0.4624 | 0 |
| C0525 | 0.4597 | 1 |
| C0133 | 0.4562 | 0 |
| C0267 | 0.4525 | 0 |
| C0167 | 0.4522 | 0 |
