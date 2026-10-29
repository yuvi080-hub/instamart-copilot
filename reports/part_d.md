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
