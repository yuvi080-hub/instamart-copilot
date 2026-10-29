"""Part A tasks 8-9: run the 7 SQL queries and the pandas cross-check/EDA.
Run: python part_a/analysis.py"""
import re, sqlite3
import numpy as np, pandas as pd

con = sqlite3.connect("data/instamart.db")
text = open("sql/queries.sql").read()
parts = re.split(r"^-- (Q\d):.*$", text, flags=re.M)
Q = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
R = {k: pd.read_sql_query(v, con) for k, v in Q.items()}
rep = ["### A.3 SQL analysis (queries in `sql/queries.sql`)\n"]
def tbl(df):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False): L.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(L)

q1, q2, q3, q4, q5, q6, q7 = (R[f"Q{i}"] for i in range(1, 8))
top6 = q6[q6.row_num == 1][["city", "customer_id", "total_spend"]]
diff = int((q6.rnk != q6.row_num).sum())
res = [("Q1 customers with >8000 on orders >500", len(q1), "30"),
       ("Q2 rows", len(q2), "30"),
       ("Q2 sum of revenues (INR)", f"{q2.revenue.sum():,.2f}", "2,998,668.80"),
       ("Q2 largest cell", f"{q2.iloc[0].city} / {q2.iloc[0].category} INR {q2.iloc[0].revenue:,.2f}", "Bengaluru / Electronics 233,909.45"),
       ("Q3 products above average price", len(q3), "11"),
       ("Q4 customers without completed order", len(q4), "25"),
       ("Q5 customers above average", len(q5), "550"),
       ("Q5 average spend (INR)", f"{q5.avg_spend.iloc[0]:.2f}", "2,552.06"),
       ("Q6 rows where RANK != ROW_NUMBER", diff, "8"),
       ("Q7 daily rows", len(q7), "183"),
       ("Q7 last cumulative (INR)", f"{q7.cumulative_revenue.iloc[-1]:,.2f}", "2,998,668.80")]
rep.append(tbl(pd.DataFrame(res, columns=["result", "mine", "reference"])) + "\n")
rep.append("**Q6 top customer per city (ROW_NUMBER = 1)**\n\n" + tbl(top6) + "\n")
rep.append("RANK() differs from ROW_NUMBER() on %d rows because customers with identical total_spend in the same city share one RANK (the next rank is skipped) while ROW_NUMBER() always gives each row a unique consecutive number.\n" % diff)
print(tbl(pd.DataFrame(res, columns=["result", "mine", "reference"])))
print(top6.to_string(index=False))

# ---------------- pandas cross-check
o = pd.read_sql_query("SELECT * FROM orders", con); c = pd.read_sql_query("SELECT * FROM customers", con)
p = pd.read_sql_query("SELECT * FROM products", con)
comp = o[o.status == "completed"].merge(c[["customer_id", "city"]], on="customer_id").merge(p[["product_id", "category"]], on="product_id")
pv = pd.pivot_table(comp, values="order_amount", index="city", columns="category", aggfunc="sum", margins=True)
rep.append("### A.4 pandas cross-check and exploratory analysis\n")
rep.append(f"pivot_table grand total = INR {pv.loc['All','All']:,.2f}; SQL Q2 total = INR {q2.revenue.sum():,.2f}; equal: {abs(pv.loc['All','All']-q2.revenue.sum())<0.01}\n")
assert abs(pv.loc["All", "All"] - q2.revenue.sum()) < 0.01
g = comp.groupby("city").agg(total=("order_amount", "sum"), mean=("order_amount", "mean"), count=("order_amount", "count")).round(2).reset_index()
rep.append("**Per-city completed order_amount**\n\n" + tbl(g) + "\n")
print(g.to_string(index=False))

a = comp["order_amount"]
q1_, q3_ = a.quantile(.25), a.quantile(.75); iqr = q3_ - q1_
lo, hi = q1_ - 1.5 * iqr, q3_ + 1.5 * iqr
stats = {"mean": round(a.mean(), 2), "median": round(a.median(), 2), "skewness": round(a.skew(), 2), "Q1": round(q1_, 2),
         "Q2": round(a.quantile(.5), 2), "Q3": round(q3_, 2), "IQR": round(iqr, 2), "lower fence": round(lo, 2),
         "upper fence": round(hi, 2), "outliers below": int((a < lo).sum()), "outliers above": int((a > hi).sum())}
rep.append("**order_amount statistics (completed)**\n\n" + tbl(pd.DataFrame({"stat": stats.keys(), "value": stats.values()})) + "\n")
cm = comp[["order_amount", "discount_pct", "quantity", "delivery_minutes"]].corr().round(3)
rep.append("**Correlation matrix (completed orders)**\n\n" + tbl(cm.reset_index().rename(columns={"index": ""})) + "\n")
pairs = cm.where(np.triu(np.ones(cm.shape), 1).astype(bool)).stack().abs().sort_values(ascending=False)
print(stats); print(cm); print(pairs.head(3))

rep.append(open("docs/part_a_eda.md").read())
open("reports/part_a_analysis.md", "w").write("\n".join(rep))
