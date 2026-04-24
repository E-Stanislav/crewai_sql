-- Намеренная синтаксическая ошибка для теста ERROR
SELECT
  id,
  email,
FROM users
WHERE created_at > NOW() - INTERVAL '7 days';
