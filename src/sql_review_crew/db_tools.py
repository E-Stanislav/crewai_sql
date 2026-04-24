from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr


@dataclass(slots=True)
class DBContext:
    db_url: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.db_url)


class SchemaSnapshotInput(BaseModel):
    max_rows: int = Field(default=300, ge=1, le=2000)


class ExplainInput(BaseModel):
    sql: str
    analyze: bool = False


class SchemaSnapshotTool(BaseTool):
    name: str = "schema_snapshot_tool"
    description: str = "Returns information_schema snapshot for PostgreSQL as JSON string."
    args_schema: type[BaseModel] = SchemaSnapshotInput

    _db_context: DBContext = PrivateAttr()

    def __init__(self, db_context: DBContext):
        super().__init__()
        self._db_context = db_context

    def _run(self, max_rows: int = 300) -> str:
        if not self._db_context.enabled:
            return json.dumps({"enabled": False, "reason": "DATABASE_URL not configured"}, ensure_ascii=False)

        query = """
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name, ordinal_position
        LIMIT %s;
        """

        with psycopg.connect(self._db_context.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (max_rows,))
                rows = cur.fetchall()

        payload = [
            {
                "schema": r[0],
                "table": r[1],
                "column": r[2],
                "type": r[3],
            }
            for r in rows
        ]
        return json.dumps({"enabled": True, "rows": payload}, ensure_ascii=False)


class ExplainTool(BaseTool):
    name: str = "postgres_explain_tool"
    description: str = "Runs EXPLAIN (FORMAT JSON) for a SQL statement in PostgreSQL."
    args_schema: type[BaseModel] = ExplainInput

    _db_context: DBContext = PrivateAttr()

    def __init__(self, db_context: DBContext):
        super().__init__()
        self._db_context = db_context

    def _run(self, sql: str, analyze: bool = False) -> str:
        if not self._db_context.enabled:
            return json.dumps({"enabled": False, "reason": "DATABASE_URL not configured"}, ensure_ascii=False)

        explain_prefix = "EXPLAIN (FORMAT JSON"
        if analyze:
            explain_prefix += ", ANALYZE TRUE"
        explain_prefix += ") "

        start = time.perf_counter()
        with psycopg.connect(self._db_context.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(explain_prefix + sql)
                result = cur.fetchone()
        duration_ms = (time.perf_counter() - start) * 1000

        explain_json: Any = result[0]
        if isinstance(explain_json, str):
            explain_json = json.loads(explain_json)

        return json.dumps(
            {
                "enabled": True,
                "duration_ms": round(duration_ms, 2),
                "plan": explain_json,
            },
            ensure_ascii=False,
        )


def read_sql_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")
