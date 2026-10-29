### A.1 Raw-data audit

**customers.csv** - shape (1200, 5)

| index | dtype | missing | missing_% |
|---|---|---|---|
| customer_id | str | 0 | 0.0 |
| city | str | 0 | 0.0 |
| signup_date | str | 0 | 0.0 |
| age | float64 | 61 | 5.08 |
| gender | str | 30 | 2.5 |

**products.csv** - shape (40, 4)

| index | dtype | missing | missing_% |
|---|---|---|---|
| product_id | str | 0 | 0.0 |
| product_name | str | 0 | 0.0 |
| category | str | 0 | 0.0 |
| price_inr | int64 | 0 | 0.0 |

**orders.csv** - shape (13084, 9)

| index | dtype | missing | missing_% |
|---|---|---|---|
| order_id | str | 0 | 0.0 |
| customer_id | str | 0 | 0.0 |
| product_id | str | 0 | 0.0 |
| quantity | int64 | 0 | 0.0 |
| order_ts | str | 0 | 0.0 |
| status | str | 0 | 0.0 |
| discount_pct | int64 | 0 | 0.0 |
| order_amount | str | 0 | 0.0 |
| delivery_minutes | float64 | 2541 | 19.42 |

**Audit figures**

| figure | value |
|---|---|
| raw orders.csv rows | 13084 |
| exact duplicate rows | 119 |
| rows with status pending | 656 |
| distinct order_id | 12309 |
| order_amount entries not convertible to number | 120 |
| negative delivery_minutes | 106 |
| blank delivery_minutes | 2541 |
| customers: blank age | 61 |
| customers: age outside 10-100 | 6 |
| customers: distinct raw city spellings | 24 |
| customers: distinct non-blank raw gender spellings | 10 |
| customers: blank gender | 30 |

### A.2 Cleaning rules and rows/values changed

| rule | count | meaning |
|---|---|---|
| customers: city strip + title case | 476 | values changed |
| customers: gender mapped to male/female/unknown | 950 | values changed |
| customers: ages outside 10-100 set missing (total missing incl. blanks) | 67 | values missing before fill |
| customers: missing age -> median age of city | 67 | values filled |
| customers: signup_date -> datetime | 1200 | all rows |
| i. order_ts -> datetime | 13084 | all rows parsed |
| ii. drop exact duplicate rows | 119 | rows removed |
| iii. keep latest order_ts per order_id (drops earlier pending records) | 656 | rows removed |
| iv. unparseable order_amount -> NaN -> price x qty x (1-disc/100) | 112 | values filled |
| v. negative delivery_minutes -> NaN | 105 | values set to missing |
| v. completed orders: fill missing delivery_minutes with category median (completed) | 774 | values filled |
| v. cancelled orders: delivery_minutes left missing | 1199 | rows left missing |

**Clean orders summary**

| check | value |
|---|---|
| rows (one per order_id) | 12309 |
| completed | 11110 |
| cancelled | 1199 |
| pending | 0 |
| missing order_amount | 0 |
| missing delivery_minutes (completed) | 0 |
| missing delivery_minutes (cancelled) | 1199 |
| sum order_amount completed (INR) | 2,998,668.80 |

**Clean customers**: cities Pune 227, Delhi 210, Bengaluru 197, Chennai 191, Hyderabad 191, Mumbai 184; genders female 610, male 560, unknown 30; missing ages 0; age range 18-60.
