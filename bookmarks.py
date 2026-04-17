"""Post queue / bookmarks — save posts to act on later."""

from __future__ import annotations

from typing import Literal

from database import _get_conn

Status = Literal["saved", "commented", "skipped"]


def add_bookmark(post: dict, source: str = "") -> bool:
    """Add a post to the queue. Returns False if already bookmarked."""
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO bookmarks
               (post_id, subreddit, title, url, score, num_comments, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                post.get("id", post.get("url", "")),
                post.get("subreddit", ""),
                post.get("title", ""),
                post.get("url", ""),
                post.get("score", 0),
                post.get("comments", post.get("num_comments", 0)),
                source,
            ),
        )
        conn.commit()
        inserted = conn.total_changes > 0
    except Exception:
        inserted = False
    finally:
        conn.close()
    return inserted


def is_bookmarked(post_id: str) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM bookmarks WHERE post_id = ?", (post_id,)
    ).fetchone()
    conn.close()
    return row is not None


def get_bookmarks(status: Status | None = None, limit: int = 100) -> list[dict]:
    conn = _get_conn()
    if status:
        rows = conn.execute(
            """SELECT * FROM bookmarks WHERE status = ?
               ORDER BY bookmarked_at DESC LIMIT ?""",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM bookmarks ORDER BY bookmarked_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_bookmarks() -> dict:
    """Return counts by status."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM bookmarks GROUP BY status"
    ).fetchall()
    conn.close()
    counts = {r["status"]: r["cnt"] for r in rows}
    counts["total"] = sum(counts.values())
    return counts


def update_status(post_id: str, status: Status, notes: str = "") -> None:
    conn = _get_conn()
    conn.execute(
        """UPDATE bookmarks
           SET status = ?, notes = ?, acted_at = datetime('now')
           WHERE post_id = ?""",
        (status, notes, post_id),
    )
    conn.commit()
    conn.close()


def remove_bookmark(post_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM bookmarks WHERE post_id = ?", (post_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
