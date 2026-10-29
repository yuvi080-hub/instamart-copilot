"""Part B tasks 1-3: RFM table, K-means (K=2..8), segment profile, PCA, outputs/customer_segments.csv.
Run: python part_b/segments.py"""
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

SNAP = pd.Timestamp("2025-10-01 00:00:00")
o = pd.read_csv("data/clean/orders.csv", parse_dates=["order_ts"])
comp = o[o.status == "completed"]
rfm = comp.groupby("customer_id").agg(last=("order_ts", "max"), frequency=("order_id", "nunique"),
                                      monetary=("order_amount", "sum")).reset_index()
rfm["recency"] = (SNAP - rfm["last"]).dt.days
rfm = rfm[["customer_id", "recency", "frequency", "monetary"]]
rfm["monetary"] = rfm["monetary"].round(2)
info = {"customers": len(rfm), "recency median": rfm.recency.median(), "recency min": rfm.recency.min(),
        "recency max": rfm.recency.max(), "frequency mean": round(rfm.frequency.mean(), 2), "frequency max": rfm.frequency.max(),
        "monetary mean": round(rfm.monetary.mean(), 2), "monetary max": rfm.monetary.max()}
print(info)

X = StandardScaler().fit_transform(rfm[["recency", "frequency", "monetary"]])
rows = []
for k in range(2, 9):
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    rows.append((k, round(km.inertia_, 1), round(silhouette_score(X, km.labels_), 3)))
ktab = pd.DataFrame(rows, columns=["K", "inertia", "silhouette"])
print(ktab.to_string(index=False))

K = 4
km = KMeans(n_clusters=K, n_init=10, random_state=42).fit(X)
rfm["segment_id"] = km.labels_
prof = rfm.groupby("segment_id").agg(size=("customer_id", "count"), mean_recency=("recency", "mean"),
                                    mean_frequency=("frequency", "mean"), mean_monetary=("monetary", "mean")).round(2)
print(prof)
pca = PCA(n_components=2).fit(X)
evr = pca.explained_variance_ratio_
print("PCA", evr, evr.sum())

# ---- naming: rule-based on the profile, so the labels follow whatever cluster ids K-means assigns
prem = prof.mean_monetary.idxmax()
lapsing = prof.mean_recency.idxmax()
loyal = prof.drop([prem, lapsing]).mean_frequency.idxmax()
names, actions = {}, {}
for sid in prof.index:
    if sid == prem:
        names[sid], actions[sid] = "Premium Big-Basket Buyers", "Dedicated concierge offers and early access to electronics deals; protect with proactive retention."
    elif sid == lapsing:
        names[sid], actions[sid] = "Lapsing Low-Activity", "Win-back push with a time-limited coupon; cheap channel (push/SMS) only."
    elif sid == loyal:
        names[sid], actions[sid] = "Loyal Frequent Shoppers", "Loyalty points and subscription (daily-essentials) bundles; do not over-discount."
    else:
        names[sid], actions[sid] = "Occasional Basket Buyers", "Nudge towards a second weekly order with free-delivery thresholds."
rfm["segment_name"] = rfm.segment_id.map(names)
rfm["is_premium"] = rfm.segment_id == prem
import os; os.makedirs("outputs", exist_ok=True)
rfm[["customer_id", "recency", "frequency", "monetary", "segment_id", "segment_name", "is_premium"]].to_csv("outputs/customer_segments.csv", index=False)

def tbl(df):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False): L.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(L)
pt = prof.reset_index(); pt["name"] = pt.segment_id.map(names); pt["premium"] = pt.segment_id == prem; pt["action"] = pt.segment_id.map(actions)
rep = ["### B.1 RFM table (snapshot 2025-10-01 00:00:00)\n", tbl(pd.DataFrame({"figure": info.keys(), "value": [str(v) for v in info.values()]})) + "\n",
       "### B.2 K-means (StandardScaler, n_init=10, random_state=42)\n", tbl(ktab) + "\n",
       "### B.3 Segment profile for K=4\n", tbl(pt) + "\n",
       f"PCA(n_components=2) explained_variance_ratio_: {evr[0]:.3f} and {evr[1]:.3f}, total {evr.sum():.3f}.\n"]
open("reports/part_b_segments.md", "w").write("\n".join(rep))
print(pt.to_string())
