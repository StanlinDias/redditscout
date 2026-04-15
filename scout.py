#!/usr/bin/env python3
"""RedditScout — CLI tool for Reddit reconnaissance and opportunity finding."""

import click

from reddit_client import get_reddit
from scanner import scan_subreddits, print_scan_results
from discovery import discover_subreddits, print_discovery_results
from opportunities import find_opportunities, print_opportunities
from karma import get_karma_breakdown, print_karma
from exporter import (
    export_scan_results,
    export_discovery_results,
    export_opportunities,
    export_karma,
)


@click.group()
@click.version_option(version="2.0.0", prog_name="RedditScout")
def cli():
    """RedditScout — find opportunities and track engagement on Reddit."""
    pass


@cli.command()
@click.option("--topic", required=True, help="Topic to search for (e.g. 'ai tools', 'saas').")
@click.option("--limit", default=25, show_default=True, help="Max number of subreddits to return.")
@click.option("--no-export", is_flag=True, help="Skip CSV export.")
def discover(topic: str, limit: int, no_export: bool):
    """Find relevant subreddits for a topic, ranked by size and activity."""
    reddit = get_reddit()
    click.echo(f"Searching for subreddits related to \"{topic}\"...")

    results = discover_subreddits(reddit, topic, limit=limit)
    print_discovery_results(results)

    if results and not no_export:
        path = export_discovery_results(results)
        click.echo(f"  Exported to {path}")


@cli.command()
@click.option("--keywords", required=True, help="Comma-separated keywords to scan for.")
@click.option("--subreddits", required=True, help="Comma-separated subreddit names to scan.")
@click.option("--limit", default=100, show_default=True, help="Posts to fetch per subreddit.")
@click.option("--no-export", is_flag=True, help="Skip CSV export.")
def scan(keywords: str, subreddits: str, limit: int, no_export: bool):
    """Scan subreddits for posts matching keywords."""
    reddit = get_reddit()

    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    sub_list = [s.strip() for s in subreddits.split(",") if s.strip()]

    click.echo(f"Scanning {len(sub_list)} subreddit(s) for {len(kw_list)} keyword(s)...")

    results = scan_subreddits(reddit, kw_list, sub_list, limit=limit)
    print_scan_results(results)

    if results and not no_export:
        path = export_scan_results(results)
        click.echo(f"  Exported to {path}")


@cli.command()
@click.option("--subreddits", required=True, help="Comma-separated subreddit names to search.")
@click.option("--keywords", default="", help="Extra comma-separated keywords beyond built-in patterns.")
@click.option("--max-age", default=24, show_default=True, help="Max post age in hours.")
@click.option("--max-comments", default=50, show_default=True, help="Max comment count to qualify.")
@click.option("--limit", default=100, show_default=True, help="Posts to fetch per subreddit.")
@click.option("--no-export", is_flag=True, help="Skip CSV export.")
def opportunities(
    subreddits: str,
    keywords: str,
    max_age: int,
    max_comments: int,
    limit: int,
    no_export: bool,
):
    """Find posts where people are asking for recommendations or feedback."""
    reddit = get_reddit()

    sub_list = [s.strip() for s in subreddits.split(",") if s.strip()]
    extra_kw = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else None

    click.echo(f"Finding opportunities in {len(sub_list)} subreddit(s)...")

    results = find_opportunities(
        reddit, sub_list,
        extra_keywords=extra_kw,
        max_age_hours=max_age,
        max_comments=max_comments,
        limit=limit,
    )
    print_opportunities(results)

    if results and not no_export:
        path = export_opportunities(results)
        click.echo(f"  Exported to {path}")


@cli.command()
@click.option("--limit", default=200, show_default=True, help="Recent items to analyze per category.")
@click.option("--no-export", is_flag=True, help="Skip CSV export.")
def karma(limit: int, no_export: bool):
    """Show your karma breakdown by subreddit."""
    reddit = get_reddit()
    click.echo("Fetching karma breakdown...")

    data = get_karma_breakdown(reddit, limit=limit)
    print_karma(data)

    if not no_export:
        path = export_karma(data)
        click.echo(f"  Exported to {path}")


@cli.command()
@click.option("--subreddits", required=True, help="Comma-separated subreddit names to search.")
@click.option("--keywords", default="", help="Extra comma-separated keywords.")
@click.option("--max-score-count", default=10, show_default=True, help="Max posts to score (controls API cost).")
@click.option("--limit", default=50, show_default=True, help="Posts to fetch per subreddit.")
@click.option("--no-export", is_flag=True, help="Skip CSV export.")
def analyze(subreddits: str, keywords: str, max_score_count: int, limit: int, no_export: bool):
    """AI-score posts for pain-point potential (requires OPENAI_API_KEY)."""
    from analyzer import score_posts, print_scored_results
    from database import save_ai_score

    reddit = get_reddit()
    sub_list = [s.strip() for s in subreddits.split(",") if s.strip()]
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else None

    click.echo(f"Fetching posts from {len(sub_list)} subreddit(s)...")
    results = find_opportunities(
        reddit, sub_list, extra_keywords=kw_list,
        max_age_hours=168, max_comments=200, limit=limit,
    )

    if not results:
        click.echo("No matching posts found to score.")
        return

    to_score = results[:max_score_count]
    click.echo(f"Found {len(results)} posts. Scoring top {len(to_score)} with AI...")

    # Fetch full post text
    for r in to_score:
        try:
            post_id = r["url"].split("/comments/")[1].split("/")[0]
            submission = reddit.submission(id=post_id)
            r["selftext"] = submission.selftext or ""
            r["id"] = post_id
        except Exception:
            r["selftext"] = ""
            r["id"] = ""

    def show_progress(current, total, title):
        click.echo(f"  [{current}/{total}] {title}...")

    scored = score_posts(to_score, progress_callback=show_progress)

    for p in scored:
        if p.get("id") and p.get("ai_scores"):
            save_ai_score(p["id"], p["ai_scores"])

    print_scored_results(scored)


@cli.command()
def web():
    """Launch the Streamlit web dashboard."""
    import subprocess
    import sys
    import os

    dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.py")
    click.echo("Starting RedditScout dashboard at http://localhost:8501 ...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])


if __name__ == "__main__":
    cli()
