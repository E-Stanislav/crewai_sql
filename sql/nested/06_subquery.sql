-- Вложенный запрос
SELECT
  p.id,
  p.name
FROM products p
WHERE p.id IN (
  SELECT oi.product_id
  FROM order_items oi
  GROUP BY oi.product_id
  HAVING SUM(oi.quantity) > 100
)
ORDER BY p.id;
