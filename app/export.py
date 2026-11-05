"""Write the survey database out as the CSVs the analysis pipeline reads.

    python app/export.py                          # app/data/survey.sqlite3 -> exports/
    python app/export.py --db PATH --out DIR
    python app/export.py --database-url "$DATABASE_URL" --out DIR

Pilot responses go to separate *_pilot.csv files and never mix with the main data.
"""
import argparse
import csv
import io
import json
import sqlite3
from pathlib import Path

try:  # Vercel imports app.export; direct local execution imports export.
    from .schema import CHOICE_COLUMNS, PARTICIPANT_COLUMNS
except ImportError:
    from schema import CHOICE_COLUMNS, PARTICIPANT_COLUMNS

HERE = Path(__file__).resolve().parent


def csv_texts(conn):
    """{filename: csv text} for the main and pilot participants and choices."""
    placeholder = "%s" if conn.__class__.__module__.startswith("psycopg") else "?"
    out = {}
    for pilot, suffix in ((0, ""), (1, "_pilot")):
        people = []
        for pid, code, block, answers, submitted_at in conn.execute(
                "SELECT pid, code, block, answers, submitted_at FROM participants "
                f"WHERE pilot = {placeholder} ORDER BY pid", (pilot,)):
            row = json.loads(answers)
            row.update(pid=pid, code=code, pilot=pilot, block=block, submitted_at=submitted_at)
            people.append(row)
        choices = conn.execute(
            f"SELECT {', '.join('c.' + c for c in CHOICE_COLUMNS)} FROM choices c "
            f"JOIN participants p ON p.pid = c.pid WHERE p.pilot = {placeholder} "
            "ORDER BY c.pid, c.set_id, c.alt_id", (pilot,)).fetchall()
        out[f"participants{suffix}.csv"] = _to_csv(PARTICIPANT_COLUMNS,
                                                   [[p.get(c, "") for c in PARTICIPANT_COLUMNS] for p in people])
        out[f"choices_long{suffix}.csv"] = _to_csv(CHOICE_COLUMNS, choices)
    return out


def _to_csv(columns, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows(["" if v is None else v for v in row] for row in rows)
    return buf.getvalue()


def write_exports(db_path, out_dir, database_url=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if database_url:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Postgres exports require psycopg; install requirements.txt") from exc
        conn = psycopg.connect(database_url)
    else:
        conn = sqlite3.connect(db_path)
    try:
        texts = csv_texts(conn)
    finally:
        conn.close()
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8")
    return {name: text.count("\n") - 1 for name, text in texts.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=HERE / "data" / "survey.sqlite3")
    ap.add_argument("--database-url", help="Neon/Postgres connection string (or pass DATABASE_URL explicitly)")
    ap.add_argument("--out", default=HERE.parent / "exports")
    args = ap.parse_args()
    for name, n in write_exports(args.db, args.out, args.database_url).items():
        print(f"{n:>5} rows  {Path(args.out) / name}")
