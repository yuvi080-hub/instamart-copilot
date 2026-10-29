"""Part D driver: RAG evaluation, 7 agent scenarios, stop-safely demos, crash-and-resume demo. Run: python part_d/run_part_d.py"""
import json, os, shutil, sys
import pandas as pd
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rag, agent
from collections import Counter

def tbl(df):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False): L.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(L)

R = ["### D.1 Chunking\n"]
idx10 = rag.Index(40, 10)
cc = Counter(c["source"] for c in idx10.chunks)
R.append(f"40-word chunks with 10-word overlap: **{len(idx10.chunks)} chunks** - " + ", ".join(f"{k.replace('_policy.txt','')} {v}" for k, v in sorted(cc.items())) + ".\n")
top = [h["source"] for h in rag.retrieve("refund policy late delivery")]
R.append(f"### D.2 Retrieval\n\nQuery `refund policy late delivery` -> top-3 sources: {top}.\n")
R.append("### D.3-D.4 Grounded answers and evaluation\n")
res10, f10 = rag.evaluate(idx10)
res0, f0 = rag.evaluate(rag.Index(40, 0))
R.append(tbl(pd.DataFrame([("overlap 10", res10["n_chunks"], res10["doc"], res10["fact"], res10["fallback"]),
                           ("overlap 0", res0["n_chunks"], res0["doc"], res0["fact"], res0["fallback"])],
                          columns=["setting", "chunks", "expected_doc in top 3 (12 answerable)", "answer contains expected_fact (12)", "fallback on unanswerable (2)"])) + "\n")
R.append("Questions that break with overlap 0:\n")
for q, why, ans in f0: R.append(f"- *{q}* - {why}; answer was: \"{ans.replace(chr(10), ' ')}\"")
print(res10, res0)

# ---- clean outputs, run the seven scenarios
for p in ("outputs/agent_runs.jsonl", "outputs/refund_ledger.jsonl", "outputs/refund_ledger_demo.jsonl"):
    if os.path.exists(p): os.remove(p)
shutil.rmtree("state", ignore_errors=True); os.makedirs("state")
sc = pd.read_csv("data/raw/agent_scenarios.csv")
rows = []
with open("outputs/agent_runs.jsonl", "a", encoding="utf-8") as f:
    for r in sc.itertuples(index=False):
        out = agent.run_agent(r.message, r.scenario_id, run_id=f"{r.scenario_id}-main")
        f.write(json.dumps({"scenario_id": r.scenario_id, "status": out["status"], "final_answer": out["final_answer"], "llm_calls": out["llm_calls"],
                            "tokens_used": out["tokens_used"], "steps": [{"tool": s["tool"], "arguments": s["arguments"], "observation": s["observation"]} for s in out["steps"]]}) + "\n")
        exp = r.expected_outcome
        ok = (out["status"].startswith("FALLBACK") if exp == "FALLBACK" else out["status"] == exp) and abs(out["refund_inr"] - r.expected_refund_inr) <= 0.01
        rows.append((r.scenario_id, out["status"], f"{out['refund_inr']:.2f}", f"{r.expected_refund_inr:.2f}", out["llm_calls"], out["tokens_used"], "yes" if ok else "NO"))
        assert ok, (r.scenario_id, out)
R.append("\n### D.5-D.6 Seven scenario results (default limits: 6 iterations, 6000 tokens, 10 s)\n")
R.append(tbl(pd.DataFrame(rows, columns=["scenario", "status", "refund INR", "expected INR", "model calls", "tokens used", "matches expected"])) + "\n")
print(pd.DataFrame(rows))

# ---- stop-safely demos (separate ledger so the main ledger holds only the seven scenario runs)
agent.LEDGER_PATH = "outputs/refund_ledger_demo.jsonl"
s1 = sc[sc.scenario_id == "S1"].iloc[0].message
d1 = agent.run_agent(s1, "S1", token_limit=200, run_id="S1-token200")
d2 = agent.run_agent(s1, "S1", time_limit_seconds=0, run_id="S1-timeout0")
assert d1["status"] == "FALLBACK_TOKEN_LIMIT" and d2["status"] == "FALLBACK_TIMEOUT"
R.append("### D.7 Stop-safely demonstrations\n")
R.append(tbl(pd.DataFrame([("S7 default limits", "FALLBACK_MAX_ITERATIONS", "6 model calls, " + str([r for r in rows if r[0] == 'S7'][0][5]) + " tokens (limit 6000 not hit)"),
                           ("S1 with token_limit=200", d1["status"], f"{d1['llm_calls']} model calls, {d1['tokens_used']} tokens; tools executed before stop: {d1['tools_executed']} (the tool requested by the call that crossed the limit was not executed)"),
                           ("S1 with time_limit_seconds=0", d2["status"], f"{d2['llm_calls']} model calls, stops before the first model call")], columns=["run", "status", "detail"])) + "\n")
R.append(f"Example hand-off summary (token-limit demo): `{d1['final_answer']}`\n")
print(d1["status"], d1["tools_executed"], d2["status"])

# ---- crash and resume
try:
    agent.run_agent(s1, "S1", run_id="S1-crash", crash_after_tools=2)
    raise AssertionError("expected a crash")
except agent.SimulatedCrash as e:
    ck = json.load(open("state/S1-crash.json"))
    before = list(ck["tools_executed"]); print("crashed:", e, before)
res = agent.resume_agent("S1-crash")
tools = res["tools_executed"]
assert tools == ["get_order", "search_policy", "calculate_refund", "issue_refund"] and res["status"] == "REFUND" and abs(res["refund_inr"] - 128.25) < 0.01
ledger_demo = open("outputs/refund_ledger_demo.jsonl").read().strip().splitlines()
R.append("### D.8 Crash and resume (S1)\n")
R.append(f"A simulated crash was raised right after the second tool execution (checkpoint `state/S1-crash.json` saved). Tools executed before the crash: {before}. "
         f"After `resume_agent('S1-crash')` the tools executed across both parts, in order, were: **{' -> '.join(tools)}** (4 executions, none repeated); "
         f"final status **{res['status']}** with INR {res['refund_inr']:.2f}; model calls in total {res['llm_calls']}; ledger lines written by the demo run: "
         f"{sum('issue_refund' in l for l in ledger_demo)} issue_refund line(s) in `outputs/refund_ledger_demo.jsonl`.\n")
R.append(open("docs/part_d_react_vs_plan.md").read())
R.append(open("docs/part_d_rag_notes.md").read())
open("reports/part_d.md", "w").write("\n".join(R))
print(res["status"], res["refund_inr"], tools)
