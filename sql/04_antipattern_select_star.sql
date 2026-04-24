-- Намеренный антипаттерн для проверки style/perf
SELECT *
FROM events e
LEFT JOIN users u ON u.id = e.user_id
WHERE DATE(e.event_time) = CURRENT_DATE;
