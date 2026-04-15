from datetime import datetime, timezone
from typing import Optional

import praw


def _age_str(created_utc: float) -> str:
    """Return a human-readable age string like '3h ago' or '2d ago'."""
    delta = datetime.now(timezone.utc) - datetime.fromtimestamp(created_utc, tz=timezone.utc)
    seconds = int(delta.total_seconds())
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def scan_subreddits(
    reddit: praw.Reddit,
    keywords: list[str],
    subreddit_names: list[str],
    limit: int = 100,
    time_filter: str = "week",
) -> list[dict]:
    """
    Scan the given subreddits for recent posts matching any of the keywords.

    Returns a list of dicts with post metadata.
    """
    results = []
    seen_ids: set[str] = set()

    for sub_name in subreddit_names:
        subreddit = reddit.subreddit(sub_name)
        try:
            posts = list(subreddit.new(limit=limit))
        except Exception as exc:
            print(f"  Warning: could not fetch r/{sub_name}: {exc}")
            continue

        for post in posts:
            if post.id in seen_ids:
                continue
            title_lower = post.title.lower()
            body_lower = (post.selftext or "").lower()
            for kw in keywords:
                if kw.lower() in title_lower or kw.lower() in body_lower:
                    seen_ids.add(post.id)
                    results.append({
                        "subreddit": sub_name,
                        "title": post.title,
                        "score": post.score,
                        "comments": post.num_comments,
                        "url": f"https://reddit.com{post.permalink}",
                        "age": _age_str(post.created_utc),
                        "created_utc": post.created_utc,
                        "matched_keyword": kw,
                    })
                    break  # one match per post is enough

    results.sort(key=lambda r: r["created_utc"], reverse=True)
    return results


def print_scan_results(results: list[dict]) -> None:
    """Pretty-print scan results to the terminal."""
    if not results:
        print("No matching posts found.")
        return

    print(f"\n{'='*80}")
    print(f"  Found {len(results)} matching post(s)")
    print(f"{'='*80}\n")

    for r in results:
        print(f"  r/{r['subreddit']}  |  {r['age']}  |  score: {r['score']}  |  {r['comments']} comments")
        print(f"  {r['title']}")
        print(f"  Keyword: \"{r['matched_keyword']}\"")
        print(f"  {r['url']}")
        print(f"  {'-'*70}")
