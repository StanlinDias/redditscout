from datetime import datetime, timezone

import praw


def discover_subreddits(
    reddit: praw.Reddit,
    topic: str,
    limit: int = 25,
) -> list[dict]:
    """
    Search Reddit for subreddits related to a topic.

    Returns a list of dicts ranked by subscriber count, with an activity
    estimate (posts per day based on the 25 most recent posts).
    """
    results = []
    seen: set[str] = set()

    # Search subreddits by name and description
    for sub in reddit.subreddits.search(topic, limit=limit):
        if sub.display_name.lower() in seen:
            continue
        seen.add(sub.display_name.lower())

        activity = _estimate_activity(sub)
        active = getattr(sub, "accounts_active", None) or getattr(sub, "active_user_count", 0) or 0
        results.append({
            "name": sub.display_name,
            "title": sub.title,
            "subscribers": sub.subscribers or 0,
            "active_users": active,
            "posts_per_day": activity,
            "description": (sub.public_description or "")[:120],
            "url": f"https://reddit.com/r/{sub.display_name}",
            "nsfw": sub.over18,
        })

    results.sort(key=lambda r: (r["subscribers"], r["posts_per_day"]), reverse=True)
    return results


def _estimate_activity(subreddit) -> float:
    """Estimate posts per day from the 25 most recent posts."""
    try:
        posts = list(subreddit.new(limit=25))
    except Exception:
        return 0.0

    if len(posts) < 2:
        return 0.0

    newest = posts[0].created_utc
    oldest = posts[-1].created_utc
    span_days = (newest - oldest) / 86400

    if span_days <= 0:
        return 0.0

    return round(len(posts) / span_days, 1)


def print_discovery_results(results: list[dict]) -> None:
    """Pretty-print discovery results to the terminal."""
    if not results:
        print("No subreddits found for that topic.")
        return

    print(f"\n{'='*80}")
    print(f"  Found {len(results)} subreddit(s)")
    print(f"{'='*80}\n")

    print(f"  {'Subreddit':<25} {'Subscribers':>12} {'Active':>8} {'Posts/day':>10} {'NSFW':>6}")
    print(f"  {'-'*25} {'-'*12} {'-'*8} {'-'*10} {'-'*6}")

    for r in results:
        nsfw = "Yes" if r["nsfw"] else ""
        print(
            f"  r/{r['name']:<23} {r['subscribers']:>12,} {r['active_users']:>8,} "
            f"{r['posts_per_day']:>10} {nsfw:>6}"
        )

    print()
