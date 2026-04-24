from __future__ import annotations

from collections import Counter
from pathlib import Path

from .models import FileReviewResult, SummaryStats


def write_file_report(reports_dir: Path, result: FileReviewResult) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    src_name = Path(result.file_path).name
    out = reports_dir / f"{src_name}.review.md"

    issues_block = "\n".join(
        f"- [{i.severity}] **{i.kind}**: {i.message}"
        + (f" → {i.recommendation}" if i.recommendation else "")
        for i in result.issues
    )
    if not issues_block:
        issues_block = "- Проблем не найдено"

    improved_block = result.improved_sql.strip() if result.improved_sql else "(не требуется)"

    md = f"""# SQL Review: {src_name}

**Status:** `{result.status}`

## Summary

{result.summary}

## Issues

{issues_block}

## Improved SQL

```sql
{improved_block}
```

## Metadata

- Database: `{result.metadata.database}`
- Explain duration (ms): `{result.metadata.explain_duration_ms}`
- Estimated cost: `{result.metadata.estimated_cost}`
- Query hash: `{result.metadata.query_hash}`
"""
    out.write_text(md, encoding="utf-8")
    return out


def build_summary_stats(results: list[FileReviewResult]) -> SummaryStats:
    stats = SummaryStats(total_files=len(results))

    for r in results:
        if r.status == "OK":
            stats.ok += 1
        elif r.status == "WARNING":
            stats.warning += 1
        else:
            stats.error += 1

    issue_counter = Counter()
    for r in results:
        for issue in r.issues:
            issue_counter[issue.kind] += 1
    stats.issues_by_kind = dict(sorted(issue_counter.items(), key=lambda x: x[0]))

    heavy = []
    for r in results:
        if r.metadata.estimated_cost is not None:
            heavy.append((r.file_path, float(r.metadata.estimated_cost)))
    heavy.sort(key=lambda x: x[1], reverse=True)
    stats.top_heavy_queries = heavy[:10]
    return stats


def write_summary(reports_dir: Path, results: list[FileReviewResult], report_paths: list[Path]) -> Path:
    stats = build_summary_stats(results)
    out = reports_dir / "SUMMARY.md"

    links = []
    for src, rpt in zip(results, report_paths, strict=False):
        links.append(f"- [{Path(src.file_path).name}]({rpt.name}) — `{src.status}`")

    heavy_block = "\n".join(f"- `{Path(p).name}`: cost `{c}`" for p, c in stats.top_heavy_queries)
    if not heavy_block:
        heavy_block = "- Нет данных о стоимости (вероятно, DB mode выключен)."

    by_kind = "\n".join(f"- `{k}`: {v}" for k, v in stats.issues_by_kind.items())
    if not by_kind:
        by_kind = "- Проблемы не обнаружены"

    md = f"""# SQL Review Summary

- Total files: **{stats.total_files}**
- OK: **{stats.ok}**
- WARNING: **{stats.warning}**
- ERROR: **{stats.error}**

## Top heavy queries

{heavy_block}

## Issues by kind

{by_kind}

## Reports

{chr(10).join(links) if links else '- Нет обработанных файлов'}
"""
    out.write_text(md, encoding="utf-8")
    return out
