"""Part A tasks 2-5, 7: audit raw data, clean customers + orders, store CSV + SQLite.
Run from the repository root:  python part_a/audit_clean.py"""
import os, sqlite3
import pandas as pd

RAW, CLEAN, DB = "data/raw", "data/clean", "data/instamart.db"
os.makedirs(CLEAN, exist_ok=True); os.makedirs("reports", exist_ok=True)
rep = []                                   # lines of the markdown report fragment
def md_table(df, index=True):
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)

# Only a truly empty cell is "missing"; strings such as "N/A" stay strings so we can count them as unparseable.
rd = lambda f: pd.read_csv(os.path.join(RAW, f), keep_default_na=False, na_values=[""])
customers, products, orders = rd("customers.csv"), rd("products.csv"), rd("orders.csv")

# ------------------------------------------------------------------ audit
rep.append("### A.1 Raw-data audit\n")
for name, df in [("customers.csv", customers), ("products.csv", products), ("orders.csv", orders)]:
    rep.append(f"**{name}** - shape {df.shape}\n")
    t = pd.DataFrame({"dtype": df.dtypes.astype(str), "missing": df.isna().sum(),
                      "missing_%": (df.isna().mean() * 100).round(2)})
    rep.append(md_table(t) + "\n")

amt_num = pd.to_numeric(orders["order_amount"], errors="coerce")
dm = pd.to_numeric(orders["delivery_minutes"], errors="coerce")
age = pd.to_numeric(customers["age"], errors="coerce")
audit = {
 "raw orders.csv rows": len(orders),
 "exact duplicate rows": int(orders.duplicated().sum()),
 "rows with status pending": int((orders["status"] == "pending").sum()),
 "distinct order_id": int(orders["order_id"].nunique()),
 "order_amount entries not convertible to number": int((amt_num.isna() & orders["order_amount"].notna()).sum()),
 "negative delivery_minutes": int((dm < 0).sum()),
 "blank delivery_minutes": int(orders["delivery_minutes"].isna().sum()),
 "customers: blank age": int(age.isna().sum()),
 "customers: age outside 10-100": int(((age < 10) | (age > 100)).sum()),
 "customers: distinct raw city spellings": int(customers["city"].nunique()),
 "customers: distinct non-blank raw gender spellings": int(customers["gender"].dropna().nunique()),
 "customers: blank gender": int(customers["gender"].isna().sum()),
}
rep.append("**Audit figures**\n")
rep.append(md_table(pd.DataFrame({"figure": audit.keys(), "value": audit.values()}), index=False) + "\n")
print("AUDIT"); [print(f"  {k}: {v}") for k, v in audit.items()]

# ------------------------------------------------------------------ clean customers
rep.append("### A.2 Cleaning rules and rows/values changed\n")
c = customers.copy()
n_city_changed = int((c["city"] != c["city"].str.strip().str.title()).sum())
c["city"] = c["city"].str.strip().str.title()
g = c["gender"].fillna("").str.strip().str.lower()
c["gender"] = g.map(lambda x: "male" if x in ("male", "m") else "female" if x in ("female", "f") else "unknown")
n_gender_changed = int((customers["gender"].fillna("") != c["gender"]).sum())
c["age"] = pd.to_numeric(c["age"], errors="coerce")
bad_age = (c["age"] < 10) | (c["age"] > 100)
c.loc[bad_age, "age"] = float("nan")
n_age_missing = int(c["age"].isna().sum())
c["age"] = c["age"].fillna(c.groupby("city")["age"].transform("median"))
c["signup_date"] = pd.to_datetime(c["signup_date"])
print("CUSTOMERS", c["city"].value_counts().to_dict(), c["gender"].value_counts().to_dict(),
      int(c["age"].isna().sum()), c["age"].min(), c["age"].max())

