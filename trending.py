"""Trending posts — find high-visibility posts where commenting maximizes reach.

Different from `opportunities.py`:
- Opportunities: low-comment posts asking for help (you provide the answer).
- Trending: high-velocity posts gaining traction (your comment rides the wave).
"""

from __future__ import annotations

from datetime import datetime, timezone

import praw
import prawcore


def _age_hours(created_utc: float) -> float:
    delta = datetime.now(timezone.utc) - datetime.fromtimestamp(created_utc, tz=timezone.utc)
    return delta.total_seconds() / 3600


def _age_str(created_utc: float) -> str:
    hours = _age_hours(created_utc)
    if hours < 1:
        return f"{int(hours * 60)}m ago"
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours // 24)}d ago"


def find_trending(
    reddit: praw.Reddit,
    subreddit_names: list[str],
    max_age_hours: int = 24,
    max_comments: int = 200,
    min_score: int = 50,
    min_upvote_ratio: float = 0.7,
    limit: int = 100,
) -> list[dict]:
    """Find high-visibility posts in the given subreddits, ranked by visibility score.

    Pulls from Reddit's own `.rising()` and `.hot()` listings, dedupes, then
    re-ranks with our criteria.

    Visibility score = velocity × (1 / (1 + comments/score))
      - velocity = upvotes per hour
      - comment-density penalty: more comments per upvote → harder for your comment to be seen
    """
    results = []
    seen_ids: set[str] = set()

    for sub_name in subreddit_names:
        sub = reddit.subreddit(sub_name)
        try:
            posts = list(sub.rising(limit=limit)) + list(sub.hot(limit=limit))
        except prawcore.exceptions.PrawcoreException as exc:
            print(f"  Warning: could not fetch r/{sub_name}: {exc}")
            continue

        for post in posts:
            if post.id in seen_ids:
                continue

            # Hard filters
            if post.stickied:
                continue
            age_h = _age_hours(post.created_utc)
            if age_h > max_age_hours:
                continue
            if post.num_comments > max_comments:
                continue
            if post.score < min_score:
                continue
            if post.upvote_ratio < min_upvote_ratio:
                continue

            seen_ids.add(post.id)

            velocity = post.score / max(1.0, age_h)
            comp_density = post.num_comments / max(1, post.score)
            visibility = velocity * (1 / (1 + comp_density))

            results.append({
                "id": post.id,
                "subreddit": sub_name,
                "title": post.title,
                "score": post.score,
                "comments": post.num_comments,
                "url": f"https://reddit.com{post.permalink}",
                "age": _age_str(post.created_utc),
                "age_hours": round(age_h, 1),
                "created_utc": post.created_utc,
                "upvote_ratio": round(post.upvote_ratio, 2),
                "velocity": round(velocity, 1),
                "visibility_score": round(visibility, 2),
                "author": str(post.author) if post.author else "[deleted]",
            })

    results.sort(key=lambda r: r["visibility_score"], reverse=True)
    return results


def print_trending(results: list[dict]) -> None:
    """Pretty-print trending results to the terminal."""
    if not results:
        print("No trending posts found.")
        return

    print(f"\n{'='*80}")
    print(f"  Found {len(results)} trending post(s)")
    print(f"{'='*80}\n")

    for r in results:
        print(
            f"  [vis {r['visibility_score']:>6.1f}]  "
            f"r/{r['subreddit']}  |  {r['age']}  |  "
            f"↑{r['score']:,}  ({int(r['upvote_ratio']*100)}%)  |  "
            f"{r['comments']} comments  |  ↑{r['velocity']}/hr"
        )
        print(f"  {r['title']}")
        print(f"  {r['url']}")
        print(f"  {'-'*70}")
