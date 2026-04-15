from collections import defaultdict

import praw


def get_karma_breakdown(reddit: praw.Reddit, limit: int = 200) -> dict:
    """
    Track the authenticated user's karma breakdown by subreddit.

    Returns a dict with user info, comment karma by sub, and post karma by sub.
    """
    user = reddit.user.me()

    comment_karma: dict[str, int] = defaultdict(int)
    post_karma: dict[str, int] = defaultdict(int)
    comment_count: dict[str, int] = defaultdict(int)
    post_count: dict[str, int] = defaultdict(int)

    for comment in user.comments.new(limit=limit):
        sub = comment.subreddit.display_name
        comment_karma[sub] += comment.score
        comment_count[sub] += 1

    for submission in user.submissions.new(limit=limit):
        sub = submission.subreddit.display_name
        post_karma[sub] += submission.score
        post_count[sub] += 1

    # Build per-subreddit summary
    all_subs = sorted(set(list(comment_karma.keys()) + list(post_karma.keys())))
    subreddits = []
    for sub in all_subs:
        subreddits.append({
            "subreddit": sub,
            "comment_karma": comment_karma.get(sub, 0),
            "post_karma": post_karma.get(sub, 0),
            "total_karma": comment_karma.get(sub, 0) + post_karma.get(sub, 0),
            "comments": comment_count.get(sub, 0),
            "posts": post_count.get(sub, 0),
        })

    subreddits.sort(key=lambda s: s["total_karma"], reverse=True)

    return {
        "username": user.name,
        "total_comment_karma": user.comment_karma,
        "total_link_karma": user.link_karma,
        "subreddits": subreddits,
    }


def print_karma(data: dict) -> None:
    """Pretty-print karma breakdown to the terminal."""
    print(f"\n{'='*80}")
    print(f"  Karma Tracker for u/{data['username']}")
    print(f"  Total comment karma: {data['total_comment_karma']:,}  |  "
          f"Total link karma: {data['total_link_karma']:,}")
    print(f"{'='*80}\n")

    subs = data["subreddits"]
    if not subs:
        print("  No recent activity found.")
        return

    print(f"  {'Subreddit':<25} {'Posts':>6} {'Post Karma':>11} "
          f"{'Comments':>9} {'Cmt Karma':>10} {'Total':>8}")
    print(f"  {'-'*25} {'-'*6} {'-'*11} {'-'*9} {'-'*10} {'-'*8}")

    for s in subs:
        print(
            f"  r/{s['subreddit']:<23} {s['posts']:>6} {s['post_karma']:>11,} "
            f"{s['comments']:>9} {s['comment_karma']:>10,} {s['total_karma']:>8,}"
        )

    print()
