-- CTE + window function
WITH ranked_orders AS (
  SELECT
    o.user_id,
    o.id AS order_id,
    o.amount,
    o.created_at,
    ROW_NUMBER() OVER (
      PARTITION BY o.user_id
      ORDER BY o.created_at DESC
    ) AS rn
  FROM orders o
)
SELECT
  user_id,
  order_id,
  amount,
  created_at
FROM ranked_orders
WHERE rn = 1
ORDER BY created_at DESC;
