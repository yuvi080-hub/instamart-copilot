# Instamart Customer Intelligence & Support Copilot

## Overview

An internal tool built in four connected parts on **synthetic data only** (nothing here is real Instamart data; all amounts are in INR).

| Part | What it does | Main files | Main outputs |
|---|---|---|---|
| A | Audit and clean the raw exports, store in SQLite, answer business questions in SQL and pandas | `part_a/audit_clean.py`, `part_a/validate.py`, `part_a/analysis.py`, `sql/queries.sql` | `data/clean/*.csv`, `data/instamart.db` |
| B | RFM + K-means customer segments, lapse prediction model | `part_b/segments.py`, `part_b/lapse_model.py` | `outputs/customer_segments.csv`, `outputs/lapse_model.joblib`, `outputs/retention_list.csv` |
| C | Support-ticket triage with privacy redaction, retries, validation, token budget, routing | `part_c/triage.py` | `outputs/triage_results.csv`, `outputs/triage_budget_demo.csv` |
| D | TF-IDF policy assistant and a ReAct refund agent with safe stopping and resume | `part_d/rag.py`, `part_d/agent.py`, `part_d/run_part_d.py` | `outputs/agent_runs.jsonl`, `outputs/refund_ledger.jsonl`, `state/` |

`generate_data.py` and `mock_llm.py` are the supplied files, committed unmodified. Every model call goes through the offline `mock_llm.py`: no network, no API key. Libraries: standard library, pandas, numpy, scikit-learn, joblib (Python 3.11+; developed on Python 3.13).

Each script writes a report fragment into `reports/`; `make_readme.py` assembles this README from those fragments, so every number below was produced by the code, not typed by hand.

## Reproduce

Run from the repository root (Linux/macOS shown; on Windows PowerShell activate with `.venv\Scripts\Activate.ps1`):

