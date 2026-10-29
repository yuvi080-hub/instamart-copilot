### A.3 SQL analysis (queries in `sql/queries.sql`)

| result | mine | reference |
|---|---|---|
| Q1 customers with >8000 on orders >500 | 30 | 30 |
| Q2 rows | 30 | 30 |
| Q2 sum of revenues (INR) | 2,998,668.80 | 2,998,668.80 |
| Q2 largest cell | Bengaluru / Electronics INR 233,909.45 | Bengaluru / Electronics 233,909.45 |
| Q3 products above average price | 11 | 11 |
| Q4 customers without completed order | 25 | 25 |
| Q5 customers above average | 550 | 550 |
| Q5 average spend (INR) | 2552.06 | 2,552.06 |
| Q6 rows where RANK != ROW_NUMBER | 8 | 8 |
| Q7 daily rows | 183 | 183 |
| Q7 last cumulative (INR) | 2,998,668.80 | 2,998,668.80 |

**Q6 top customer per city (ROW_NUMBER = 1)**

| city | customer_id | total_spend |
|---|---|---|
| Bengaluru | C0082 | 12856.2 |
| Chennai | C0930 | 10151.4 |
| Delhi | C0291 | 13742.6 |
| Hyderabad | C0743 | 12730.05 |
| Mumbai | C0693 | 14766.55 |
| Pune | C0426 | 10377.1 |

RANK() differs from ROW_NUMBER() on 8 rows because customers with identical total_spend in the same city share one RANK (the next rank is skipped) while ROW_NUMBER() always gives each row a unique consecutive number.

### A.4 pandas cross-check and exploratory analysis

pivot_table grand total = INR 2,998,668.80; SQL Q2 total = INR 2,998,668.80; equal: True

**Per-city completed order_amount**

| city | total | mean | count |
|---|---|---|---|
| Bengaluru | 523643.4 | 276.47 | 1894 |
| Chennai | 463629.15 | 272.72 | 1700 |
| Delhi | 502829.8 | 243.62 | 2064 |
| Hyderabad | 528589.9 | 284.95 | 1855 |
| Mumbai | 479058.5 | 297.0 | 1613 |
| Pune | 500918.05 | 252.48 | 1984 |

**order_amount statistics (completed)**

| stat | value |
|---|---|
| mean | 269.91 |
| median | 135.0 |
| skewness | 4.61 |
| Q1 | 64.8 |
| Q2 | 135.0 |
| Q3 | 297.0 |
| IQR | 232.2 |
| lower fence | -283.5 |
| upper fence | 645.3 |
| outliers below | 0.0 |
| outliers above | 897.0 |

**Correlation matrix (completed orders)**

|  | order_amount | discount_pct | quantity | delivery_minutes |
|---|---|---|---|---|
| order_amount | 1.0 | -0.095 | 0.087 | -0.003 |
| discount_pct | -0.095 | 1.0 | -0.0 | -0.01 |
| quantity | 0.087 | -0.0 | 1.0 | -0.013 |
| delivery_minutes | -0.003 | -0.01 | -0.013 | 1.0 |

**EDA answers (own words, under 200 words).**
*What is the data about?* 11,110 completed Instamart orders (April-September 2025) from 1,175 customers in six cities, mostly low-value grocery, dairy and snack baskets plus a few electronics.
*Distributions?* order_amount is strongly right-skewed: mean INR 269.91 sits far above the median INR 135.00, skewness is about 4.61, and the middle half of orders lies between INR 64.80 and INR 297.00.
*Outliers?* The upper fence is INR 645.30 and 897 orders exceed it; none fall below the lower fence. These are genuine high-priced electronics orders, not errors, so they were kept.
*Relationships?* All correlations are weak. The largest in absolute value is order_amount with discount_pct (about -0.095), just ahead of order_amount with quantity (+0.087); delivery time is essentially uncorrelated with everything. A correlation this small, even if consistent, does not establish causation - discounts may simply be applied to different baskets.
