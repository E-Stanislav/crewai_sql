-- Базовый валидный запрос
SELECT
  id,
  email,
  created_at
FROM users
WHERE created_at >= DATE '2025-01-01'
ORDER BY created_at DESC
LIMIT 100;