1. `python -m venv .venv`
2. `source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `python generate_data.py` (last line: `generated: customers=1200 products=40 orders_raw=13084 tickets=164`)
5. `python part_a/audit_clean.py`
6. `python part_a/validate.py` (prints `ALL CHECKPOINTS PASSED`)
7. `python part_a/analysis.py`
8. `python part_b/segments.py`
9. `python part_b/lapse_model.py`
10. `python part_c/triage.py`
11. `python part_d/run_part_d.py`
12. `python make_readme.py` (optional: rebuilds this README from `reports/` and `docs/`)

Fixed seeds: `random_state=42` everywhere in scikit-learn, `random.seed(42)` for retry jitter. `part_d/run_part_d.py` deletes and rewrites the agent outputs, so it can be re-run safely.

## Part A

Data foundation: audit, clean, store, query. Cleaning scripts apply the rules in the order the brief gives; numbers of rows/values changed are in the table below.

### A.1 Raw-data audit

**customers.csv** - shape (1200, 5)

| index | dtype | missing | missing_% |
|---|---|---|---|
| customer_id | str | 0 | 0.0 |
| city | str | 0 | 0.0 |
| signup_date | str | 0 | 0.0 |
| age | float64 | 61 | 5.08 |
| gender | str | 30 | 2.5 |

**products.csv** - shape (40, 4)

| index | dtype | missing | missing_% |
|---|---|---|---|
| product_id | str | 0 | 0.0 |
| product_name | str | 0 | 0.0 |
| category | str | 0 | 0.0 |
| price_inr | int64 | 0 | 0.0 |

**orders.csv** - shape (13084, 9)

| index | dtype | missing | missing_% |
|---|---|---|---|
| order_id | str | 0 | 0.0 |
| customer_id | str | 0 | 0.0 |
| product_id | str | 0 | 0.0 |
| quantity | int64 | 0 | 0.0 |
| order_ts | str | 0 | 0.0 |
| status | str | 0 | 0.0 |
| discount_pct | int64 | 0 | 0.0 |
| order_amount | str | 0 | 0.0 |
| delivery_minutes | float64 | 2541 | 19.42 |

**Audit figures**

| figure | value |
|---|---|
| raw orders.csv rows | 13084 |
| exact duplicate rows | 119 |
| rows with status pending | 656 |
| distinct order_id | 12309 |
| order_amount entries not convertible to number | 120 |
| negative delivery_minutes | 106 |
| blank delivery_minutes | 2541 |
| customers: blank age | 61 |
| customers: age outside 10-100 | 6 |
| customers: distinct raw city spellings | 24 |
| customers: distinct non-blank raw gender spellings | 10 |
| customers: blank gender | 30 |

### A.2 Cleaning rules and rows/values changed

| rule | count | meaning |
|---|---|---|
| customers: city strip + title case | 476 | values changed |
| customers: gender mapped to male/female/unknown | 950 | values changed |
| customers: ages outside 10-100 set missing (total missing incl. blanks) | 67 | values missing before fill |
| customers: missing age -> median age of city | 67 | values filled |
| customers: signup_date -> datetime | 1200 | all rows |
| i. order_ts -> datetime | 13084 | all rows parsed |
| ii. drop exact duplicate rows | 119 | rows removed |
| iii. keep latest order_ts per order_id (drops earlier pending records) | 656 | rows removed |
| iv. unparseable order_amount -> NaN -> price x qty x (1-disc/100) | 112 | values filled |
| v. negative delivery_minutes -> NaN | 105 | values set to missing |
| v. completed orders: fill missing delivery_minutes with category median (completed) | 774 | values filled |
| v. cancelled orders: delivery_minutes left missing | 1199 | rows left missing |

**Clean orders summary**

| check | value |
|---|---|
| rows (one per order_id) | 12309 |
| completed | 11110 |
| cancelled | 1199 |
| pending | 0 |
| missing order_amount | 0 |
| missing delivery_minutes (completed) | 0 |
| missing delivery_minutes (cancelled) | 1199 |
| sum order_amount completed (INR) | 2,998,668.80 |

**Clean customers**: cities Pune 227, Delhi 210, Bengaluru 197, Chennai 191, Hyderabad 191, Mumbai 184; genders female 610, male 560, unknown 30; missing ages 0; age range 18-60.

### A.3 SQL analysis (queries in `sql/queries.sql`)

| result | mine | reference |
|---|---|---|
| Q1 customers with >8000 on orders >500 | 30 | 30 |
| Q2 rows | 30 | 30 |
| Q2 sum of revenues (INR) | 2,998,668.80 | 2,998,668.80 |
| Q2 largest cell | Bengaluru / Electronics INR 233,909.45 | Bengaluru / Electronics 233,909.45 |
| Q3 products above average price | 11 | 11 |
| Q4 customers without completed order | 25 | 25 |
| Q5 customers above average | 550 | 550 |
| Q5 average spend (INR) | 2552.06 | 2,552.06 |
| Q6 rows where RANK != ROW_NUMBER | 8 | 8 |
| Q7 daily rows | 183 | 183 |
| Q7 last cumulative (INR) | 2,998,668.80 | 2,998,668.80 |

**Q6 top customer per city (ROW_NUMBER = 1)**

| city | customer_id | total_spend |
|---|---|---|
| Bengaluru | C0082 | 12856.2 |
| Chennai | C0930 | 10151.4 |
| Delhi | C0291 | 13742.6 |
| Hyderabad | C0743 | 12730.05 |
| Mumbai | C0693 | 14766.55 |
| Pune | C0426 | 10377.1 |

RANK() differs from ROW_NUMBER() on 8 rows because customers with identical total_spend in the same city share one RANK (the next rank is skipped) while ROW_NUMBER() always gives each row a unique consecutive number.

### A.4 pandas cross-check and exploratory analysis

pivot_table grand total = INR 2,998,668.80; SQL Q2 total = INR 2,998,668.80; equal: True

**Per-city completed order_amount**

| city | total | mean | count |
|---|---|---|---|
| Bengaluru | 523643.4 | 276.47 | 1894 |
| Chennai | 463629.15 | 272.72 | 1700 |
| Delhi | 502829.8 | 243.62 | 2064 |
| Hyderabad | 528589.9 | 284.95 | 1855 |
| Mumbai | 479058.5 | 297.0 | 1613 |
| Pune | 500918.05 | 252.48 | 1984 |

**order_amount statistics (completed)**

| stat | value |
|---|---|
| mean | 269.91 |
| median | 135.0 |
| skewness | 4.61 |
| Q1 | 64.8 |
| Q2 | 135.0 |
| Q3 | 297.0 |
| IQR | 232.2 |
| lower fence | -283.5 |
| upper fence | 645.3 |
| outliers below | 0.0 |
| outliers above | 897.0 |

**Correlation matrix (completed orders)**

|  | order_amount | discount_pct | quantity | delivery_minutes |
|---|---|---|---|---|
| order_amount | 1.0 | -0.095 | 0.087 | -0.003 |
| discount_pct | -0.095 | 1.0 | -0.0 | -0.01 |
| quantity | 0.087 | -0.0 | 1.0 | -0.013 |
| delivery_minutes | -0.003 | -0.01 | -0.013 | 1.0 |

**EDA answers (own words, under 200 words).**
*What is the data about?* 11,110 completed Instamart orders (April-September 2025) from 1,175 customers in six cities, mostly low-value grocery, dairy and snack baskets plus a few electronics.
*Distributions?* order_amount is strongly right-skewed: mean INR 269.91 sits far above the median INR 135.00, skewness is about 4.61, and the middle half of orders lies between INR 64.80 and INR 297.00.
*Outliers?* The upper fence is INR 645.30 and 897 orders exceed it; none fall below the lower fence. These are genuine high-priced electronics orders, not errors, so they were kept.
*Relationships?* All correlations are weak. The largest in absolute value is order_amount with discount_pct (about -0.095), just ahead of order_amount with quantity (+0.087); delivery time is essentially uncorrelated with everything. A correlation this small, even if consistent, does not establish causation - discounts may simply be applied to different baskets.

`python part_a/validate.py` asserts 21 reference checkpoints (raw audit counts, clean row counts, revenue INR 2,998,668.80, city/gender counts, age range) and prints `ALL CHECKPOINTS PASSED`.

## Part B

Segments and lapse prediction. Only completed orders are used for customer behaviour.

### B.1 RFM table (snapshot 2025-10-01 00:00:00)

| figure | value |
|---|---|
| customers | 1175 |
| recency median | 19.0 |
| recency min | 0 |
| recency max | 180 |
| frequency mean | 9.46 |
| frequency max | 33 |
| monetary mean | 2552.06 |
| monetary max | 14766.55 |

### B.2 K-means (StandardScaler, n_init=10, random_state=42)

| K | inertia | silhouette |
|---|---|---|
| 2 | 1820.8 | 0.465 |
| 3 | 1268.2 | 0.445 |
| 4 | 743.1 | 0.526 |
| 5 | 617.4 | 0.48 |
| 6 | 503.2 | 0.482 |
| 7 | 408.5 | 0.416 |
| 8 | 366.5 | 0.412 |

### B.3 Segment profile for K=4

| segment_id | size | mean_recency | mean_frequency | mean_monetary | name | premium | action |
|---|---|---|---|---|---|---|---|
| 0 | 436 | 28.86 | 3.77 | 1057.62 | Occasional Basket Buyers | False | Nudge towards a second weekly order with free-delivery thresholds. |
| 1 | 138 | 24.12 | 6.77 | 7129.7 | Premium Big-Basket Buyers | True | Dedicated concierge offers and early access to electronics deals; protect with proactive retention. |
| 2 | 419 | 8.77 | 19.4 | 3410.02 | Loyal Frequent Shoppers | False | Loyalty points and subscription (daily-essentials) bundles; do not over-discount. |
| 3 | 182 | 109.04 | 2.2 | 685.99 | Lapsing Low-Activity | False | Win-back push with a time-limited coupon; cheap channel (push/SMS) only. |

PCA(n_components=2) explained_variance_ratio_: 0.634 and 0.218, total 0.852.

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

### B.10 Written answers

**Choice of K.** The inertia curve drops steeply from K=2 to K=4 (1820.8 -> 1268.2 -> 743.1) and then flattens (617.4 at K=5, 503.2 at K=6), so the elbow is at K=4, and K=4 also has the highest silhouette (0.526 versus 0.480 for K=5). I chose **K=4**: it is the best on both metrics and gives four segments (436 / 138 / 419 / 182) that the business can act on, whereas K=5 only splits an existing group.

**Why inertia alone cannot pick K.** Inertia is the sum of squared distances to the nearest centroid, so adding clusters can never increase it - K=8 (366.5) is always below K=2 (1820.8), and K=n (every point its own cluster) would reach 0. Because it falls with K by construction, it must be read for the *bend* (elbow) together with the silhouette score and business usefulness, not for its minimum.

**Cluster ids are labels only.** The numbers 0-3 carry no order or ranking; K-means may number the same groups differently with another seed. The Premium flag therefore follows the segment with the highest mean monetary value (segment 1: mean monetary INR 7,129.70, 138 customers), not a cluster number.

**Model choice.** Random forest was selected because it had the higher cross-validated F1 (0.681 versus 0.651) and a slightly higher test F1 (0.655 versus 0.648, 58 of 89 lapsing customers caught in both). Missing a lapsing customer means a lost customer and all their future orders, while wrongly targeting a loyal customer only costs one coupon or message, so recall on the lapsed class matters more than precision; both models reach about 0.65 recall, and the forest is not worse on either metric and needs no separate threshold tuning. Both clear the F1 >= 0.55 requirement.

**Class-balance result.** Over-sampling the lapsed class in the training set moved **recall** the most (0.652 -> 0.854), while precision fell (0.644 -> 0.589) and F1 rose to 0.697. For the retention team this means they would reach about one in five more lapsing customers at the price of contacting more customers who would have stayed anyway - acceptable when a campaign message is cheap.

**Feature readings.** Random forest top-5: frequency (0.280) and monetary (0.271) dominate - customers who order often and spend more are far less likely to stop; recency (0.115) says how long they have already been silent; average delivery time (0.061) and cancellation rate (0.052) hint that bad service experiences push customers away. Logistic regression coefficients (standardised): **frequency is strongly negative (-1.70)** - more orders, less lapse; **monetary is positive (+0.28)** - once frequency is controlled for, higher spend per order goes with slightly more lapse (high-ticket buyers order rarely); **recency is slightly positive (+0.04)** - a longer silence raises lapse risk, but weakly once frequency is in the model.

**Leakage statement.** No encoder, scaler or resampler saw any test row: the pipeline is fitted on the 924 training rows only (inside `GridSearchCV` each fold fits its own copy) and over-sampling is applied to the training rows only. No order dated 2025-09-01 or later entered any feature, and the segment labels from task 3 were not used as features.

**Retention list caveat.** The retention list is illustrative and not a leakage-free evaluation, because the Premium flag comes from whole-window RFM that includes the September lapse window (it is a post-hoc label). Only 1 of the 10 listed Premium customers actually lapsed, which is consistent with Premium customers rarely lapsing at all.

## Part C

Support-ticket triage (tickets processed in file order; all model calls via `mock_llm.py`).

### C.1 Input guardrails

Empty tickets (status `skipped_empty`, never sent to the model): 4. Tickets with est_tokens > 400 (status `flagged_long`, never sent): 4, each estimated at [734] tokens.

### C.2 Redaction (applied in order email, phone, order id)

| type | substitutions |
|---|---|
| EMAIL | 55 |
| PHONE | 91 |
| ORDER_ID | 132 |
| TOTAL | 278 |
| left after re-applying patterns | 0 |

### C.3 Prompts

Zero-shot prompt (26 est. tokens):

```
You CLASSIFY customer support tickets. Allowed categories: billing, delivery, technical, fraud. Reply with JSON only, exactly {"category": "...", "reason": "..."}.
```

Few-shot prompt (141 est. tokens):

```
You CLASSIFY customer support tickets. Allowed categories: billing, delivery, technical, fraud. Reply with JSON only, exactly {"category": "...", "reason": "..."}.
EXAMPLES:
Ticket: Someone hacked my account and used my wallet, this is fraud. -> {"category": "fraud", "reason": "unauthorized account use"}
Ticket: There is an unauthorized transaction on my card for [ORDER_ID]. -> {"category": "fraud", "reason": "unauthorized transaction"}
Ticket: The app crashes and shows an error when I open the cart. -> {"category": "technical", "reason": "app failure"}
Ticket: I was charged twice for [ORDER_ID]. -> {"category": "billing", "reason": "double charge"}
Ticket: My order [ORDER_ID] is very late and the rider is not answering. -> {"category": "delivery", "reason": "late delivery"}
```

### C.4 Resilient calls

Retry log (zero-shot run): 19 retry lines, one per TransientLLMError; every retry was retry number [0] with waits between 0.0453s and 0.0562s (allowed 0.045-0.0575s). Few-shot run log: `reports/part_c_retry_log_few_shot.txt`. All transient errors were recovered by the first retry; no ticket ended with a permanent error.

Example log lines:

```
RETRY ticket=T0002 retry=0 wait=0.0530s
RETRY ticket=T0116 retry=0 wait=0.0453s
RETRY ticket=T0153 retry=0 wait=0.0484s
```

### C.5-C.6 Validation and prompt comparison (156 eligible tickets per run)

| prompt | classified | accuracy | total tokens | tokens / classified ticket | classified_json | classified_keyword | flagged_invalid_output | transient errors | retry lines |
|---|---|---|---|---|---|---|---|---|---|
| zero-shot | 147 | 85.7% (126 of 147) | 8464 | 57.6 | 135 | 12 | 9 | 19 | 19 |
| few-shot | 147 | 100.0% (147 of 147) | 26404 | 179.6 | 135 | 12 | 9 | 19 | 19 |

Zero-shot confusion table (rows = true category, columns = predicted):

| true \ predicted | billing | delivery | technical | fraud |
|---|---|---|---|---|
| billing | 38 | 0 | 0 | 0 |
| delivery | 0 | 36 | 0 | 0 |
| technical | 10 | 0 | 29 | 0 |
| fraud | 11 | 0 | 0 | 23 |

### C.7 Token budget, routing and output

Budget demo: zero-shot prompt (26 est. tokens) with TOKEN_BUDGET = 6000: **45 tickets ended `budget_exhausted`** (token total 6027); saved to `outputs/triage_budget_demo.csv`.

Final `outputs/triage_results.csv` (few-shot, TOKEN_BUDGET = 100000, 164 rows):

Status counts:

| status | tickets |
|---|---|
| classified_json | 135 |
| classified_keyword | 12 |
| flagged_invalid_output | 9 |
| skipped_empty | 4 |
| flagged_long | 4 |

Route counts:

| route | priority | tickets |
|---|---|---|
| human_review | NORMAL | 17 |
| premium_desk | HIGH | 11 |
| security_team | HIGH | 34 |
| support_queue | NORMAL | 102 |

### C.8 Written answers

**When is few-shot worth its extra tokens?** The few-shot prompt costs 179.6 tokens per classified ticket against 57.6 for zero-shot (about 3.1x; 26,404 versus 8,464 tokens over 147 classified tickets), because every call re-sends the five examples. In return accuracy rose from 85.7% (126 of 147) to 100% (147 of 147): the zero-shot model sent 11 fraud tickets and 10 technical tickets to billing. The extra 17,940 tokens bought 21 correct tickets, about 854 tokens each, which is cheap when a missed fraud ticket loses the 2-hour security-team deadline of the escalation policy; for a low-stakes classification where 86% is good enough, the cheaper zero-shot prompt (or a shorter few-shot prompt with only the confusing categories) would be the better economy.

**Which outputs were rule-validated and which went to humans.** 147 of 164 tickets (135 `classified_json` and 12 `classified_keyword`) passed an automatic rule check: valid JSON with an allowed category, or exactly one allowed category word in a non-JSON reply. The other 17 tickets (4 `skipped_empty`, 4 `flagged_long`, 9 `flagged_invalid_output`) were never guessed and are routed to `human_review`. No `budget_exhausted` ticket occurs in the final run (budget 100000, 26,404 tokens used); the separate 6,000-token zero-shot demo shows the budget stopping the run.

**Privacy check.** An assertion in `part_c/triage.py` re-applies the three patterns to every system and user message that was sent to the model (156 prompts per run) and finds nothing; the user message is exactly the redacted ticket text. Redaction is regular-expression based, so personal data written in unusual formats (for example a phone number with spaces) would not be caught.

## Part D

Policy RAG assistant (`part_d/rag.py`) and refund agent (`part_d/agent.py`); tools `get_order`, `search_policy`, `calculate_refund`, `issue_refund`, `escalate_to_human` are listed in `TOOLS_SPEC` and dispatched through `TOOL_MAP`.

### D.1 Chunking

40-word chunks with 10-word overlap: **15 chunks** - delivery 3, escalation 3, payment 3, privacy 2, refund 4.

### D.2 Retrieval

Query `refund policy late delivery` -> top-3 sources: ['refund_policy.txt', 'refund_policy.txt', 'refund_policy.txt'].

### D.3-D.4 Grounded answers and evaluation

| setting | chunks | expected_doc in top 3 (12 answerable) | answer contains expected_fact (12) | fallback on unanswerable (2) |
|---|---|---|---|---|
| overlap 10 | 15 | 12/12 | 12/12 | 2/2 |
| overlap 0 | 13 | 12/12 | 10/12 | 2/2 |

Questions that break with overlap 0:

- *What delivery time makes a completed order eligible for a full refund?* - doc_in_top3=True, fact_in_answer=False; answer was: "receives a full refund of the order amount."
- *How soon is money returned when a payment fails but is deducted?* - doc_in_top3=True, fact_in_answer=False; answer was: "If a payment fails but money is deducted, the amount is returned automatically   1000 must be approved by a human support lead before money is returned."

### D.5-D.6 Seven scenario results (default limits: 6 iterations, 6000 tokens, 10 s)

| scenario | status | refund INR | expected INR | model calls | tokens used | matches expected |
|---|---|---|---|---|---|---|
| S1 | REFUND | 128.25 | 128.25 | 5 | 1102 | yes |
| S2 | REFUND | 135.00 | 135.00 | 5 | 1102 | yes |
| S3 | ESCALATE | 1999.00 | 1999.00 | 5 | 1089 | yes |
| S4 | DENIED | 0.00 | 0.00 | 4 | 769 | yes |
| S5 | DENIED | 0.00 | 0.00 | 3 | 460 | yes |
| S6 | NOT_FOUND | 0.00 | 0.00 | 2 | 154 | yes |
| S7 | FALLBACK_MAX_ITERATIONS | 0.00 | 0.00 | 6 | 3246 | yes |

### D.7 Stop-safely demonstrations

| run | status | detail |
|---|---|---|
| S7 default limits | FALLBACK_MAX_ITERATIONS | 6 model calls, 3246 tokens (limit 6000 not hit) |
| S1 with token_limit=200 | FALLBACK_TOKEN_LIMIT | 3 model calls, 477 tokens; tools executed before stop: ['get_order', 'search_policy'] (the tool requested by the call that crossed the limit was not executed) |
| S1 with time_limit_seconds=0 | FALLBACK_TIMEOUT | 0 model calls, stops before the first model call |

Example hand-off summary (token-limit demo): `HANDOFF TO HUMAN AGENT: token limit 200 exceeded (477 used). Steps completed so far: get_order, search_policy. Please review order request: My order ORD-100048 reached me very late. I would like a refund.`

### D.8 Crash and resume (S1)

A simulated crash was raised right after the second tool execution (checkpoint `state/S1-crash.json` saved). Tools executed before the crash: ['get_order', 'search_policy']. After `resume_agent('S1-crash')` the tools executed across both parts, in order, were: **get_order -> search_policy -> calculate_refund -> issue_refund** (4 executions, none repeated); final status **REFUND** with INR 128.25; model calls in total 5; ledger lines written by the demo run: 1 issue_refund line(s) in `outputs/refund_ledger_demo.jsonl`.

### D.9 ReAct versus plan-and-execute

My ReAct agent asks the model before every action: S1 needed 5 model calls (1,102 tokens), S4 4 calls (769), S5 3 calls (460), S6 2 calls (154) and the looping S7 6 calls (3,246). Every call re-sends the whole message history, including the policy passages, so tokens grow with each step. A plan-and-execute design asks once for the full step list (get_order, search_policy, calculate_refund, issue_refund) and runs it without further model calls, so a normal refund would need about 2 calls (plan plus final answer) and clearly fewer tokens; this is my estimate, not a measurement.

The difference shows on unexpected observations. In ReAct the model sees `order not found` (S6) or a cancelled order (S5) and stops after 2 or 3 calls, because the next step is chosen with the new information. A fixed plan would first run the remaining steps against a missing or cancelled order and fail or wrongly compute a refund, and only then replan, costing an extra call and risking a bad action.

For this refund workflow I would choose ReAct, with the three safety limits kept (6 iterations, token limit, timeout). The workflow is short, its refund tools change money and each step depends on the previous result (status decides whether to calculate, the amount decides between issuing and escalating), so deciding step by step is safer than saving a few thousand tokens. Plan-and-execute becomes attractive only if volumes grow and the tool sequence stays stable.

### D.10 Written answers (retrieval)

**TF and IDF.** Term frequency (TF) measures how often a word occurs inside one chunk, so words repeated in a chunk weigh more there; inverse document frequency (IDF) measures how rare a word is across all 15 chunks, so common words such as "the" or "refund" (present in many chunks) are down-weighted and distinctive words are boosted. A limitation for this task is that TF-IDF matches words, not meaning: a question phrased with different words than the policy (for example "reimbursement" for "refund") would retrieve the wrong chunk.

**Why overlap 0 breaks answers.** With 40-word chunks and no overlap, a sentence that straddles a boundary is cut in two. "How soon is money returned when a payment fails but is deducted?" lost its fact `48 hours` because the sentence "...the amount is returned automatically within 48 hours" falls across the boundary of the payment policy, and "What delivery time makes a completed order eligible for a full refund?" lost `more than 45 minutes` for the same reason in the refund policy. The 10-word overlap repeats the end of each chunk at the start of the next, so those sentences stay whole in at least one chunk (12/12 with overlap 10, 10/12 with overlap 0).

## Limitations and Next Steps

- **Retention list is illustrative, not a leakage-free evaluation.** The Premium flag comes from whole-window RFM that includes the September window which defines the lapse label, so it is a post-hoc label; the model's own features use only orders before 2025-09-01.
- **Synthetic data and a mock model.** All results (including 100% few-shot accuracy and the agent behaviour) come from deterministic generated data and a keyword-based mock LLM; real tickets and a real model would be noisier.
- **Lapse model.** About 0.65 F1 on 232 test customers is a small, noisy estimate; no probability-threshold tuning, calibration or time-based validation was done. Next step: back-test on a rolling cutoff.
- **Median imputation** of delivery time (by product category) and age (by city) hides real variation; flagging imputed values with an indicator column would be better.
- **Redaction** is regex-only (email, ten-digit phone starting 6-9, `ORD-` ids) and would miss unusual formats or names/addresses written in free text.
- **TF-IDF retrieval** matches words, not meaning, and only 5 short documents were indexed; embeddings and a larger evaluation set are the next step.
- **Refund agent.** The 7-day refund window is assumed to be satisfied; the ledger is a local file, not a payment system; `resume_agent` restarts the wall-clock timer and relies on the checkpoint, so a crash between a tool call and its checkpoint could repeat that tool (an idempotency key per refund would remove this risk).
- **Experiments in the README use only the supplied scenarios;** the demonstration ledger `outputs/refund_ledger_demo.jsonl` holds the writes of the stop-safely and crash demos so the main ledger contains exactly the seven scenario runs.
