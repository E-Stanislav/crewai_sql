from __future__ import annotations

from pathlib import Path


def scan_sql_files(root: Path, pattern: str = "**/*.sql", limit: int | None = None) -> list[Path]:
    files = sorted(path for path in root.glob(pattern) if path.is_file())
    if limit is not None:
        return files[:limit]
    return files
