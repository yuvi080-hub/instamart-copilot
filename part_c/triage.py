"""Part C: support-ticket triage with guardrails, redaction, retries, validation, token budget and routing.
Run from the repo root:  python part_c/triage.py   (needs outputs/customer_segments.csv from Part B)"""
import json, os, random, re, sys, time
import pandas as pd
sys.path.insert(0, os.getcwd())
import mock_llm
from mock_llm import est_tokens, TransientLLMError

MAX_INPUT_TOKENS, BASE_DELAY, MAX_RETRIES = 400, 0.05, 3
ALLOWED = ["billing", "delivery", "technical", "fraud"]
PATTERNS = [("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
            ("PHONE", re.compile(r"\b[6-9]\d{9}\b"), "[PHONE]"),
            ("ORDER_ID", re.compile(r"ORD-\d{6}"), "[ORDER_ID]")]

ZERO_SHOT = ('You CLASSIFY customer support tickets. Allowed categories: billing, delivery, technical, fraud. '
             'Reply with JSON only, exactly {"category": "...", "reason": "..."}.')
FEW_SHOT = ('You CLASSIFY customer support tickets. Allowed categories: billing, delivery, technical, fraud. '
            'Reply with JSON only, exactly {"category": "...", "reason": "..."}.\n'
            'EXAMPLES:\n'
            'Ticket: Someone hacked my account and used my wallet, this is fraud. -> {"category": "fraud", "reason": "unauthorized account use"}\n'
            'Ticket: There is an unauthorized transaction on my card for [ORDER_ID]. -> {"category": "fraud", "reason": "unauthorized transaction"}\n'
            'Ticket: The app crashes and shows an error when I open the cart. -> {"category": "technical", "reason": "app failure"}\n'
            'Ticket: I was charged twice for [ORDER_ID]. -> {"category": "billing", "reason": "double charge"}\n'
            'Ticket: My order [ORDER_ID] is very late and the rider is not answering. -> {"category": "delivery", "reason": "late delivery"}')

def redact(text, counter=None):
    for name, rx, ph in PATTERNS:
        text, n = rx.subn(ph, text)
        if counter is not None: counter[name] += n
    return text

def call_with_retry(messages, ticket_id, log, stats):
    """Max 3 retries; wait before retry n = BASE_DELAY * 2**n * uniform(0.9, 1.15); one log line per retry."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return mock_llm.chat(messages)
        except TransientLLMError:
            stats["transient"] += 1
            if attempt == MAX_RETRIES: raise
            wait = BASE_DELAY * 2 ** attempt * random.uniform(0.9, 1.15)
            log.append(f"RETRY ticket={ticket_id} retry={attempt} wait={wait:.4f}s")
            time.sleep(wait)

def validate(content):
    """JSON with an allowed category -> classified_json; non-JSON with exactly one allowed word -> classified_keyword; else flagged."""
    try:
        obj = json.loads(content)
        if isinstance(obj, dict) and obj.get("category") in ALLOWED:
            return "classified_json", obj["category"]
        return "flagged_invalid_output", ""
    except (json.JSONDecodeError, TypeError):
        found = [w for w in re.findall(r"[a-z]+", (content or "").lower()) if w in ALLOWED]
        if len(set(found)) == 1 and len(found) == 1:
            return "classified_keyword", found[0]
        return "flagged_invalid_output", ""

def run(tickets, system_prompt, token_budget=None, prompt_log=None):
    mock_llm.reset(); random.seed(42)
    log, stats, total, results = [], {"transient": 0}, 0, []
    for t in tickets.itertuples(index=False):
        rec = dict(ticket_id=t.ticket_id, customer_id=t.customer_id, status="", category="", true_category=t.true_category, tokens_used=0)
        text = t.text
        if text.strip() == "":
            rec["status"] = "skipped_empty"
        elif est_tokens(text) > MAX_INPUT_TOKENS:
            rec["status"] = "flagged_long"
        elif token_budget is not None and total >= token_budget:
            rec["status"] = "budget_exhausted"
        else:
            msgs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": redact(text)}]
            if prompt_log is not None: prompt_log.append(msgs)
            resp = call_with_retry(msgs, t.ticket_id, log, stats)
            used = resp.usage.total_tokens; total += used; rec["tokens_used"] = used
            rec["status"], rec["category"] = validate(resp.choices[0].message.content)
        results.append(rec)
    return pd.DataFrame(results), total, log, stats

def tbl(df):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False): L.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(L)

if __name__ == "__main__":
    tickets = pd.read_csv("data/raw/tickets.csv", keep_default_na=False)
    R = ["### C.1 Input guardrails\n"]
    n_empty = int((tickets.text.str.strip() == "").sum()); long_tok = tickets.text.map(est_tokens)
    n_long = int((long_tok > MAX_INPUT_TOKENS).sum())
    R.append(f"Empty tickets (status `skipped_empty`, never sent to the model): {n_empty}. Tickets with est_tokens > {MAX_INPUT_TOKENS} "
             f"(status `flagged_long`, never sent): {n_long}, each estimated at {sorted(set(long_tok[long_tok > MAX_INPUT_TOKENS]))} tokens.\n")
    # ---- redaction counts over all 164 tickets + re-application check
    cnt = {"EMAIL": 0, "PHONE": 0, "ORDER_ID": 0}
    red = [redact(x, cnt) for x in tickets.text]
    left = sum(len(rx.findall(x)) for x in red for _, rx, _ in PATTERNS)
    assert left == 0
    R += ["### C.2 Redaction (applied in order email, phone, order id)\n",
          tbl(pd.DataFrame([(k, v) for k, v in cnt.items()] + [("TOTAL", sum(cnt.values())), ("left after re-applying patterns", left)], columns=["type", "substitutions"])) + "\n"]
    print("redactions", cnt, sum(cnt.values()), "left", left)
    R.append("### C.3 Prompts\n\nZero-shot prompt (%d est. tokens):\n\n```\n%s\n```\n\nFew-shot prompt (%d est. tokens):\n\n```\n%s\n```\n" %
             (est_tokens(ZERO_SHOT), ZERO_SHOT, est_tokens(FEW_SHOT), FEW_SHOT))
    assert "CLASSIFY" in ZERO_SHOT and "CLASSIFY" in FEW_SHOT and "EXAMPLES:" not in ZERO_SHOT and "EXAMPLES:" in FEW_SHOT

    def check_prompts(plog):   # nothing personal ever reaches the model
        for msgs in plog:
            for m in msgs:
                for _, rx, _ in PATTERNS: assert not rx.search(m["content"]), "PII leaked into a prompt"
            assert msgs[1]["content"] == redact(msgs[1]["content"])
    summaries, runs = [], {}
    for name, prompt in [("zero-shot", ZERO_SHOT), ("few-shot", FEW_SHOT)]:
        plog = []
        df, total, log, stats = run(tickets, prompt, None, plog); check_prompts(plog)
        assert len(plog) == 156 and not (set(df[df.status.isin(["skipped_empty", "flagged_long"])].ticket_id) & {m[1]["content"] for m in plog})
        cl = df[df.status.isin(["classified_json", "classified_keyword"])]
        acc = (cl.category == cl.true_category).mean()
        sc = df.status.value_counts().to_dict()
        waits = [float(re.search(r"wait=([\d.]+)s", l).group(1)) for l in log]
        retries = {int(re.search(r"retry=(\d)", l).group(1)) for l in log}
        summaries.append((name, len(cl), f"{100 * acc:.1f}% ({int((cl.category == cl.true_category).sum())} of {len(cl)})", total, round(total / len(cl), 1),
                          sc.get("classified_json", 0), sc.get("classified_keyword", 0), sc.get("flagged_invalid_output", 0), stats["transient"], len(log)))
        runs[name] = (df, log, waits, retries)
        print(name, summaries[-1], "waits", min(waits), max(waits), "retry numbers", retries)
        if name == "zero-shot":
            cm = pd.crosstab(cl.true_category, cl.category).reindex(index=ALLOWED, columns=ALLOWED, fill_value=0)
            cm_md = tbl(cm.reset_index().rename(columns={"true_category": "true \\ predicted"}))
            print(cm)
    log_df = runs["few-shot"][1]
    os.makedirs("reports", exist_ok=True); open("reports/part_c_retry_log_few_shot.txt", "w").write("\n".join(log_df) + "\n")
    w = runs["zero-shot"][2]
    R += ["### C.4 Resilient calls\n",
          f"Retry log (zero-shot run): {len(runs['zero-shot'][1])} retry lines, one per TransientLLMError; every retry was retry number {sorted(runs['zero-shot'][3])} "
          f"with waits between {min(w):.4f}s and {max(w):.4f}s (allowed 0.045-0.0575s). Few-shot run log: `reports/part_c_retry_log_few_shot.txt`. "
          "All transient errors were recovered by the first retry; no ticket ended with a permanent error.\n\nExample log lines:\n\n```\n" + "\n".join(runs['zero-shot'][1][:3]) + "\n```\n",
          "### C.5-C.6 Validation and prompt comparison (156 eligible tickets per run)\n",
          tbl(pd.DataFrame(summaries, columns=["prompt", "classified", "accuracy", "total tokens", "tokens / classified ticket", "classified_json", "classified_keyword", "flagged_invalid_output", "transient errors", "retry lines"])) + "\n",
          "Zero-shot confusion table (rows = true category, columns = predicted):\n\n" + cm_md + "\n"]
    # ---- budget demo
    BUDGET = 6000
    dfb, totb, logb, _ = run(tickets, ZERO_SHOT, BUDGET)
    n_ex = int((dfb.status == "budget_exhausted").sum())
    assert n_ex >= 1
    os.makedirs("outputs", exist_ok=True)
    dfb[["ticket_id", "customer_id", "status", "category", "tokens_used"]].to_csv("outputs/triage_budget_demo.csv", index=False)
    print("budget demo", BUDGET, "exhausted", n_ex, "tokens", totb)
    # ---- final run + routing
    seg = pd.read_csv("outputs/customer_segments.csv").set_index("customer_id")
    dff, totf, _, _ = run(tickets, FEW_SHOT, 100000)
    def route(r):
        if r.status in ("skipped_empty", "flagged_long", "flagged_invalid_output", "budget_exhausted"): return "human_review", "NORMAL"
        if r.category == "fraud": return "security_team", "HIGH"
        prem = bool(seg.is_premium.get(r.customer_id, False))
        return ("premium_desk", "HIGH") if prem else ("support_queue", "NORMAL")
    dff["segment_name"] = dff.customer_id.map(seg.segment_name).fillna("")
    dff[["route", "priority"]] = [route(r) for r in dff.itertuples()]
    dff.loc[~dff.status.isin(["classified_json", "classified_keyword"]), "category"] = ""
    out = dff[["ticket_id", "customer_id", "status", "category", "segment_name", "priority", "route", "tokens_used"]]
    out.to_csv("outputs/triage_results.csv", index=False)
    assert len(out) == 164
    R += ["### C.7 Token budget, routing and output\n",
          f"Budget demo: zero-shot prompt ({est_tokens(ZERO_SHOT)} est. tokens) with TOKEN_BUDGET = {BUDGET}: **{n_ex} tickets ended `budget_exhausted`** "
          f"(token total {totb}); saved to `outputs/triage_budget_demo.csv`.\n",
          "Final `outputs/triage_results.csv` (few-shot, TOKEN_BUDGET = 100000, 164 rows):\n\nStatus counts:\n\n" + tbl(out.status.value_counts().rename_axis("status").reset_index(name="tickets")) + "\n\nRoute counts:\n\n" +
          tbl(out.groupby(["route", "priority"]).size().reset_index(name="tickets")) + "\n"]
    open("reports/part_c.md", "w").write("\n".join(R))
    print(out.status.value_counts().to_dict(), out.route.value_counts().to_dict())
