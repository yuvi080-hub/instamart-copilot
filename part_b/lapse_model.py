"""Part B tasks 4-8: lapse cohort/label/features, leak-free preprocessing, tuning, evaluation,
class-balance experiment, interpretation, persistence, retention list.
Run: python part_b/lapse_model.py   (needs outputs/customer_segments.csv from part_b/segments.py)"""
import numpy as np, pandas as pd, joblib
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CUTOFF, END = pd.Timestamp("2025-09-01"), pd.Timestamp("2025-10-01")
o = pd.read_csv("data/clean/orders.csv", parse_dates=["order_ts"])
c = pd.read_csv("data/clean/customers.csv", parse_dates=["signup_date"])
p = pd.read_csv("data/clean/products.csv")
o = o.merge(p[["product_id", "category"]], on="product_id")

# ---- label uses September only; features use ONLY orders strictly before the cutoff
hist = o[o.order_ts < CUTOFF]
comp_h = hist[hist.status == "completed"]
fin_h = hist[hist.status.isin(["completed", "cancelled"])]
feat = comp_h.groupby("customer_id").agg(last=("order_ts", "max"), frequency=("order_id", "nunique"),
                                         monetary=("order_amount", "sum"), avg_discount=("discount_pct", "mean"),
                                         avg_delivery=("delivery_minutes", "mean")).reset_index()
feat["recency"] = (CUTOFF - feat["last"]).dt.days
cancel = fin_h.assign(canc=(fin_h.status == "cancelled")).groupby("customer_id")["canc"].mean().rename("cancel_rate")
fav = comp_h.groupby("customer_id")["category"].agg(lambda s: s.value_counts().sort_index().idxmax()).rename("fav_category")
feat = feat.merge(cancel, on="customer_id", how="left").merge(fav, on="customer_id", how="left")
feat = feat.merge(c[["customer_id", "city", "age", "gender", "signup_date"]], on="customer_id", how="left")
feat["tenure_days"] = (CUTOFF - feat["signup_date"]).dt.days
sept = o[(o.order_ts >= CUTOFF) & (o.order_ts < END) & (o.status == "completed")]["customer_id"].unique()
feat["lapsed"] = (~feat.customer_id.isin(sept)).astype(int)
NUM = ["recency", "frequency", "monetary", "avg_discount", "cancel_rate", "avg_delivery", "age", "tenure_days"]
CAT = ["city", "gender", "fav_category"]
X, y = feat[["customer_id"] + NUM + CAT], feat["lapsed"]
assert not X[NUM + CAT].isna().any().any(), "missing values in features"
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
ids_te = Xte["customer_id"].values
Xtr, Xte = Xtr.drop(columns="customer_id"), Xte.drop(columns="customer_id")
R = []   # report lines
def tbl(df):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False): L.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(L)

base = np.zeros(len(yte), dtype=int)
b_acc, b_f1 = accuracy_score(yte, base), f1_score(yte, base, zero_division=0)
cohort = {"cohort customers": len(feat), "lapsed": int(y.sum()), "lapsed %": round(100 * y.mean(), 2),
          "train rows": len(Xtr), "test rows": len(Xte), "baseline accuracy %": round(100 * b_acc, 1), "baseline lapsed F1": b_f1}
print(cohort)
R += ["### B.4 Lapse problem and baseline (cutoff 2025-09-01)\n", tbl(pd.DataFrame({"figure": cohort.keys(), "value": cohort.values()})) + "\n"]

def make(model):
    pre = ColumnTransformer([("num", StandardScaler(), NUM), ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), CAT)])
    return Pipeline([("pre", pre), ("clf", model)])
lr_gs = GridSearchCV(make(LogisticRegression(max_iter=1000)), {"clf__C": [0.01, 0.1, 1, 10, 100]}, cv=5, scoring="f1").fit(Xtr, ytr)
rf_gs = GridSearchCV(make(RandomForestClassifier(n_estimators=100, random_state=42)),
                     {"clf__max_depth": [3, 5, 8], "clf__min_samples_leaf": [5, 10, 20]}, cv=5, scoring="f1").fit(Xtr, ytr)

# ---- leakage proof: the fitted scaler only knows the training rows
sc = lr_gs.best_estimator_.named_steps["pre"].named_transformers_["num"]
mean_tr, mean_all = sc.mean_[NUM.index("frequency")], feat["frequency"].mean()
print("scaler mean frequency (train only):", round(mean_tr, 3), " cohort mean:", round(mean_all, 3))
R += ["### B.5 Leak-free preprocessing\n",
      f"Fitted-scaler mean of frequency (training rows only) = {mean_tr:.3f}; full-cohort mean of frequency = {mean_all:.3f}. "
      "They differ because the scaler has seen only the 924 training rows, so its mean is a sample estimate that excludes the 232 test rows.\n",
      "Missing values in any feature column: 0 (asserted in code).\n"]

def evalm(m):
    pr = m.predict(Xte)
    return dict(cm=confusion_matrix(yte, pr), precision=precision_score(yte, pr, zero_division=0),
                recall=recall_score(yte, pr, zero_division=0), f1=f1_score(yte, pr, zero_division=0), pred=pr)
