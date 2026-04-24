-- JOIN + агрегаты
SELECT
  u.country,
  COUNT(o.id) AS orders_count,
  SUM(o.amount) AS total_amount
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE o.status = 'paid'
  AND o.created_at >= NOW() - INTERVAL '30 days'
GROUP BY u.country
HAVING COUNT(o.id) > 10
ORDER BY total_amount DESC;
