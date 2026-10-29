### B.1 RFM table (snapshot 2025-10-01 00:00:00)

| figure | value |
|---|---|
| customers | 1175 |
| recency median | 19.0 |
| recency min | 0 |
| recency max | 180 |
| frequency mean | 9.46 |
| frequency max | 33 |
| monetary mean | 2552.06 |
| monetary max | 14766.55 |

### B.2 K-means (StandardScaler, n_init=10, random_state=42)

| K | inertia | silhouette |
|---|---|---|
| 2 | 1820.8 | 0.465 |
| 3 | 1268.2 | 0.445 |
| 4 | 743.1 | 0.526 |
| 5 | 617.4 | 0.48 |
| 6 | 503.2 | 0.482 |
| 7 | 408.5 | 0.416 |
| 8 | 366.5 | 0.412 |

### B.3 Segment profile for K=4

| segment_id | size | mean_recency | mean_frequency | mean_monetary | name | premium | action |
|---|---|---|---|---|---|---|---|
| 0 | 436 | 28.86 | 3.77 | 1057.62 | Occasional Basket Buyers | False | Nudge towards a second weekly order with free-delivery thresholds. |
| 1 | 138 | 24.12 | 6.77 | 7129.7 | Premium Big-Basket Buyers | True | Dedicated concierge offers and early access to electronics deals; protect with proactive retention. |
| 2 | 419 | 8.77 | 19.4 | 3410.02 | Loyal Frequent Shoppers | False | Loyalty points and subscription (daily-essentials) bundles; do not over-discount. |
| 3 | 182 | 109.04 | 2.2 | 685.99 | Lapsing Low-Activity | False | Win-back push with a time-limited coupon; cheap channel (push/SMS) only. |

PCA(n_components=2) explained_variance_ratio_: 0.634 and 0.218, total 0.852.
