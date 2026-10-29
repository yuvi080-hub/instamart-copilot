**EDA answers (own words, under 200 words).**
*What is the data about?* 11,110 completed Instamart orders (April-September 2025) from 1,175 customers in six cities, mostly low-value grocery, dairy and snack baskets plus a few electronics.
*Distributions?* order_amount is strongly right-skewed: mean INR 269.91 sits far above the median INR 135.00, skewness is about 4.61, and the middle half of orders lies between INR 64.80 and INR 297.00.
*Outliers?* The upper fence is INR 645.30 and 897 orders exceed it; none fall below the lower fence. These are genuine high-priced electronics orders, not errors, so they were kept.
*Relationships?* All correlations are weak. The largest in absolute value is order_amount with discount_pct (about -0.095), just ahead of order_amount with quantity (+0.087); delivery time is essentially uncorrelated with everything. A correlation this small, even if consistent, does not establish causation - discounts may simply be applied to different baskets.
