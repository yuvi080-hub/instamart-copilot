"""Part A task 7: assert the reference checkpoints. Run: python part_a/validate.py"""
import sqlite3
import pandas as pd

raw = pd.read_csv("data/raw/orders.csv", keep_default_na=False, na_values=[""])
rc = pd.read_csv("data/raw/customers.csv", keep_default_na=False, na_values=[""])
con = sqlite3.connect("data/instamart.db")
o = pd.read_sql_query("SELECT * FROM orders", con)
c = pd.read_sql_query("SELECT * FROM customers", con)
tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
comp = o[o.status == "completed"]
checks = [
 ("db tables", tables >= {"customers", "products", "orders"}),
 ("raw order rows 13084", len(raw) == 13084),
 ("exact duplicates 119", raw.duplicated().sum() == 119),
 ("pending rows 656", (raw.status == "pending").sum() == 656),
 ("distinct order_id 12309", raw.order_id.nunique() == 12309),
 ("negative delivery 106", (pd.to_numeric(raw.delivery_minutes) < 0).sum() == 106),
 ("blank delivery 2541", raw.delivery_minutes.isna().sum() == 2541),
 ("blank ages 61", rc.age.isna().sum() == 61),
 ("raw city spellings 24", rc.city.nunique() == 24),
 ("raw gender spellings 10", rc.gender.dropna().nunique() == 10),
 ("clean orders 12309", len(o) == 12309),
 ("11110 completed / 1199 cancelled", (len(comp), (o.status == "cancelled").sum()) == (11110, 1199)),
 ("no pending", (o.status == "pending").sum() == 0),
 ("0 missing amount", o.order_amount.isna().sum() == 0),
 ("0 missing delivery (completed)", comp.delivery_minutes.isna().sum() == 0),
 ("1199 missing delivery (cancelled)", o[o.status == "cancelled"].delivery_minutes.isna().sum() == 1199),
 ("completed revenue 2,998,668.80", round(comp.order_amount.sum(), 2) == 2998668.80),
 ("six cities", c.city.nunique() == 6),
 ("city counts", c.city.value_counts().to_dict() == {"Pune": 227, "Delhi": 210, "Bengaluru": 197, "Chennai": 191, "Hyderabad": 191, "Mumbai": 184}),
 ("gender counts", c.gender.value_counts().to_dict() == {"female": 610, "male": 560, "unknown": 30}),
 ("ages 18-60, none missing", c.age.notna().all() and c.age.between(18, 60).all()),
]
bad = [n for n, ok in checks if not ok]
for n, ok in checks: print(("PASS " if ok else "FAIL "), n)
assert not bad, f"failed: {bad}"
print("ALL CHECKPOINTS PASSED")