# ------------------------------------------------------------------ clean orders
o = orders.copy()
steps = []
o["order_ts"] = pd.to_datetime(o["order_ts"]); steps.append(("i. order_ts -> datetime", len(o), "all rows parsed"))
before = len(o); o = o.drop_duplicates(); steps.append(("ii. drop exact duplicate rows", before - len(o), "rows removed"))
before = len(o); o = o.sort_values(["order_id", "order_ts"]).drop_duplicates("order_id", keep="last")
steps.append(("iii. keep latest order_ts per order_id (drops earlier pending records)", before - len(o), "rows removed"))
o["order_amount"] = pd.to_numeric(o["order_amount"], errors="coerce")
n_amt = int(o["order_amount"].isna().sum())
o = o.merge(products[["product_id", "price_inr", "category"]], on="product_id", how="left")
fill = (o["price_inr"] * o["quantity"] * (1 - o["discount_pct"] / 100)).round(2)
o["order_amount"] = o["order_amount"].fillna(fill)
steps.append(("iv. unparseable order_amount -> NaN -> price x qty x (1-disc/100)", n_amt, "values filled"))
o["delivery_minutes"] = pd.to_numeric(o["delivery_minutes"], errors="coerce")
n_neg = int((o["delivery_minutes"] < 0).sum())
o.loc[o["delivery_minutes"] < 0, "delivery_minutes"] = float("nan")
comp = o["status"] == "completed"
med = o[comp].groupby("category")["delivery_minutes"].transform("median")
n_dm = int((o.loc[comp, "delivery_minutes"].isna()).sum())
o.loc[comp, "delivery_minutes"] = o.loc[comp, "delivery_minutes"].fillna(med)
steps.append(("v. negative delivery_minutes -> NaN", n_neg, "values set to missing"))
steps.append(("v. completed orders: fill missing delivery_minutes with category median (completed)", n_dm, "values filled"))
steps.append(("v. cancelled orders: delivery_minutes left missing", int((o["status"] == "cancelled").sum()), "rows left missing"))
o = o.drop(columns=["price_inr", "category"]).sort_values("order_id").reset_index(drop=True)

rule_rows = [("customers: city strip + title case", n_city_changed, "values changed"),
             ("customers: gender mapped to male/female/unknown", n_gender_changed, "values changed"),
             ("customers: ages outside 10-100 set missing (total missing incl. blanks)", n_age_missing, "values missing before fill"),
             ("customers: missing age -> median age of city", n_age_missing, "values filled"),
             ("customers: signup_date -> datetime", len(c), "all rows")] + steps
rep.append(md_table(pd.DataFrame(rule_rows, columns=["rule", "count", "meaning"]), index=False) + "\n")

comp = o["status"] == "completed"
summary = {"rows (one per order_id)": len(o), "completed": int(comp.sum()), "cancelled": int((o.status == "cancelled").sum()),
           "pending": int((o.status == "pending").sum()), "missing order_amount": int(o.order_amount.isna().sum()),
           "missing delivery_minutes (completed)": int(o.loc[comp, "delivery_minutes"].isna().sum()),
           "missing delivery_minutes (cancelled)": int(o.loc[~comp, "delivery_minutes"].isna().sum()),
           "sum order_amount completed (INR)": f"{o.loc[comp, 'order_amount'].sum():,.2f}"}
rep.append("**Clean orders summary**\n")
rep.append(md_table(pd.DataFrame({"check": summary.keys(), "value": summary.values()}), index=False) + "\n")
rep.append("**Clean customers**: cities " + ", ".join(f"{k} {v}" for k, v in c["city"].value_counts().items()) +
           "; genders " + ", ".join(f"{k} {v}" for k, v in c["gender"].value_counts().items()) +
           f"; missing ages {int(c.age.isna().sum())}; age range {c.age.min():.0f}-{c.age.max():.0f}.\n")
print("ORDERS", summary)

# ------------------------------------------------------------------ store
c_out = c.copy(); c_out["signup_date"] = c_out["signup_date"].dt.strftime("%Y-%m-%d")
o_out = o.copy(); o_out["order_ts"] = o_out["order_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
c_out.to_csv(f"{CLEAN}/customers.csv", index=False); products.to_csv(f"{CLEAN}/products.csv", index=False)
o_out.to_csv(f"{CLEAN}/orders.csv", index=False)
if os.path.exists(DB): os.remove(DB)
con = sqlite3.connect(DB)
c_out.to_sql("customers", con, index=False); products.to_sql("products", con, index=False); o_out.to_sql("orders", con, index=False)
con.close()
open("reports/part_a_audit_clean.md", "w").write("\n".join(rep))
print("stored clean CSVs and", DB)
