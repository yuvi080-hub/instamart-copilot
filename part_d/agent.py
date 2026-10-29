"""Part D tasks 5-8: tools, ReAct loop, safe stopping, checkpoint + resume."""
import json, math, os, sqlite3, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_llm
import rag

DB_PATH = os.path.join("data", "instamart.db")
LEDGER_PATH = os.path.join("outputs", "refund_ledger.jsonl")
STATE_DIR = "state"
LATE_MINUTES, AUTO_LIMIT_INR = 45, 1000

# ------------------------------------------------------------------ tools
def get_order(order_id):
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute("SELECT order_id, status, order_amount, delivery_minutes FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    finally:
        con.close()
    if row is None: return {"error": "order not found"}
    dm = None if row[3] is None or (isinstance(row[3], float) and math.isnan(row[3])) else row[3]
    return {"order_id": row[0], "status": row[1], "order_amount": row[2], "delivery_minutes": dm}

def search_policy(query):
    return {"results": rag.retrieve(query, 3)}

def calculate_refund(order_amount, delivery_minutes):
    """Delivered in more than 45 minutes -> 100% of order_amount, otherwise 0 (status is checked by the agent flow)."""
    late = delivery_minutes is not None and delivery_minutes > LATE_MINUTES
    return {"refund_inr": round(float(order_amount), 2) if late else 0}

def _ledger(tool, order_id, refund_inr):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "tool": tool, "order_id": order_id, "refund_inr": refund_inr}) + "\n")
    return {"refund_inr": refund_inr}
def issue_refund(order_id, refund_inr): return _ledger("issue_refund", order_id, refund_inr)
def escalate_to_human(order_id, refund_inr): return _ledger("escalate_to_human", order_id, refund_inr)

def _spec(name, desc, props, req):
    return {"name": name, "description": desc, "parameters": {"type": "object", "properties": props, "required": req}}
TOOLS_SPEC = [
    _spec("get_order", "Look up an order's status, amount and delivery time in the Instamart database.", {"order_id": {"type": "string"}}, ["order_id"]),
    _spec("search_policy", "Search the company policy documents and return the most relevant passages.", {"query": {"type": "string"}}, ["query"]),
    _spec("calculate_refund", "Compute the refund in INR: full order amount if delivered in more than 45 minutes, otherwise 0.",
          {"order_amount": {"type": "number"}, "delivery_minutes": {"type": "number"}}, ["order_amount", "delivery_minutes"]),
    _spec("issue_refund", "Issue an automatic refund of up to INR 1000 and record it in the ledger.", {"order_id": {"type": "string"}, "refund_inr": {"type": "number"}}, ["order_id", "refund_inr"]),
    _spec("escalate_to_human", "Send a refund above INR 1000 to a human support lead and record it in the ledger.", {"order_id": {"type": "string"}, "refund_inr": {"type": "number"}}, ["order_id", "refund_inr"]),
]
TOOL_MAP = {"get_order": get_order, "search_policy": search_policy, "calculate_refund": calculate_refund,
            "issue_refund": issue_refund, "escalate_to_human": escalate_to_human}

# ------------------------------------------------------------------ agent
AGENT_SYSTEM = ("You are a refund AGENT for Instamart support. Use the tools to look up the order, check the policy, "
                "calculate the refund and then issue it or escalate it. Reply with a final line starting with REFUND, ESCALATE, DENIED or NOT_FOUND.")
class SimulatedCrash(Exception):
    pass

def _save(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, f"{state['run_id']}.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, default=str)

def _finish(state, status, final):
    state.update(status=status, final_answer=final); _save(state)
    refund = 0
    for s in state["steps"]:
        if s["tool"] in ("issue_refund", "escalate_to_human"): refund = s["observation"]["refund_inr"]
    return {"status": status, "final_answer": final, "steps": state["steps"], "llm_calls": state["llm_calls"],
            "tokens_used": state["tokens_used"], "refund_inr": refund, "run_id": state["run_id"], "tools_executed": state["tools_executed"]}

def _fallback(state, status, reason):
    done = ", ".join(state["tools_executed"]) or "none"
    return _finish(state, status, f"HANDOFF TO HUMAN AGENT: {reason}. Steps completed so far: {done}. Please review order request: {state['user_message']}")

def _loop(state, max_iterations, token_limit, time_limit_seconds, crash_after_tools=None):
    t0 = time.monotonic()
    while True:
        if time.monotonic() - t0 >= time_limit_seconds:                       # (c) wall-clock limit, checked at top of iteration
            return _fallback(state, "FALLBACK_TIMEOUT", f"time limit of {time_limit_seconds}s reached")
        if state["llm_calls"] >= max_iterations:                              # (a) iteration limit
            return _fallback(state, "FALLBACK_MAX_ITERATIONS", f"no final answer after {max_iterations} model calls")
        resp = mock_llm.chat(state["messages"], TOOLS_SPEC)
        state["llm_calls"] += 1; state["tokens_used"] += resp.usage.total_tokens
        if state["tokens_used"] > token_limit:                                # (b) token limit - tool is NOT executed
            return _fallback(state, "FALLBACK_TOKEN_LIMIT", f"token limit {token_limit} exceeded ({state['tokens_used']} used)")
        msg = resp.choices[0].message
        if not msg.tool_calls:
            final = msg.content
            return _finish(state, final.split(":")[0].strip(), final)
        tc = msg.tool_calls[0]
        args = dict(tc.arguments)
        state["messages"].append({"role": "assistant", "content": None, "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": args}]})
        result = TOOL_MAP[tc.name](**args)                                    # look the name up and call with the arguments
        state["messages"].append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": json.dumps(result)})
        state["steps"].append({"tool": tc.name, "arguments": args, "observation": result})
        state["tools_executed"].append(tc.name); state["step"] += 1
        _save(state)                                                          # checkpoint after every tool observation
        if crash_after_tools is not None and len(state["tools_executed"]) == crash_after_tools:
            raise SimulatedCrash(f"simulated crash after tool #{crash_after_tools}")

def run_agent(user_message, scenario_id, max_iterations=6, token_limit=6000, time_limit_seconds=10, run_id=None, crash_after_tools=None):
    run_id = run_id or f"{scenario_id}-{int(time.time() * 1000)}"
    state = {"run_id": run_id, "scenario_id": scenario_id, "user_message": user_message, "step": 0, "llm_calls": 0, "tokens_used": 0,
             "tools_executed": [], "steps": [], "status": None, "final_answer": None,
             "limits": {"max_iterations": max_iterations, "token_limit": token_limit, "time_limit_seconds": time_limit_seconds},
             "messages": [{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": user_message}]}
    return _loop(state, max_iterations, token_limit, time_limit_seconds, crash_after_tools)

def resume_agent(run_id):
    """Load state/<run_id>.json and continue; tools already executed are in the message list and are not run again."""
    with open(os.path.join(STATE_DIR, f"{run_id}.json"), encoding="utf-8") as f:
        state = json.load(f)
    lim = state["limits"]
    return _loop(state, lim["max_iterations"], lim["token_limit"], lim["time_limit_seconds"])
