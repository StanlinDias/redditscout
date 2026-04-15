from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import praw

# Patterns that signal someone is looking for recommendations / feedback
OPPORTUNITY_PATTERNS = [
    # Recommendation-seeking
    r"looking for\b",
    r"any recommendations\b",
    r"can anyone recommend\b",
    r"what do you use\b",
    r"what tools do you use\b",
    r"what do you recommend\b",
    r"need help with\b",
    r"suggest(ions)?\b",
    r"alternative(s)? to\b",
    r"best .{0,30} for\b",
    r"anyone know of\b",
    r"is there a\b.{0,30}\btool\b",
    r"how do you handle\b",
    r"what('s| is) the best\b",
    # Feedback-seeking
    r"feedback on\b",
    r"looking for feedback\b",
    r"would love feedback\b",
    r"honest feedback\b",
    r"roast my\b",
    r"review my\b",
    r"thoughts on\b.{0,30}\b(app|tool|site|product|idea|startup|project)\b",
    # Pain-point signals (from reddit-painpointer)
    r"spending hours (every|on)\b",
    r"hate manually\b",
    r"tedious process\b",
    r"wish there was a (tool|way|app|solution)\b",
    r"there('s| is) no good\b",
    r"can('t|not) find a\b.{0,30}\b(tool|app|solution|way)\b",
    r"wasting time on\b",
    r"so frustrat(ed|ing)\b",
    r"pain( |-)?point\b",
    r"struggle(s|d)? with\b",
    r"sick of\b",
    r"tired of\b",
    r"manual(ly)? .{0,20} every\b",
    r"automate .{0,30} workflow\b",
    r"does anyone have a (solution|fix|workaround)\b",
    r"what('s| is) your .{0,20} (workflow|stack|process|setup)\b",
    r"how (are|do) you .{0,20} (managing|handling|dealing|tracking)\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in OPPORTUNITY_PATTERNS]


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


def _match_patterns(text: str, extra_keywords: list[str] | None = None) -> str | None:
    """Return the first matching pattern/keyword found in text, or None."""
    for pattern in COMPILED_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(0)

    if extra_keywords:
        text_lower = text.lower()
        for kw in extra_keywords:
            if kw.lower() in text_lower:
                return kw

    return None


def find_opportunities(
    reddit: praw.Reddit,
    subreddit_names: list[str],
    extra_keywords: list[str] | None = None,
    max_age_hours: int = 24,
    max_comments: int = 50,
    limit: int = 100,
) -> list[dict]:
    """
    Find posts where someone is asking for recommendations, feedback, or tool
    suggestions. Filters for comment-friendly posts (recent, low comment count).
    """
    # Fetch subreddits user has already engaged in
    engaged_subs = _get_engaged_subreddits(reddit)

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

            age_h = _age_hours(post.created_utc)
            if age_h > max_age_hours:
                continue
            if post.num_comments >= max_comments:
                continue

            text = f"{post.title} {post.selftext or ''}"
            matched = _match_patterns(text, extra_keywords)
            if not matched:
                continue

            seen_ids.add(post.id)
            already_engaged = sub_name.lower() in engaged_subs
            results.append({
                "subreddit": sub_name,
                "title": post.title,
                "score": post.score,
                "comments": post.num_comments,
                "url": f"https://reddit.com{post.permalink}",
                "age": _age_str(post.created_utc),
                "age_hours": round(age_h, 1),
                "matched_pattern": matched,
                "already_engaged": already_engaged,
                "created_utc": post.created_utc,
            })

    # Sort: not-yet-engaged subreddits first, then by recency
    results.sort(key=lambda r: (r["already_engaged"], -r["created_utc"]))
    return results


def _get_engaged_subreddits(reddit: praw.Reddit) -> set[str]:
    """Return lowercase names of subreddits the user has recently engaged in."""
    subs: set[str] = set()
    try:
        user = reddit.user.me()
        for comment in user.comments.new(limit=100):
            subs.add(comment.subreddit.display_name.lower())
        for submission in user.submissions.new(limit=100):
            subs.add(submission.subreddit.display_name.lower())
    except Exception:
        pass
    return subs


def print_opportunities(results: list[dict]) -> None:
    """Pretty-print opportunity results to the terminal."""
    if not results:
        print("No opportunities found.")
        return

    fresh = [r for r in results if not r["already_engaged"]]
    engaged = [r for r in results if r["already_engaged"]]

    print(f"\n{'='*80}")
    print(f"  Found {len(results)} opportunity post(s)  "
          f"({len(fresh)} in new subs, {len(engaged)} in subs you've engaged in)")
    print(f"{'='*80}\n")

    for r in results:
        tag = " [already engaged]" if r["already_engaged"] else ""
        print(f"  r/{r['subreddit']}{tag}  |  {r['age']}  |  "
              f"score: {r['score']}  |  {r['comments']} comments")
        print(f"  {r['title']}")
        print(f"  Pattern: \"{r['matched_pattern']}\"")
        print(f"  {r['url']}")
        print(f"  {'-'*70}")
