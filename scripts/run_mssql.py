#!/usr/bin/env python3
"""Run MSSQL SQL scripts using credentials from a .env file.

Usage:
  python scripts/run_mssql.py --env-file .env

This script reads MSSQL connection params from the env and executes
SQL files found in the `database/` folder in this repo. It splits
on lines that contain only `GO` (case-insensitive) so scripts written
for `sqlcmd` will run correctly.
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import pyodbc
except Exception:
    print("pyodbc is required. Install with: pip install pyodbc python-dotenv")
    raise

try:
    from dotenv import load_dotenv, find_dotenv
except Exception:
    print("python-dotenv is required. Install with: pip install python-dotenv")
    raise


def load_env(env_path: Path):
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded env from {env_path}")
    else:
        print(f"Env file {env_path} not found — relying on environment variables")


def get_mssql_connection():
    server = os.getenv("MSSQL_SERVER")
    database = os.getenv("MSSQL_DATABASE")
    user = os.getenv("MSSQL_USERNAME")
    password = os.getenv("MSSQL_PASSWORD")
    port = os.getenv("MSSQL_PORT")
    driver = os.getenv("MSSQL_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

    if not all([server, database, user, password]):
        raise RuntimeError(
            "Missing MSSQL connection env vars. Set MSSQL_SERVER, MSSQL_DATABASE, MSSQL_USERNAME, MSSQL_PASSWORD"
        )

    server_part = f"{server},{port}" if port else server
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server_part};"
        f"DATABASE={database};"
        f"UID={user};PWD={password};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    print("Connecting to MSSQL server...")
    return pyodbc.connect(conn_str)


def split_sql_batches(sql_text: str):
    # Split on lines that contain only GO (sqlcmd style)
    parts = re.split(r"^\s*GO\s*$", sql_text, flags=re.I | re.M)
    return [p.strip() for p in parts if p.strip()]


def run_sql_file(cursor, path: Path):
    print(f"Running: {path}")
    text = path.read_text(encoding="utf-8")
    batches = split_sql_batches(text)
    for i, batch in enumerate(batches, start=1):
        try:
            # Some statements (CREATE DATABASE, ALTER DATABASE, BACKUP DATABASE)
            # are not allowed inside multi-statement transactions on SQL Server.
            # Execute those batches with autocommit enabled.
            conn = cursor.connection
            needs_autocommit = bool(
                re.search(
                    r"^\s*(CREATE\s+DATABASE|ALTER\s+DATABASE|BACKUP\s+DATABASE)",
                    batch,
                    flags=re.I | re.M,
                )
            )
            prev_autocommit = getattr(conn, "autocommit", False)
            if needs_autocommit:
                conn.autocommit = True
            try:
                cursor.execute(batch)
                if not needs_autocommit:
                    conn.commit()
                print(f"  Batch {i}/{len(batches)} executed")
            finally:
                if needs_autocommit:
                    conn.autocommit = prev_autocommit
        except Exception as e:
            print(f"Error executing batch {i} in {path}: {e}")
            raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--env-file",
        default=None,
        help="Path to .env file (auto-discovered if omitted)",
    )
    ap.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    ap.add_argument(
        "--files", help="Comma-separated SQL files to run (overrides defaults)"
    )
    args = ap.parse_args()

    # Load .env: use explicit path if provided, else auto-discover with dotenv.find_dotenv()
    if args.env_file:
        env_path = Path(args.env_file)
        load_env(env_path)
    else:
        found = find_dotenv(usecwd=True)
        if found:
            load_dotenv(found)
            print(f"Auto-loaded env from {found}")
        else:
            print("No .env file found (auto). Relying on environment variables.")

    default_files = [
        Path("database/schema.sql"),
        Path("database/seed_data.sql"),
        Path("database/stored_procedures.sql"),
    ]

    if args.files:
        files = [Path(p.strip()) for p in args.files.split(",") if p.strip()]
    else:
        files = [p for p in default_files if p.exists()]

    if not files:
        print(
            "No SQL files found to run. Specify --files or place SQL scripts in the database/ folder."
        )
        sys.exit(1)

    print("The following files will be executed in order:")
    for f in files:
        print(" -", f)

    if not args.yes:
        confirm = input("Proceed? [y/N]: ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("Aborted by user.")
            sys.exit(0)

    conn = get_mssql_connection()
    try:
        cursor = conn.cursor()
        for f in files:
            run_sql_file(cursor, f)
    finally:
        conn.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
