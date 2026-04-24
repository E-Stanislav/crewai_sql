WITH 
-- CTE1: все категории без фильтра (материализуется целиком)
all_categories AS (
    SELECT *, (SELECT COUNT(*) FROM categories c2) AS total_cats
    FROM categories
),

-- CTE2: все поставщики с подзапросом (дублирует данные)
all_suppliers AS (
    SELECT s.*, 
           (SELECT AVG(p.price) FROM products p WHERE p.supplier_id = s.id) AS avg_price_subquery
    FROM suppliers s
),

-- CTE3: все продукты с кросс‑джойном (картезианское произведение!)
all_products_expanded AS (
    SELECT p.*, c.name AS cat_name, s.name AS sup_name,
           p.price * 1.1 AS price_with_tax
    FROM products p
    CROSS JOIN all_categories c  -- неоптимально!
    CROSS JOIN all_suppliers s
    WHERE p.category_id = c.id AND p.supplier_id = s.id
),

-- CTE4: все пользователи с повторным подзапросом
all_users_detailed AS (
    SELECT u.*, 
           (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count_sub
    FROM users u
),

-- CTE5: все заказы с джойнами к предыдущим (многоуровневые)
all_orders_full AS (
    SELECT o.*, 
           u.login AS user_login,
           p.name AS product_name,
           ape.cat_name,
           ape.price_with_tax AS current_price
    FROM orders o
    JOIN all_users_detailed u ON o.user_id = u.id
    JOIN all_products_expanded ape ON o.product_id = ape.id  -- большой CTE!
),

-- Рекурсивный CTE6: иерархия категорий (хоть её нет, симулируем глубину)
recursive_categories AS (
    SELECT id, name, 0 AS level
    FROM all_categories
    UNION ALL
    SELECT ac.id, ac.name, rc.level + 1
    FROM recursive_categories rc
    CROSS JOIN all_categories ac  -- бесконечный рост без лимита!
    WHERE rc.level < 10  -- искусственный стоп
),

-- CTE7: агрегация заказов по пользователям (без GROUP BY оптимизации)
user_orders_agg AS (
    SELECT user_id, 
           SUM(quantity) AS total_qty,
           AVG(total_price) AS avg_order,
           COUNT(*) * 1000 AS weird_metric  -- бессмысленный расчёт
    FROM all_orders_full
    GROUP BY user_id
),

-- CTE8: ещё один джойн всего ко всему (пирамида CTE)
final_analytics AS (
    SELECT u.login,
           uoa.total_qty,
           SUM(aof.total_price) OVER (PARTITION BY u.id) AS window_total,
           rc.name AS rec_cat_name,
           COUNT(*) AS row_count
    FROM all_users_detailed u
    JOIN user_orders_agg uoa ON u.id = uoa.user_id
    JOIN all_orders_full aof ON u.id = aof.user_id
    CROSS JOIN recursive_categories rc  -- снова кросс!
    WHERE u.status = 'active'
)

-- Финальный SELECT: топ по неоптимальной метрике
SELECT 
    login,
    total_qty,
    window_total,
    rec_cat_name,
    row_count,
    RANK() OVER (ORDER BY weird_metric DESC) AS bad_rank
FROM final_analytics
ORDER BY bad_rank;