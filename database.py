from __future__ import annotations

import os
import sqlite3
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "redditscout.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            selftext TEXT,
            score INTEGER DEFAULT 0,
            num_comments INTEGER DEFAULT 0,
            url TEXT,
            permalink TEXT,
            created_utc REAL,
            author TEXT,
            fetched_at TEXT DEFAULT (datetime('now')),
            source TEXT  -- 'scan', 'opportunities', 'discover'
        );

        CREATE TABLE IF NOT EXISTS ai_scores (
            post_id TEXT PRIMARY KEY REFERENCES posts(id),
            relevance REAL,
            pain_clarity REAL,
            emotional_intensity REAL,
            implementability REAL,
            technical_depth REAL,
            composite_score REAL,
            summary TEXT,
            category TEXT,
            scored_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subreddit_discovery (
            name TEXT PRIMARY KEY,
            title TEXT,
            subscribers INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            posts_per_day REAL DEFAULT 0,
            description TEXT,
            nsfw INTEGER DEFAULT 0,
            discovered_at TEXT DEFAULT (datetime('now')),
            topic TEXT
        );

        CREATE TABLE IF NOT EXISTS karma_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            subreddit TEXT NOT NULL,
            post_karma INTEGER DEFAULT 0,
            comment_karma INTEGER DEFAULT 0,
            total_karma INTEGER DEFAULT 0,
            posts INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            snapshot_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS saved_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,  -- 'subreddits' or 'keywords'
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(name, kind)
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL UNIQUE,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            num_comments INTEGER DEFAULT 0,
            source TEXT,
            status TEXT DEFAULT 'saved',
            notes TEXT DEFAULT '',
            bookmarked_at TEXT DEFAULT (datetime('now')),
            acted_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_bookmarks_status ON bookmarks(status);
        CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
        CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source);
        CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_utc);
        CREATE INDEX IF NOT EXISTS idx_ai_scores_composite ON ai_scores(composite_score);
        CREATE INDEX IF NOT EXISTS idx_saved_lists_kind ON saved_lists(kind);
    """)
    conn.commit()
    conn.close()


# --- Posts ---

def save_posts(posts: list[dict], source: str) -> int:
    """Save posts to DB. Returns count of newly inserted posts."""
    conn = _get_conn()
    inserted = 0
    for p in posts:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO posts
                   (id, subreddit, title, selftext, score, num_comments, url, permalink, created_utc, author, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    p.get("id", ""),
                    p.get("subreddit", ""),
                    p.get("title", ""),
                    p.get("selftext", ""),
                    p.get("score", 0),
                    p.get("comments", p.get("num_comments", 0)),
                    p.get("url", ""),
                    p.get("permalink", ""),
                    p.get("created_utc", 0),
                    p.get("author", ""),
                    source,
                ),
            )
            if conn.total_changes:
                inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return inserted


def is_post_seen(post_id: str) -> bool:
    """Check if a post has already been stored."""
    conn = _get_conn()
    row = conn.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return row is not None


def get_posts(source: str = None, limit: int = 200) -> list[dict]:
    """Retrieve stored posts, optionally filtered by source."""
    conn = _get_conn()
    if source:
        rows = conn.execute(
            "SELECT * FROM posts WHERE source = ? ORDER BY created_utc DESC LIMIT ?",
            (source, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM posts ORDER BY created_utc DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- AI Scores ---

def save_ai_score(post_id: str, scores: dict) -> None:
    """Save AI analysis scores for a post."""
    conn = _get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO ai_scores
           (post_id, relevance, pain_clarity, emotional_intensity,
            implementability, technical_depth, composite_score, summary, category)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            post_id,
            scores.get("relevance", 0),
            scores.get("pain_clarity", 0),
            scores.get("emotional_intensity", 0),
            scores.get("implementability", 0),
            scores.get("technical_depth", 0),
            scores.get("composite_score", 0),
            scores.get("summary", ""),
            scores.get("category", ""),
        ),
    )
    conn.commit()
    conn.close()


def get_scored_posts(min_score: float = 0, limit: int = 100) -> list[dict]:
    """Retrieve posts with AI scores, sorted by composite score."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT p.*, s.relevance, s.pain_clarity, s.emotional_intensity,
                  s.implementability, s.technical_depth, s.composite_score,
                  s.summary, s.category
           FROM posts p
           JOIN ai_scores s ON p.id = s.post_id
           WHERE s.composite_score >= ?
           ORDER BY s.composite_score DESC
           LIMIT ?""",
        (min_score, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Subreddit Discovery ---

def save_discovered_subreddits(subreddits: list[dict], topic: str) -> None:
    conn = _get_conn()
    for s in subreddits:
        conn.execute(
            """INSERT OR REPLACE INTO subreddit_discovery
               (name, title, subscribers, active_users, posts_per_day, description, nsfw, topic)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                s["name"], s.get("title", ""), s.get("subscribers", 0),
                s.get("active_users", 0), s.get("posts_per_day", 0),
                s.get("description", ""), 1 if s.get("nsfw") else 0, topic,
            ),
        )
    conn.commit()
    conn.close()


def get_discovered_subreddits(topic: str = None) -> list[dict]:
    conn = _get_conn()
    if topic:
        rows = conn.execute(
            "SELECT * FROM subreddit_discovery WHERE topic = ? ORDER BY subscribers DESC",
            (topic,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM subreddit_discovery ORDER BY subscribers DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Karma ---

def save_karma_snapshot(data: dict) -> None:
    conn = _get_conn()
    username = data["username"]
    for s in data["subreddits"]:
        conn.execute(
            """INSERT INTO karma_snapshots
               (username, subreddit, post_karma, comment_karma, total_karma, posts, comments)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                username, s["subreddit"], s.get("post_karma", 0),
                s.get("comment_karma", 0), s.get("total_karma", 0),
                s.get("posts", 0), s.get("comments", 0),
            ),
        )
    conn.commit()
    conn.close()


# --- Stats helpers for Home dashboard ---

def get_karma_history(limit: int = 30) -> list[dict]:
    """Return total karma per snapshot, ordered oldest → newest."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT snapshot_at,
                  SUM(total_karma)   AS total_karma,
                  SUM(comment_karma) AS comment_karma,
                  SUM(post_karma)    AS post_karma
           FROM karma_snapshots
           GROUP BY snapshot_at
           ORDER BY snapshot_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_stats() -> dict:
    """Quick counts for the Home dashboard."""
    conn = _get_conn()
    posts_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    scored_count = conn.execute("SELECT COUNT(*) FROM ai_scores").fetchone()[0]
    lists_count = conn.execute("SELECT COUNT(*) FROM saved_lists").fetchone()[0]
    conn.close()
    return {
        "posts_scanned": posts_count,
        "posts_scored": scored_count,
        "saved_lists": lists_count,
    }


# Initialize on import
init_db()
