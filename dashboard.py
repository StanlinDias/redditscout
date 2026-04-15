#!/usr/bin/env python3
"""RedditScout — Streamlit Dashboard"""

import streamlit as st

from reddit_client import get_reddit
from scanner import scan_subreddits
from discovery import discover_subreddits
from opportunities import find_opportunities
from karma import get_karma_breakdown
from database import (
    save_posts, save_discovered_subreddits, save_karma_snapshot,
    save_ai_score, get_scored_posts,
)
from exporter import (
    export_scan_results, export_discovery_results,
    export_opportunities, export_karma,
)

st.set_page_config(page_title="RedditScout", page_icon="🔍", layout="wide")

# --- Sidebar ---
st.sidebar.title("RedditScout")
st.sidebar.markdown("Reddit reconnaissance & opportunity finder")

try:
    reddit = get_reddit()
    user = reddit.user.me()
    st.sidebar.success(f"Connected as u/{user.name}")
except Exception as e:
    st.sidebar.error(f"Reddit connection failed: {e}")
    st.stop()

page = st.sidebar.radio(
    "Navigate",
    ["Discover Subreddits", "Keyword Scanner", "Opportunities", "AI Scoring", "Karma Tracker"],
)

# ===== Discover Subreddits =====
if page == "Discover Subreddits":
    st.header("Subreddit Discovery")
    st.caption("Find relevant subreddits for any topic, ranked by size and activity.")

    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input("Topic", placeholder="e.g. ai tools, saas, side projects")
    with col2:
        limit = st.number_input("Max results", min_value=5, max_value=100, value=25)

    if st.button("Discover", type="primary") and topic:
        with st.spinner(f"Searching for subreddits related to \"{topic}\"..."):
            results = discover_subreddits(reddit, topic, limit=limit)

        if results:
            save_discovered_subreddits(results, topic)

            st.success(f"Found {len(results)} subreddit(s)")
            st.dataframe(
                [
                    {
                        "Subreddit": f"r/{r['name']}",
                        "Subscribers": r["subscribers"],
                        "Active": r["active_users"],
                        "Posts/day": r["posts_per_day"],
                        "Description": r["description"],
                        "NSFW": "Yes" if r["nsfw"] else "",
                    }
                    for r in results
                ],
                use_container_width=True,
                hide_index=True,
            )

            path = export_discovery_results(results)
            st.info(f"Exported to `{path}`")
        else:
            st.warning("No subreddits found.")

# ===== Keyword Scanner =====
elif page == "Keyword Scanner":
    st.header("Keyword Scanner")
    st.caption("Scan subreddits for posts matching your keywords.")

    keywords = st.text_input("Keywords (comma-separated)", placeholder="micro saas, side project, ai tools")
    subreddits = st.text_input("Subreddits (comma-separated)", placeholder="SaaS, indiehackers, startups")

    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input("Posts per subreddit", min_value=10, max_value=500, value=100)

    if st.button("Scan", type="primary") and keywords and subreddits:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        sub_list = [s.strip() for s in subreddits.split(",") if s.strip()]

        with st.spinner(f"Scanning {len(sub_list)} subreddit(s) for {len(kw_list)} keyword(s)..."):
            results = scan_subreddits(reddit, kw_list, sub_list, limit=limit)

        if results:
            save_posts(
                [dict(r, id=r["url"].split("/comments/")[1].split("/")[0] if "/comments/" in r["url"] else r["url"]) for r in results],
                source="scan",
            )

            st.success(f"Found {len(results)} matching post(s)")
            for r in results:
                with st.expander(f"r/{r['subreddit']}  |  {r['age']}  |  score: {r['score']}  |  {r['comments']} comments"):
                    st.markdown(f"**{r['title']}**")
                    st.markdown(f"Matched keyword: `{r['matched_keyword']}`")
                    st.markdown(f"[Open on Reddit]({r['url']})")

            path = export_scan_results(results)
            st.info(f"Exported to `{path}`")
        else:
            st.warning("No matching posts found.")

# ===== Opportunities =====
elif page == "Opportunities":
    st.header("Opportunity Finder")
    st.caption("Find posts where people are asking for recommendations, feedback, or tools.")

    subreddits = st.text_input("Subreddits (comma-separated)", placeholder="SaaS, startups, indiehackers")
    extra_kw = st.text_input("Extra keywords (optional)", placeholder="looking for, need help with")

    col1, col2, col3 = st.columns(3)
    with col1:
        max_age = st.number_input("Max age (hours)", min_value=1, max_value=168, value=24)
    with col2:
        max_comments = st.number_input("Max comments", min_value=1, max_value=500, value=50)
    with col3:
        limit = st.number_input("Posts per sub", min_value=10, max_value=500, value=100)

    if st.button("Find Opportunities", type="primary") and subreddits:
        sub_list = [s.strip() for s in subreddits.split(",") if s.strip()]
        extra = [k.strip() for k in extra_kw.split(",") if k.strip()] if extra_kw else None

        with st.spinner(f"Finding opportunities in {len(sub_list)} subreddit(s)..."):
            results = find_opportunities(
                reddit, sub_list, extra_keywords=extra,
                max_age_hours=max_age, max_comments=max_comments, limit=limit,
            )

        if results:
            st.success(f"Found {len(results)} opportunity post(s)")

            fresh = [r for r in results if not r["already_engaged"]]
            engaged = [r for r in results if r["already_engaged"]]

            if fresh:
                st.subheader(f"New subreddits ({len(fresh)})")
                for r in fresh:
                    with st.expander(f"r/{r['subreddit']}  |  {r['age']}  |  {r['comments']} comments  |  Pattern: \"{r['matched_pattern']}\""):
                        st.markdown(f"**{r['title']}**")
                        st.markdown(f"Score: {r['score']}  |  Pattern: `{r['matched_pattern']}`")
                        st.markdown(f"[Open on Reddit]({r['url']})")

            if engaged:
                st.subheader(f"Already engaged ({len(engaged)})")
                for r in engaged:
                    with st.expander(f"r/{r['subreddit']}  |  {r['age']}  |  {r['comments']} comments"):
                        st.markdown(f"**{r['title']}**")
                        st.markdown(f"Score: {r['score']}  |  Pattern: `{r['matched_pattern']}`")
                        st.markdown(f"[Open on Reddit]({r['url']})")

            path = export_opportunities(results)
            st.info(f"Exported to `{path}`")
        else:
            st.warning("No opportunities found.")

