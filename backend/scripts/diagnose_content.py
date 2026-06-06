"""
One-shot diagnostic for the "content_type=series returns 0" problem.

Run from the backend/ directory:   python scripts/diagnose_content.py

It answers the two questions that fully explain the bug:
  1. What content_type values + counts are actually in the DB? (casing check)
  2. What would a freshly-built in-memory catalog contain? (what the server
     serves AFTER a restart)

Compare the script's catalog counts against what your RUNNING server returns
from GET /content (no filter). If they differ, the running server's catalog
is stale and a restart fixes it.
"""

import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text, select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db.database import SessionLocal      # noqa: E402
from services import catalog_service       # noqa: E402
from models import Content                 # noqa: E402

db = SessionLocal()
try:
    # 1) Raw SQL: exact content_type strings + counts (reveals casing).
    print("=== DB: SELECT content_type, COUNT(*) GROUP BY content_type ===")
    rows = db.execute(
        text("SELECT content_type, COUNT(*) FROM content GROUP BY content_type")
    ).all()
    for value, count in rows:
        print(f"  {value!r}: {count}")

    # 2) Exact-match count the route's filter relies on (lowercase 'series').
    series_exact = db.execute(
        text("SELECT COUNT(*) FROM content WHERE content_type = 'series'")
    ).scalar()
    print(f"\nRows where content_type = 'series' (exact): {series_exact}")

    # 3) What a fresh catalog build would hold (i.e. post-restart state).
    catalog_service.build_catalog(db)
    catalog = catalog_service.get_all_content()
    dist = Counter(c["content_type"] for c in catalog)
    print(f"\n=== Fresh in-memory catalog: {len(catalog)} items ===")
    for value, count in dist.items():
        print(f"  {value!r}: {count}")

    print("\nINTERPRETATION:")
    print("  - If DB shows 'Series' (capital): casing bug -> the route fix handles it.")
    print("  - If DB shows 'series' (lowercase) AND your RUNNING /content total")
    print("    is ~222 (not 465): the running catalog is STALE -> restart uvicorn.")
finally:
    db.close()