lr_e, rf_e = evalm(lr_gs.best_estimator_), evalm(rf_gs.best_estimator_)
rows = [("LogisticRegression", str(lr_gs.best_params_), round(lr_gs.best_score_, 3), lr_e),
        ("RandomForest", str(rf_gs.best_params_), round(rf_gs.best_score_, 3), rf_e)]
R += ["### B.6 Tuning and test evaluation (positive class = lapsed)\n",
      tbl(pd.DataFrame([(n, bp, cv, round(e["precision"], 3), round(e["recall"], 3), round(e["f1"], 3), e["cm"].tolist())
                        for n, bp, cv, e in rows], columns=["model", "best params", "best CV F1", "test precision", "test recall", "test F1", "confusion [[TN,FP],[FN,TP]]"])) + "\n"]
for n, bp, cv, e in rows: print(n, bp, cv, {k: (round(v, 3) if k != "cm" and k != "pred" else v) for k, v in e.items() if k != "pred"})

# selection by cross-validated F1 (no test peeking)
sel_name = "RandomForest" if rf_gs.best_score_ >= lr_gs.best_score_ else "LogisticRegression"
sel = rf_gs.best_estimator_ if sel_name == "RandomForest" else lr_gs.best_estimator_
sel_e = rf_e if sel_name == "RandomForest" else lr_e
assert sel_e["f1"] >= 0.55
R += [f"Selected model: **{sel_name}** (higher cross-validated F1). Test F1 = {sel_e['f1']:.3f} (requirement >= 0.55).\n"]

# ---- class-balance experiment (training rows only)
tr = Xtr.assign(lapsed=ytr.values)
minority = tr[tr.lapsed == 1]; need = (tr.lapsed == 0).sum() - len(minority)
extra = minority.sample(n=need, replace=True, random_state=42)
bal = pd.concat([tr, extra]); print("balanced counts", bal.lapsed.value_counts().to_dict())
lr_bal = clone(lr_gs.best_estimator_).fit(bal[NUM + CAT], bal["lapsed"])
bal_e = evalm(lr_bal)
cmpdf = pd.DataFrame([("LR un-balanced", lr_e["precision"], lr_e["recall"], lr_e["f1"]), ("LR over-sampled", bal_e["precision"], bal_e["recall"], bal_e["f1"])],
                     columns=["model", "precision", "recall", "F1"]).round(3)
print(cmpdf)
R += ["### B.7 Class-balance experiment (over-sampling training set only)\n",
      f"Training counts after over-sampling: {bal.lapsed.value_counts().to_dict()}.\n", tbl(cmpdf) + "\n"]

# ---- interpretation
rf_pipe = rf_gs.best_estimator_; names = rf_pipe.named_steps["pre"].get_feature_names_out()
imp = pd.Series(rf_pipe.named_steps["clf"].feature_importances_, index=names).sort_values(ascending=False)
coef = pd.Series(lr_gs.best_estimator_.named_steps["clf"].coef_[0], index=names)
print(imp.head(5)); print(coef[["num__recency", "num__frequency", "num__monetary"]])
R += ["### B.8 Interpretation\n", "**Top-5 random-forest feature importances**\n",
      tbl(imp.head(5).round(3).rename_axis("feature").reset_index().rename(columns={0: "importance"})) + "\n",
      "**Logistic regression coefficients (standardised features)**\n",
      tbl(coef[["num__recency", "num__frequency", "num__monetary"]].round(3).rename_axis("feature").reset_index().rename(columns={0: "coefficient"})) + "\n"]

# ---- persistence
joblib.dump(sel, "outputs/lapse_model.joblib")
re = joblib.load("outputs/lapse_model.joblib")
same = bool((re.predict(Xte) == sel.predict(Xte)).all() and np.allclose(re.predict_proba(Xte), sel.predict_proba(Xte)))
assert same; print("reloaded model reproduces predictions:", same)
R += [f"Saved `outputs/lapse_model.joblib`; reloaded model reproduces test predictions and probabilities exactly: {same}.\n"]

# ---- retention list (illustrative: Premium flag is post-hoc whole-window)
seg = pd.read_csv("outputs/customer_segments.csv")
prem_ids = set(seg.loc[seg.is_premium, "customer_id"])
prob = sel.predict_proba(Xte)[:, 1]
te = pd.DataFrame({"customer_id": ids_te, "lapse_probability": prob.round(4), "actually_lapsed": yte.values})
ret = te[te.customer_id.isin(prem_ids)].sort_values("lapse_probability", ascending=False).head(10)
ret.to_csv("outputs/retention_list.csv", index=False)
print(ret); print("truly lapsed in list:", int(ret.actually_lapsed.sum()), "of", len(ret))
n_prem_test = int(te.customer_id.isin(prem_ids).sum())
R += ["### B.9 Retention list\n", f"Premium customers in the test set: {n_prem_test}. List written to `outputs/retention_list.csv` ({len(ret)} rows); "
      f"{int(ret.actually_lapsed.sum())} of {len(ret)} truly lapsed.\n", tbl(ret) + "\n"]
open("reports/part_b_lapse.md", "w").write("\n".join(R))
