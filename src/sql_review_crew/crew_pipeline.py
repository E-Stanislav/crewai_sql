from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, Process, Task

from .config import AppConfig, build_crewai_llm
from .db_tools import DBContext, ExplainTool, SchemaSnapshotTool, read_sql_file
from .models import FileReviewResult, ReviewIssue, ReviewMetadata


def _hash_sql(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def _extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        left = text.find("{")
        right = text.rfind("}")
        if left >= 0 and right > left:
            return json.loads(text[left : right + 1])
    return {}


def _estimate_cost_from_plan(plan_payload: dict[str, Any]) -> float | None:
    if not plan_payload.get("enabled"):
        return None

    plan = plan_payload.get("plan")
    if not isinstance(plan, list) or not plan:
        return None

    root = plan[0]
    if not isinstance(root, dict):
        return None
    inner = root.get("Plan")
    if not isinstance(inner, dict):
        return None
    total_cost = inner.get("Total Cost")
    if isinstance(total_cost, (int, float)):
        return float(total_cost)
    return None


def analyze_sql_file(file_path: Path, cfg: AppConfig) -> FileReviewResult:
    sql_text = read_sql_file(file_path)
    query_hash = _hash_sql(sql_text)

    db_context = DBContext(db_url=cfg.db_url)
    schema_tool = SchemaSnapshotTool(db_context=db_context)
    explain_tool = ExplainTool(db_context=db_context)

    schema_payload = _extract_json(schema_tool.run(max_rows=300))
    explain_payload = _extract_json(explain_tool.run(sql=sql_text, analyze=False))

    llm = build_crewai_llm(cfg)

    schema_agent = Agent(
        role="Schema & Syntax Agent",
        goal="Validate SQL syntax and schema alignment.",
        backstory="You are an expert SQL reviewer focused on correctness and schema consistency.",
        llm=llm,
        tools=[schema_tool],
        verbose=False,
    )

    plan_agent = Agent(
        role="Plan & Optimization Agent",
        goal="Find execution plan bottlenecks and optimization opportunities.",
        backstory="You are a database performance engineer specialized in query plans.",
        llm=llm,
        tools=[explain_tool],
        verbose=False,
    )

    style_agent = Agent(
        role="Style Agent",
        goal="Improve readability and SQL best practices.",
        backstory="You are a SQL style guide reviewer for analytics and product queries.",
        llm=llm,
        verbose=False,
    )

    aggregator_agent = Agent(
        role="Report Aggregator Agent",
        goal="Produce final structured JSON report for one SQL file.",
        backstory="You aggregate findings into concise machine-readable review output.",
        llm=llm,
        verbose=False,
    )

    schema_task = Task(
        description=(
            "Analyze SQL for syntax/schema issues. Return short findings list.\n"
            f"FILE: {file_path}\n"
            f"SQL:\n{sql_text}\n\n"
            f"SCHEMA_SNAPSHOT_JSON:\n{json.dumps(schema_payload, ensure_ascii=False)[:15000]}"
        ),
        expected_output="Bulleted findings with severity and recommendation.",
        agent=schema_agent,
    )

    plan_task = Task(
        description=(
            "Analyze potential performance issues and rewrite hints.\n"
            f"SQL:\n{sql_text}\n\n"
            f"EXPLAIN_JSON:\n{json.dumps(explain_payload, ensure_ascii=False)[:15000]}"
        ),
        expected_output="Bulleted performance findings with concrete suggestions.",
        agent=plan_agent,
        context=[schema_task],
    )

    style_task = Task(
        description=(
            "Analyze style/readability and anti-patterns (SELECT *, nested subqueries, naming, etc).\n"
            f"SQL:\n{sql_text}"
        ),
        expected_output="Bulleted style findings with proposed cleanups.",
        agent=style_agent,
        context=[schema_task, plan_task],
    )

    output_contract = {
        "status": "OK|WARNING|ERROR",
        "summary": "short summary",
        "issues": [
            {
                "kind": "syntax|schema|performance|style|other",
                "severity": "low|medium|high",
                "message": "...",
                "recommendation": "...",
            }
        ],
        "improved_sql": "optional rewritten SQL with same semantics",
    }
    aggregator_task = Task(
        description=(
            "Aggregate all previous findings and return STRICT JSON only, without markdown.\n"
            f"JSON_SCHEMA_EXAMPLE:\n{json.dumps(output_contract, ensure_ascii=False)}\n"
            "Allowed status only: OK, WARNING, ERROR."
        ),
        expected_output="Strict JSON object only.",
        agent=aggregator_agent,
        context=[schema_task, plan_task, style_task],
    )

    crew = Crew(
        agents=[schema_agent, plan_agent, style_agent, aggregator_agent],
        tasks=[schema_task, plan_task, style_task, aggregator_task],
        process=Process.sequential,
        verbose=False,
    )

    raw_output = str(crew.kickoff())
    payload = _extract_json(raw_output)

    issues = []
    for issue in payload.get("issues", []):
        if isinstance(issue, dict):
            try:
                issues.append(ReviewIssue.model_validate(issue))
            except Exception:
                issues.append(
                    ReviewIssue(
                        kind="other",
                        severity="medium",
                        message=str(issue),
                    )
                )

    explain_ms = explain_payload.get("duration_ms") if isinstance(explain_payload, dict) else None
    if not isinstance(explain_ms, (int, float)):
        explain_ms = None

    result = FileReviewResult(
        file_path=str(file_path),
        status=payload.get("status", "WARNING"),
        summary=payload.get("summary", "No summary provided by model."),
        issues=issues,
        improved_sql=payload.get("improved_sql"),
        metadata=ReviewMetadata(
            database="postgres" if cfg.db_url else "none",
            explain_duration_ms=float(explain_ms) if explain_ms is not None else None,
            estimated_cost=_estimate_cost_from_plan(explain_payload if isinstance(explain_payload, dict) else {}),
            query_hash=query_hash,
        ),
    )

    if result.status not in {"OK", "WARNING", "ERROR"}:
        result.status = "WARNING"
    return result
