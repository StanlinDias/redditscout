"""Saved lists — reusable sets of subreddits or keywords."""

from __future__ import annotations

import sqlite3
from typing import Literal

from database import _get_conn


Kind = Literal["subreddits", "keywords"]


def _row_to_dict(row) -> dict:
    """Map DB row to consumer-friendly dict; expose 'content' column as 'values'."""
    d = dict(row)
    d["values"] = d.pop("content")
    return d


def get_lists(kind: Kind) -> list[dict]:
    """Return all saved lists of the given kind, newest-updated first."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT id, name, kind, content, created_at, updated_at
           FROM saved_lists
           WHERE kind = ?
           ORDER BY updated_at DESC""",
        (kind,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_list(name: str, kind: Kind) -> dict | None:
    """Return a single list by (name, kind) or None."""
    conn = _get_conn()
    row = conn.execute(
        """SELECT id, name, kind, content, created_at, updated_at
           FROM saved_lists
           WHERE name = ? AND kind = ?""",
        (name, kind),
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def save_list(name: str, kind: Kind, values: str) -> None:
    """Upsert a saved list. Updates content and `updated_at` if (name, kind) exists."""
    name = name.strip()
    values = values.strip()
    if not name or not values:
        raise ValueError("Both name and values are required.")

    conn = _get_conn()
    conn.execute(
        """INSERT INTO saved_lists (name, kind, content)
           VALUES (?, ?, ?)
           ON CONFLICT(name, kind) DO UPDATE SET
             content = excluded.content,
             updated_at = datetime('now')""",
        (name, kind, values),
    )
    conn.commit()
    conn.close()


def delete_list(name: str, kind: Kind) -> bool:
    """Delete a list. Returns True if a row was deleted."""
    conn = _get_conn()
    cur = conn.execute(
        "DELETE FROM saved_lists WHERE name = ? AND kind = ?",
        (name, kind),
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def rename_list(old_name: str, new_name: str, kind: Kind) -> bool:
    """Rename a list. Returns False if new_name already exists for this kind."""
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("New name cannot be empty.")

    conn = _get_conn()
    try:
        cur = conn.execute(
            """UPDATE saved_lists
               SET name = ?, updated_at = datetime('now')
               WHERE name = ? AND kind = ?""",
            (new_name, old_name, kind),
        )
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
