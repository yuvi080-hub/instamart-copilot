"""Assemble README.md from docs/ and reports/ fragments (all numbers come from the scripts). Run: python make_readme.py"""
def r(p): return open(p, encoding="utf-8").read().strip() + "\n"
parts = [r("docs/overview.md"),
         "## Part A\n\nData foundation: audit, clean, store, query. Cleaning scripts apply the rules in the order the brief gives; numbers of rows/values changed are in the table below.\n",
         r("reports/part_a_audit_clean.md"), r("reports/part_a_analysis.md"),
         "`python part_a/validate.py` asserts 21 reference checkpoints (raw audit counts, clean row counts, revenue INR 2,998,668.80, city/gender counts, age range) and prints `ALL CHECKPOINTS PASSED`.\n",
         "## Part B\n\nSegments and lapse prediction. Only completed orders are used for customer behaviour.\n",
         r("reports/part_b_segments.md"), r("reports/part_b_lapse.md"), r("docs/part_b_notes.md"),
         "## Part C\n\nSupport-ticket triage (tickets processed in file order; all model calls via `mock_llm.py`).\n",
         r("reports/part_c.md"), r("docs/part_c_notes.md"),
         "## Part D\n\nPolicy RAG assistant (`part_d/rag.py`) and refund agent (`part_d/agent.py`); tools `get_order`, `search_policy`, `calculate_refund`, `issue_refund`, `escalate_to_human` are listed in `TOOLS_SPEC` and dispatched through `TOOL_MAP`.\n",
         r("reports/part_d.md"), r("docs/limitations.md")]
open("README.md", "w", encoding="utf-8").write("\n".join(parts))
print("README.md written")