# ===== AI Scoring =====
elif page == "AI Scoring":
    st.header("AI Pain-Point Scoring")
    st.caption("Score posts on relevance, pain clarity, emotional intensity, implementability, and technical depth.")

    import os
    if not os.getenv("GEMINI_API_KEY"):
        st.warning("Add `GEMINI_API_KEY` to your `.env` file to use AI scoring.")
        st.code("GEMINI_API_KEY=AIza...", language="text")
        st.stop()

    subreddits = st.text_input("Subreddits to scan", placeholder="SaaS, startups, indiehackers")
    keywords = st.text_input("Keywords", placeholder="looking for, need help, pain point")

    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input("Posts to fetch per sub", min_value=5, max_value=200, value=50)
    with col2:
        max_score = st.number_input("Max posts to score (API cost control)", min_value=1, max_value=50, value=10)

    if st.button("Scan & Score", type="primary") and subreddits:
        from analyzer import score_posts

        sub_list = [s.strip() for s in subreddits.split(",") if s.strip()]
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else ["looking for", "need help", "recommendation"]

        with st.spinner("Fetching posts..."):
            results = find_opportunities(
                reddit, sub_list, extra_keywords=kw_list,
                max_age_hours=168, max_comments=200, limit=limit,
            )

        if not results:
            st.warning("No matching posts found to score.")
            st.stop()

        # Add selftext for scoring
        st.info(f"Found {len(results)} posts. Scoring top {min(max_score, len(results))} with AI...")
        to_score = results[:max_score]

        # Fetch full post text
        with st.spinner("Fetching post bodies..."):
            for r in to_score:
                try:
                    post_id = r["url"].split("/comments/")[1].split("/")[0]
                    submission = reddit.submission(id=post_id)
                    r["selftext"] = submission.selftext or ""
                    r["id"] = post_id
                except Exception:
                    r["selftext"] = ""
                    r["id"] = ""

        progress = st.progress(0, text="Scoring posts with AI...")
        def update_progress(current, total, title):
            progress.progress(current / total, text=f"Scoring {current}/{total}: {title}...")

        scored = score_posts(to_score, progress_callback=update_progress)
        progress.empty()

        if scored:
            # Save to database
            for p in scored:
                if p.get("id"):
                    save_ai_score(p["id"], p["ai_scores"])

            st.success(f"Scored {len(scored)} post(s)")
            for p in scored:
                s = p.get("ai_scores", {})
                composite = s.get("composite_score", 0)

                color = "🟢" if composite >= 7 else "🟡" if composite >= 4 else "🔴"
                with st.expander(f"{color} [{composite:.1f}/10]  r/{p['subreddit']}  —  {p['title'][:80]}"):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Relevance", f"{s.get('relevance', 0)}/10")
                    col2.metric("Pain", f"{s.get('pain_clarity', 0)}/10")
                    col3.metric("Emotion", f"{s.get('emotional_intensity', 0)}/10")
                    col4.metric("Implement", f"{s.get('implementability', 0)}/10")
                    col5.metric("Technical", f"{s.get('technical_depth', 0)}/10")

                    st.markdown(f"**Category:** {s.get('category', '?')}")
                    st.markdown(f"**Summary:** {s.get('summary', '')}")
                    st.markdown(f"[Open on Reddit]({p['url']})")

    # Show previously scored posts
    st.divider()
    st.subheader("Previously Scored Posts")
    stored = get_scored_posts(min_score=0, limit=50)
    if stored:
        st.dataframe(
            [
                {
                    "Score": r["composite_score"],
                    "Subreddit": r["subreddit"],
                    "Title": r["title"][:80],
                    "Category": r["category"],
                    "Summary": r["summary"],
                }
                for r in stored
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No scored posts yet. Run a scan above to get started.")

# ===== Karma Tracker =====
elif page == "Karma Tracker":
    st.header("Karma Tracker")
    st.caption("Your karma breakdown by subreddit.")

    limit = st.number_input("Recent items to analyze", min_value=50, max_value=1000, value=200)

    if st.button("Fetch Karma", type="primary"):
        with st.spinner("Fetching karma breakdown..."):
            data = get_karma_breakdown(reddit, limit=limit)

        save_karma_snapshot(data)

        st.metric("Total Comment Karma", f"{data['total_comment_karma']:,}")
        st.metric("Total Link Karma", f"{data['total_link_karma']:,}")

        subs = data["subreddits"]
        if subs:
            st.dataframe(
                [
                    {
                        "Subreddit": f"r/{s['subreddit']}",
                        "Posts": s["posts"],
                        "Post Karma": s["post_karma"],
                        "Comments": s["comments"],
                        "Comment Karma": s["comment_karma"],
                        "Total Karma": s["total_karma"],
                    }
                    for s in subs
                ],
                use_container_width=True,
                hide_index=True,
            )

            path = export_karma(data)
            st.info(f"Exported to `{path}`")
        else:
            st.warning("No recent activity found.")
