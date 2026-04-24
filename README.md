# SQL Review Crew (MVP)

MVP оффлайн‑системы ревью SQL на базе CrewAI.

## Что умеет

- Рекурсивно ищет `.sql` файлы в каталоге.
- Для каждого SQL запускает crew с агентами:
	- `Schema & Syntax`
	- `Plan & Optimization`
	- `Style`
	- `Report Aggregator`
- Пишет отчёты по файлам в `reports/*.sql.review.md`.
- Формирует агрегированный `reports/SUMMARY.md`.

## Стек

- Python 3.11+
- `uv`
- `crewai`
- `openai` (OpenAI‑совместимый локальный endpoint: LM Studio / Ollama / vLLM и т.д.)

## Быстрый старт

1. Установить зависимости:

```bash
uv sync
```

2. Настроить переменные окружения:

```bash
cp .env.example .env
```

3. Запуск анализа:

```bash
uv run sql-review \
	--sql-root ./sql \
	--reports-dir ./reports
```

## Использование локальной модели через OpenAI API

В `.env` укажите ваш OpenAI‑совместимый endpoint:

- `OPENAI_BASE_URL=http://localhost:1234/v1`
- `OPENAI_API_KEY=local`
- `OPENAI_MODEL=gpt-4o-mini` (или имя вашей локальной модели)

Важно: CrewAI использует LLM через OpenAI‑совместимый интерфейс.

## Опционально: подключение к PostgreSQL

Если задан `DATABASE_URL`, pipeline выполнит `EXPLAIN (FORMAT JSON)`
и снимок схемы из `information_schema`.

Пример:

```bash
export DATABASE_URL='postgresql://user:pass@localhost:5432/dbname'
```

Если БД не настроена — анализ всё равно выполняется (без DB‑проверок).

## Аргументы CLI

- `--sql-root` — корневая папка с SQL (обязательно)
- `--reports-dir` — куда писать отчёты (по умолчанию `./reports`)
- `--db-url` — DSN PostgreSQL (перекрывает `DATABASE_URL`)
- `--glob` — маска файлов (по умолчанию `**/*.sql`)
- `--limit` — ограничить число файлов
- `--workers` — задел под параллельность (в MVP пока последовательный запуск)

## Структура

- `src/sql_review_crew/main.py` — CLI entrypoint
- `src/sql_review_crew/crew_pipeline.py` — запуск crew на файл
- `src/sql_review_crew/db_tools.py` — DB‑инструменты (schema/explain)
- `src/sql_review_crew/reporting.py` — markdown отчёты + `SUMMARY.md`
- `src/sql_review_crew/sql_scanner.py` — поиск SQL файлов
