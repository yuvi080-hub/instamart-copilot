## Limitations and Next Steps

- **Retention list is illustrative, not a leakage-free evaluation.** The Premium flag comes from whole-window RFM that includes the September window which defines the lapse label, so it is a post-hoc label; the model's own features use only orders before 2025-09-01.
- **Synthetic data and a mock model.** All results (including 100% few-shot accuracy and the agent behaviour) come from deterministic generated data and a keyword-based mock LLM; real tickets and a real model would be noisier.
- **Lapse model.** About 0.65 F1 on 232 test customers is a small, noisy estimate; no probability-threshold tuning, calibration or time-based validation was done. Next step: back-test on a rolling cutoff.
- **Median imputation** of delivery time (by product category) and age (by city) hides real variation; flagging imputed values with an indicator column would be better.
- **Redaction** is regex-only (email, ten-digit phone starting 6-9, `ORD-` ids) and would miss unusual formats or names/addresses written in free text.
- **TF-IDF retrieval** matches words, not meaning, and only 5 short documents were indexed; embeddings and a larger evaluation set are the next step.
- **Refund agent.** The 7-day refund window is assumed to be satisfied; the ledger is a local file, not a payment system; `resume_agent` restarts the wall-clock timer and relies on the checkpoint, so a crash between a tool call and its checkpoint could repeat that tool (an idempotency key per refund would remove this risk).
- **Experiments in the README use only the supplied scenarios;** the demonstration ledger `outputs/refund_ledger_demo.jsonl` holds the writes of the stop-safely and crash demos so the main ledger contains exactly the seven scenario runs.
