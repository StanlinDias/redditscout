import csv
import os
from datetime import datetime


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def _ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _timestamped_path(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{prefix}_{ts}.csv")


def export_scan_results(results: list[dict]) -> str:
    """Export keyword scan results to CSV. Returns the file path."""
    _ensure_output_dir()
    path = _timestamped_path("scan")
    fields = ["subreddit", "title", "score", "comments", "url", "age", "matched_keyword"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    return path


def export_discovery_results(results: list[dict]) -> str:
    """Export subreddit discovery results to CSV. Returns the file path."""
    _ensure_output_dir()
    path = _timestamped_path("discovery")
    fields = ["name", "title", "subscribers", "active_users", "posts_per_day", "description", "url", "nsfw"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    return path


def export_opportunities(results: list[dict]) -> str:
    """Export opportunity finder results to CSV. Returns the file path."""
    _ensure_output_dir()
    path = _timestamped_path("opportunities")
    fields = [
        "subreddit", "title", "score", "comments", "url", "age",
        "matched_pattern", "already_engaged",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    return path


def export_karma(data: dict) -> str:
    """Export karma breakdown to CSV. Returns the file path."""
    _ensure_output_dir()
    path = _timestamped_path("karma")
    fields = ["subreddit", "posts", "post_karma", "comments", "comment_karma", "total_karma"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data["subreddits"])

    return path
