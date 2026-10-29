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
