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
