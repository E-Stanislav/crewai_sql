from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .crew_pipeline import analyze_sql_file
from .reporting import write_file_report, write_summary
from .sql_scanner import scan_sql_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SQL Review Crew MVP")
    parser.add_argument("--sql-root", type=Path, required=True, help="Root folder with .sql files")
    parser.add_argument("--reports-dir", type=Path, default=Path("./reports"), help="Output reports folder")
    parser.add_argument("--db-url", type=str, default=None, help="PostgreSQL DSN (overrides DATABASE_URL)")
    parser.add_argument("--glob", type=str, default="**/*.sql", help="Glob for SQL files")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of files")
    parser.add_argument("--workers", type=int, default=1, help="Reserved for parallel mode")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cfg = load_config(db_url_override=args.db_url)
    sql_root: Path = args.sql_root
    reports_dir: Path = args.reports_dir

    files = scan_sql_files(root=sql_root, pattern=args.glob, limit=args.limit)
    if not files:
        print(f"SQL-файлы не найдены в: {sql_root}")
        return

    reports_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    report_paths = []
    total = len(files)

    for i, file_path in enumerate(files, start=1):
        print(f"[{i}/{total}] Reviewing: {file_path}")
        try:
            result = analyze_sql_file(file_path=file_path, cfg=cfg)
        except Exception as exc:
            from .models import FileReviewResult, ReviewIssue, ReviewMetadata

            result = FileReviewResult(
                file_path=str(file_path),
                status="ERROR",
                summary="Во время ревью файла произошла ошибка пайплайна.",
                issues=[
                    ReviewIssue(
                        kind="other",
                        severity="high",
                        message=f"Необработанная ошибка: {exc}",
                        recommendation="Проверьте подключение к БД, endpoint модели и синтаксис SQL.",
                    )
                ],
                improved_sql=None,
                metadata=ReviewMetadata(database="unknown", query_hash="n/a"),
            )

        report_path = write_file_report(reports_dir=reports_dir, result=result)
        all_results.append(result)
        report_paths.append(report_path)

    summary_path = write_summary(reports_dir=reports_dir, results=all_results, report_paths=report_paths)
    print(f"Готово. Сформировано отчётов: {len(report_paths)} + сводка: {summary_path}")


if __name__ == "__main__":
    main()
