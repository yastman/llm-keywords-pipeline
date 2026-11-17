"""Upload generated SQL content to MariaDB/MySQL.

Reads connection config from environment variables (see .env.example).
mysql-connector-python is an optional dependency — import is deferred so
the rest of the package works without it.

Usage:
    uv run python scripts/upload_to_db.py <file.sql>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def get_connection_config() -> dict:
    """Read DB credentials from environment variables."""
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "database": os.getenv("MYSQL_DATABASE", "demo_db"),
        "user": os.getenv("MYSQL_USER", "demo_user"),
        "password": os.getenv("MYSQL_PASSWORD", "demo_pass"),
    }


def connect(config: dict):
    """Return a mysql.connector connection. Raises ImportError if not installed."""
    try:
        import mysql.connector  # noqa: PLC0415 (lazy import by design)
    except ImportError as exc:
        raise ImportError(
            "mysql-connector-python is required for DB upload. "
            "Install it with: uv sync --group dev"
        ) from exc
    return mysql.connector.connect(**config)


def split_statements(sql: str) -> list[str]:
    """Split SQL on ';' outside quoted literals ('...', "...", `...`).

    Inside a literal, a backslash escapes the next char (MySQL style) and a
    doubled quote ('') closes and reopens it, so both keep the literal intact.
    """
    statements = []
    start = 0
    quote = None
    i = 0
    while i < len(sql):
        ch = sql[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch == ";":
            statements.append(sql[start:i])
            start = i + 1
        i += 1
    statements.append(sql[start:])
    return [s.strip() for s in statements if s.strip()]


def execute_sql_file(conn, sql_path: Path) -> int:
    """Execute SQL statements from a file. Returns count of executed statements."""
    sql = sql_path.read_text(encoding="utf-8")
    statements = split_statements(sql)
    cursor = conn.cursor()
    for stmt in statements:
        cursor.execute(stmt)
    conn.commit()
    cursor.close()
    return len(statements)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("Usage: python scripts/upload_to_db.py <file.sql>")
        return 1

    sql_path = Path(args[0])
    if not sql_path.exists():
        print(f"❌ File not found: {sql_path}")
        return 1

    config = get_connection_config()
    try:
        conn = connect(config)
    except ImportError as exc:
        print(f"❌ {exc}")
        return 1

    try:
        count = execute_sql_file(conn, sql_path)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"✅ Executed {count} statement(s) from {sql_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
