#!/usr/bin/env python3
"""RedditScout — Streamlit Dashboard"""

from __future__ import annotations

import os

import streamlit as st

import ui
from reddit_client import get_reddit
from scanner import scan_subreddits
from discovery import discover_subreddits
from opportunities import find_opportunities
from trending import find_trending
from karma import get_karma_breakdown
from database import (
    save_posts, save_discovered_subreddits, save_karma_snapshot,
    save_ai_score, get_scored_posts, get_karma_history, get_stats,
    get_onboarding_progress,
)
from exporter import (
    export_scan_results, export_discovery_results,
    export_opportunities, export_karma,
)
from lists import (
    get_lists, get_list, save_list, delete_list, rename_list,
)
from bookmarks import (
    add_bookmark, is_bookmarked, get_bookmarks, count_bookmarks,
    update_status, remove_bookmark,
)

st.set_page_config(
    page_title="RedditScout",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

ui.inject_styles()


# --- Helpers ---
def _on_list_load(value_key: str, kind: str, load_key: str) -> None:
    """Callback: when a saved list is picked, push its values into the text input."""
    selected = st.session_state.get(load_key)
    if selected and selected != "— none —":
        lst = get_list(selected, kind)
        if lst:
            st.session_state[value_key] = lst["values"]


def list_input(
    label: str,
    placeholder: str,
    kind: str,
    key: str,
    help: str | None = None,
) -> str:
    """Text input + saved-list load/save controls.

    - `kind` is 'subreddits' or 'keywords' — picks the right list pool.
    - `key` must be unique per input across the app.
    """
    value_key = f"{key}_value"
    load_key = f"{key}_load"
    saving_key = f"{key}_saving"

    lists = get_lists(kind)
    options = ["— none —"] + [lst["name"] for lst in lists]

    # Field label
    st.markdown(
        f'<div style="font-weight:500; font-size:0.875rem; color:var(--text); margin-bottom:0.4rem;">{label}</div>',
        unsafe_allow_html=True,
    )

    # Load + Save controls
    col_load, col_save = st.columns([3, 1])
    with col_load:
        st.selectbox(
            "Load saved list",
            options,
            key=load_key,
            on_change=_on_list_load,
            args=(value_key, kind, load_key),
            label_visibility="collapsed",
            disabled=(len(lists) == 0),
            help="Load a previously saved list" if lists else "No saved lists yet — save one from this input first.",
        )
    with col_save:
        if st.button("Save as…", key=f"{key}_save_btn", use_container_width=True):
            st.session_state[saving_key] = not st.session_state.get(saving_key, False)

    # Save-as inline form
    if st.session_state.get(saving_key):
        name_col, save_col, cancel_col = st.columns([3, 1, 1])
        with name_col:
            name = st.text_input(
                "List name",
                key=f"{key}_name",
                placeholder="e.g. SaaS communities",
                label_visibility="collapsed",
            )
        with save_col:
            if st.button("Save", key=f"{key}_confirm_save", type="primary", use_container_width=True):
                current_value = st.session_state.get(value_key, "")
                if name and current_value.strip():
                    save_list(name, kind, current_value)
                    st.session_state[saving_key] = False
                    st.toast(f"Saved list '{name}'")
                    st.rerun()
                else:
                    st.warning("Need both a name and values in the input.")
        with cancel_col:
            if st.button("Cancel", key=f"{key}_cancel", use_container_width=True):
                st.session_state[saving_key] = False
                st.rerun()

    # Actual input
    return st.text_input(
        label,
        placeholder=placeholder,
        key=value_key,
        label_visibility="collapsed",
        help=help,
    )


def _extract_post_id(r: dict) -> str:
    """Get a usable post ID from any result dict."""
    if r.get("id"):
        return r["id"]
    url = r.get("url", "")
    if "/comments/" in url:
        return url.split("/comments/")[1].split("/")[0]
    return url


def _bookmark_button(post: dict, source: str, idx: int) -> None:
    """Render a small Save-to-queue / In-queue indicator below a post card."""
    post_id = _extract_post_id(post)
    if not post_id:
        return
    bm_key = f"bm_{source}_{idx}"
    if is_bookmarked(post_id):
        st.markdown(
            '<div style="font-size:0.8rem; color:var(--text-3); margin: -0.3rem 0 0.6rem 0;">In your queue</div>',
            unsafe_allow_html=True,
        )
    else:
        if st.button("Save to queue", key=bm_key):
            add_bookmark({**post, "id": post_id}, source=source)
            st.toast("Saved to queue")
            st.rerun()


def _render_scored_post(p: dict) -> None:
    """Render one freshly scored post as an expander with score bars."""
    s = p.get("ai_scores", {})
    composite = s.get("composite_score", 0)
    header = f"{composite:.1f}/10  ·  r/{p['subreddit']}  —  {p['title'][:80]}"

    with st.expander(header):
        st.markdown(
            f"""
            <div class="rs-score-header">
              {ui.score_pill(composite)}
              {ui.pill(s.get('category', '—'), 'muted')}
            </div>
            """,
            unsafe_allow_html=True,
        )

        bars = "".join([
            ui.score_bar_row("Relevance", s.get("relevance", 0)),
            ui.score_bar_row("Pain clarity", s.get("pain_clarity", 0)),
            ui.score_bar_row("Emotional intensity", s.get("emotional_intensity", 0)),
            ui.score_bar_row("Implementability", s.get("implementability", 0)),
            ui.score_bar_row("Technical depth", s.get("technical_depth", 0)),
        ])
        st.markdown(f'<div style="margin: 0.5rem 0 1rem 0;">{bars}</div>', unsafe_allow_html=True)

        if s.get("summary"):
            st.markdown(f"**Summary.** {s['summary']}")
        st.markdown(f"[Open on Reddit →]({p['url']})")


# --- Sidebar: brand, connection, nav ---
try:
    reddit = get_reddit()
    user = reddit.user.me()
except Exception as e:
    st.error(f"Reddit connection failed: {e}")
    st.stop()

with st.sidebar:
    ui.brand_mark()
    ui.connection_status(user.name)
    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        [
            "🏠  Home",
            "🔍  Discover",
            "📡  Scan",
            "💡  Opportunities",
            "🔥  Trending",
            "🧠  AI Scoring",
            "📌  Queue",
            "📊  Karma",
            "📋  Lists",
        ],
        label_visibility="collapsed",
        key="nav",
    )
    # Strip emoji prefix for page matching
    page = page.split("  ", 1)[-1] if "  " in page else page


# ===== Home =====
if page == "Home":
    ui.hero(
        eyebrow="RedditScout",
        title="Dashboard",
        subtitle="Your Reddit growth at a glance.",
    )

    # --- Onboarding ---
    progress = get_onboarding_progress()
    if not progress["any_activity"]:
        ui.welcome_screen()
    else:
        if progress["completed"] < progress["total"]:
            ui.progress_tracker(progress)

    # --- Stat cards ---
    stats = get_stats()
    bm_counts = count_bookmarks()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("In queue", bm_counts.get("saved", 0))
    with c2:
        st.metric("Commented", bm_counts.get("commented", 0))
    with c3:
        st.metric("Posts scored", stats["posts_scored"])
    with c4:
        st.metric("Saved lists", stats["saved_lists"])

    # --- Queue preview ---
    ui.section_title("Queue — next up")
    queue = get_bookmarks(status="saved", limit=5)
    if queue:
        for bm in queue:
            ui.post_card(
                subreddit=bm["subreddit"],
                title=bm["title"],
                url=bm["url"],
                score=bm["score"],
                comments=bm["num_comments"],
                extra_pills=[ui.pill(bm.get("source", ""), "muted")] if bm.get("source") else [],
            )
    else:
        ui.empty_state(
            "Queue is empty",
            "Scan for posts, then hit 'Save to queue' on ones you want to act on.",
        )

    # --- Top scored ---
    ui.section_title("Top AI-scored posts")
    top_scored = get_scored_posts(min_score=5, limit=5)
    if top_scored:
        for p in top_scored:
            composite = p.get("composite_score", 0)
            ui.post_card(
                subreddit=p["subreddit"],
                title=p["title"],
                url=p.get("url") or p.get("permalink") or f"https://reddit.com/r/{p['subreddit']}",
                extra_pills=[
                    ui.pill(f"{composite:.1f}/10", "muted"),
                    ui.pill(p.get("category", ""), "muted"),
                ],
            )
    else:
        ui.empty_state("No scored posts yet", "Use the AI Scoring tab to analyze posts.")

    # --- Karma trend ---
    karma_history = get_karma_history(limit=30)
    if karma_history:
        ui.section_title("Karma trend")
        import pandas as pd
        df = pd.DataFrame(karma_history)
        df = df.rename(columns={
            "snapshot_at": "Date",
            "total_karma": "Total",
            "comment_karma": "Comments",
            "post_karma": "Posts",
        })
        df = df.set_index("Date")
        st.area_chart(df[["Total"]], color=["#FF4500"])


# ===== Discover Subreddits =====
elif page == "Discover":
    ui.hero(
        eyebrow="Discover",
        title="Find the right subreddits",
        subtitle="Search Reddit for communities relevant to a topic, ranked by size and activity.",
    )

    ui.tip("<strong>How it works:</strong> Enter a topic and we'll search Reddit for matching communities, ranked by subscribers and daily activity. Save the ones you like as a list to reuse on other tabs.")

    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input(
            "Topic",
            placeholder="e.g. ai tools, saas, side projects",
            key="discover_topic",
        )
    with col2:
        d_limit = st.number_input(
            "Max results", min_value=5, max_value=100, value=25, key="discover_limit"
        )

    run_discover = st.button("Discover", type="primary", key="discover_btn")

    if run_discover and topic:
        with st.spinner(f'Searching Reddit for "{topic}"…'):
            results = discover_subreddits(reddit, topic, limit=d_limit)

        if results:
            save_discovered_subreddits(results, topic)
            ui.section_title(f"{len(results)} subreddit{'s' if len(results) != 1 else ''} found")

            st.dataframe(
                [
                    {
                        "Subreddit": r["url"],
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
                column_config={
                    "Subreddit": st.column_config.LinkColumn(
                        "Subreddit",
                        help="Click to open on Reddit",
                        display_text=r"r/[^/]+",
                    ),
                },
            )

            path = export_discovery_results(results)
            st.caption(f"Exported to `{path}`")
        else:
            ui.empty_state("No subreddits found", f'No communities matched "{topic}". Try a broader term.')


# ===== Keyword Scanner =====
elif page == "Scan":
    ui.hero(
        eyebrow="Scan",
        title="Keyword scanner",
        subtitle="Pull recent posts matching your keywords across a set of subreddits.",
    )

    ui.tip("<strong>How it works:</strong> Enter keywords and subreddits (or load from a saved list), then hit Scan. We pull recent posts and show matches. Save interesting ones to your Queue.")

    keywords = list_input(
        label="Keywords",
        placeholder="micro saas, side project, ai tools",
        kind="keywords",
        key="scan_keywords",
        help="Comma-separated list",
    )
    subreddits = list_input(
        label="Subreddits",
        placeholder="SaaS, indiehackers, startups",
        kind="subreddits",
        key="scan_subs",
        help="Comma-separated list",
    )

    col1, _ = st.columns([1, 2])
    with col1:
        s_limit = st.number_input(
            "Posts per subreddit", min_value=10, max_value=500, value=100, key="scan_limit"
        )

    run_scan = st.button("Run scan", type="primary", key="scan_btn")

    if run_scan and keywords and subreddits:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        sub_list = [s.strip() for s in subreddits.split(",") if s.strip()]

        with st.spinner(f"Scanning {len(sub_list)} subreddit(s) for {len(kw_list)} keyword(s)…"):
            results = scan_subreddits(reddit, kw_list, sub_list, limit=s_limit)

        if results:
            save_posts(
                [
                    dict(
                        r,
                        id=r["url"].split("/comments/")[1].split("/")[0]
                        if "/comments/" in r["url"]
                        else r["url"],
                    )
                    for r in results
                ],
                source="scan",
            )
            ui.section_title(f"{len(results)} matching post{'s' if len(results) != 1 else ''}")

            for i, r in enumerate(results):
                ui.post_card(
                    subreddit=r["subreddit"],
                    title=r["title"],
                    url=r["url"],
                    age=r["age"],
                    score=r["score"],
                    comments=r["comments"],
                    extra_pills=[ui.pill(f'match: {r["matched_keyword"]}', "pattern")],
                )
                _bookmark_button(r, "scan", i)

            path = export_scan_results(results)
            st.caption(f"Exported to `{path}`")
        else:
            ui.empty_state("No matching posts", "Try broader keywords or more subreddits.")


# ===== Opportunities =====
elif page == "Opportunities":
    ui.hero(
        eyebrow="Opportunities",
        title="Find engagement openings",
        subtitle="Surface posts where people are asking for recommendations, feedback, or tools.",
    )

    ui.tip("<strong>How it works:</strong> We scan subreddits for 30+ pain-point patterns like 'looking for', 'need help with', and 'any recommendations'. Results are filtered to recent, low-comment posts — ideal for a helpful reply that gets noticed.")

    subreddits = list_input(
        label="Subreddits",
        placeholder="SaaS, startups, indiehackers",
        kind="subreddits",
        key="opp_subs",
        help="Comma-separated list",
    )
    extra_kw = list_input(
        label="Extra keywords (optional)",
        placeholder="looking for, need help with",
        kind="keywords",
        key="opp_extra",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        max_age = st.number_input(
            "Max age (hours)", min_value=1, max_value=168, value=24, key="opp_age"
        )
    with col2:
        max_comments = st.number_input(
            "Max comments", min_value=1, max_value=500, value=50, key="opp_comments"
        )
    with col3:
        o_limit = st.number_input(
            "Posts per sub", min_value=10, max_value=500, value=100, key="opp_limit"
        )

    run_opps = st.button("Find opportunities", type="primary", key="opp_btn")

    if run_opps and subreddits:
        sub_list = [s.strip() for s in subreddits.split(",") if s.strip()]
        extra = [k.strip() for k in extra_kw.split(",") if k.strip()] if extra_kw else None

        with st.spinner(f"Scanning {len(sub_list)} subreddit(s)…"):
            results = find_opportunities(
                reddit, sub_list,
                extra_keywords=extra,
                max_age_hours=max_age,
                max_comments=max_comments,
                limit=o_limit,
            )

        if results:
            fresh = [r for r in results if not r["already_engaged"]]
            engaged = [r for r in results if r["already_engaged"]]

            if fresh:
                ui.section_title(f"New subreddits · {len(fresh)}")
                for i, r in enumerate(fresh):
                    ui.post_card(
                        subreddit=r["subreddit"],
                        title=r["title"],
                        url=r["url"],
                        age=r["age"],
                        score=r["score"],
                        comments=r["comments"],
                        pattern=r["matched_pattern"],
                    )
                    _bookmark_button(r, "opp_fresh", i)

            if engaged:
                ui.section_title(f"Already engaged · {len(engaged)}")
                for i, r in enumerate(engaged):
                    ui.post_card(
                        subreddit=r["subreddit"],
                        title=r["title"],
                        url=r["url"],
                        age=r["age"],
                        score=r["score"],
                        comments=r["comments"],
                        pattern=r["matched_pattern"],
                        extra_pills=[ui.pill("engaged", "muted")],
                    )
                    _bookmark_button(r, "opp_engaged", i)

            path = export_opportunities(results)
            st.caption(f"Exported to `{path}`")
        else:
            ui.empty_state("No opportunities yet", "Try widening the age window or adding more subreddits.")


# ===== Trending =====
elif page == "Trending":
    ui.hero(
        eyebrow="Trending",
        title="High-visibility posts",
        subtitle="Posts gaining traction right now where commenting puts you in front of the most eyeballs.",
    )

    ui.tip("<strong>How it works:</strong> We pull from Reddit's Rising and Hot feeds, then rank by <strong>upvote velocity</strong> (upvotes per hour) with a penalty for over-commented posts. High velocity + low competition = your comment gets seen by the most people.")

    trend_subs = list_input(
        label="Subreddits",
        placeholder="SaaS, startups, indiehackers",
        kind="subreddits",
        key="trend_subs",
        help="Comma-separated list",
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        t_max_age = st.number_input(
            "Max age (hours)", min_value=1, max_value=72, value=24, key="trend_age"
        )
    with col2:
        t_max_comments = st.number_input(
            "Max comments", min_value=10, max_value=2000, value=200, key="trend_max_comments",
            help="Higher = more competition; your comment buried easier",
        )
    with col3:
        t_min_score = st.number_input(
            "Min upvotes", min_value=10, max_value=10000, value=50, key="trend_min_score",
            help="Filters out low-noise posts",
        )
    with col4:
        t_min_ratio = st.slider(
            "Min upvote ratio", min_value=0.5, max_value=1.0, value=0.8, step=0.05,
            key="trend_min_ratio",
            help="Avoids controversial / divisive posts",
        )

    run_trending = st.button("Find trending posts", type="primary", key="trend_btn")

    if run_trending and trend_subs:
        sub_list = [s.strip() for s in trend_subs.split(",") if s.strip()]

        with st.spinner(f"Scanning {len(sub_list)} subreddit(s) for trending posts…"):
            results = find_trending(
                reddit, sub_list,
                max_age_hours=t_max_age,
                max_comments=t_max_comments,
                min_score=t_min_score,
                min_upvote_ratio=t_min_ratio,
            )

        if results:
            ui.section_title(f"{len(results)} trending post{'s' if len(results) != 1 else ''} · ranked by visibility")

            for i, r in enumerate(results):
                velocity_pill = ui.pill(f"↑ {r['velocity']}/hr", "velocity")
                ratio_pill = ui.pill(f"{int(r['upvote_ratio']*100)}% upvoted", "ratio")
                ui.post_card(
                    subreddit=r["subreddit"],
                    title=r["title"],
                    url=r["url"],
                    age=r["age"],
                    score=r["score"],
                    comments=r["comments"],
                    extra_pills=[velocity_pill, ratio_pill],
                )
                _bookmark_button(r, "trend", i)
        else:
            ui.empty_state(
                "No trending posts match",
                "Try lowering the min upvotes or widening the age window.",
            )


# ===== AI Scoring =====
elif page == "AI Scoring":
    ui.hero(
        eyebrow="AI scoring",
        title="Pain-point analysis",
        subtitle="Score posts on relevance, pain clarity, emotional intensity, implementability, and technical depth.",
    )

    ui.tip("<strong>How it works:</strong> We fetch posts matching your criteria, then score each with AI across 5 dimensions: relevance, pain clarity, emotional intensity, implementability, and technical depth. High composite scores = strong product opportunities.")

    if not os.getenv("GEMINI_API_KEY"):
        st.warning("Add `GEMINI_API_KEY` to your `.env` file to use AI scoring.")
        st.code("GEMINI_API_KEY=AIza...", language="text")
    else:
        ai_subreddits = list_input(
            label="Subreddits to scan",
            placeholder="SaaS, startups, indiehackers",
            kind="subreddits",
            key="ai_subs",
        )
        ai_keywords = list_input(
            label="Keywords",
            placeholder="looking for, need help, pain point",
            kind="keywords",
            key="ai_keywords",
        )

        col1, col2 = st.columns(2)
        with col1:
            ai_limit = st.number_input(
                "Posts to fetch per sub",
                min_value=5, max_value=200, value=50,
                key="ai_limit",
            )
        with col2:
            max_score = st.number_input(
                "Max posts to score",
                min_value=1, max_value=50, value=10,
                key="ai_max_score",
                help="API cost control",
            )

        run_ai = st.button("Scan & score", type="primary", key="ai_btn")

        if run_ai and ai_subreddits:
            from analyzer import score_posts

            sub_list = [s.strip() for s in ai_subreddits.split(",") if s.strip()]
            kw_list = (
                [k.strip() for k in ai_keywords.split(",") if k.strip()]
                if ai_keywords
                else ["looking for", "need help", "recommendation"]
            )

            with st.spinner("Fetching posts…"):
                results = find_opportunities(
                    reddit, sub_list,
                    extra_keywords=kw_list,
                    max_age_hours=168,
                    max_comments=200,
                    limit=ai_limit,
                )

            if not results:
                ui.empty_state("No matching posts to score", "Loosen your filters and try again.")
            else:
                st.caption(f"Found {len(results)} posts · scoring top {min(max_score, len(results))} with AI.")
                to_score = results[:max_score]

                with st.spinner("Fetching post bodies…"):
                    for r in to_score:
                        try:
                            post_id = r["url"].split("/comments/")[1].split("/")[0]
                            submission = reddit.submission(id=post_id)
                            r["selftext"] = submission.selftext or ""
                            r["id"] = post_id
                        except Exception:
                            r["selftext"] = ""
                            r["id"] = ""

                progress = st.progress(0, text="Scoring posts with AI…")

                def update_progress(current, total, title):
                    progress.progress(current / total, text=f"Scoring {current}/{total}: {title[:60]}…")

                scored = score_posts(to_score, progress_callback=update_progress)
                progress.empty()

                if scored:
                    for p in scored:
                        if p.get("id"):
                            save_ai_score(p["id"], p["ai_scores"])

                    ui.section_title(f"{len(scored)} scored")
                    for p in scored:
                        _render_scored_post(p)

        # --- Previously scored ---
        ui.section_title("Previously scored")
        stored = get_scored_posts(min_score=0, limit=50)
        if stored:
            st.dataframe(
                [
                    {
                        "Score": round(r["composite_score"], 1),
                        "Subreddit": f"https://reddit.com/r/{r['subreddit']}",
                        "Title": r["title"][:80],
                        "Open": r.get("url") or r.get("permalink") or f"https://reddit.com/r/{r['subreddit']}",
                        "Category": r["category"],
                        "Summary": r["summary"],
                    }
                    for r in stored
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Subreddit": st.column_config.LinkColumn(
                        "Subreddit",
                        display_text=r"r/[^/]+",
                    ),
                    "Open": st.column_config.LinkColumn(
                        "Open",
                        display_text="Open ↗",
                        width="small",
                    ),
                },
            )
        else:
            ui.empty_state("No scored posts yet", "Run a scan above to get started.")


# ===== Queue =====
elif page == "Queue":
    ui.hero(
        eyebrow="Queue",
        title="Post queue",
        subtitle="Posts you've saved to act on. Comment, then mark as done.",
    )

    ui.tip("<strong>How it works:</strong> Posts you save from Scan, Opportunities, or Trending land here. Open a post on Reddit, leave your comment, then come back and hit <strong>Commented</strong> to track your progress. Use <strong>Skip</strong> for ones you decide to pass on.")

    bm_counts = count_bookmarks()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Saved", bm_counts.get("saved", 0))
    with c2:
        st.metric("Commented", bm_counts.get("commented", 0))
    with c3:
        st.metric("Skipped", bm_counts.get("skipped", 0))

    # --- Filter ---
    status_filter = st.radio(
        "Show",
        ["All", "Saved", "Commented", "Skipped"],
        horizontal=True,
        key="queue_filter",
    )
    filter_map = {"All": None, "Saved": "saved", "Commented": "commented", "Skipped": "skipped"}
    items = get_bookmarks(status=filter_map[status_filter], limit=200)

    if not items:
        ui.empty_state(
            "Nothing here yet" if status_filter == "All" else f"No {status_filter.lower()} posts",
            "Save posts from the Scan, Opportunities, or Trending tabs.",
        )
    else:
        for bm in items:
            ui.post_card(
                subreddit=bm["subreddit"],
                title=bm["title"],
                url=bm["url"],
                score=bm["score"],
                comments=bm["num_comments"],
                extra_pills=[
                    ui.pill(bm["status"], "velocity" if bm["status"] == "saved" else "muted"),
                    ui.pill(bm.get("source", ""), "muted") if bm.get("source") else "",
                ],
            )

            # Action buttons
            btn_cols = st.columns([1, 1, 1, 4])
            if bm["status"] == "saved":
                with btn_cols[0]:
                    if st.button("Commented", key=f"q_done_{bm['post_id']}"):
                        update_status(bm["post_id"], "commented")
                        st.toast("Marked as commented")
                        st.rerun()
                with btn_cols[1]:
                    if st.button("Skip", key=f"q_skip_{bm['post_id']}"):
                        update_status(bm["post_id"], "skipped")
                        st.toast("Skipped")
                        st.rerun()
            elif bm["status"] in ("commented", "skipped"):
                with btn_cols[0]:
                    if st.button("Move back", key=f"q_undo_{bm['post_id']}"):
                        update_status(bm["post_id"], "saved")
                        st.rerun()
            with btn_cols[2]:
                if st.button("Remove", key=f"q_rm_{bm['post_id']}"):
                    remove_bookmark(bm["post_id"])
                    st.toast("Removed")
                    st.rerun()


# ===== Karma Tracker =====
elif page == "Karma":
    ui.hero(
        eyebrow="Karma",
        title="Karma tracker",
        subtitle="Your recent karma broken down by subreddit.",
    )

    ui.tip("<strong>How it works:</strong> Fetches your recent posts and comments, then breaks down karma earned per subreddit. Use this to see which communities are giving you the most traction.")

    k_limit = st.number_input(
        "Recent items to analyze",
        min_value=50, max_value=1000, value=200,
        key="karma_limit",
    )

    run_karma = st.button("Fetch karma", type="primary", key="karma_btn")

    if run_karma:
        with st.spinner("Fetching karma breakdown…"):
            data = get_karma_breakdown(reddit, limit=k_limit)

        save_karma_snapshot(data)

        m1, m2 = st.columns(2)
        with m1:
            st.metric("Comment karma", f"{data['total_comment_karma']:,}")
        with m2:
            st.metric("Link karma", f"{data['total_link_karma']:,}")

        subs = data["subreddits"]
        if subs:
            ui.section_title(f"By subreddit · {len(subs)}")
            st.dataframe(
                [
                    {
                        "Subreddit": f"https://reddit.com/r/{s['subreddit']}",
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
                column_config={
                    "Subreddit": st.column_config.LinkColumn(
                        "Subreddit",
                        display_text=r"r/[^/]+",
                    ),
                },
            )

            path = export_karma(data)
            st.caption(f"Exported to `{path}`")
        else:
            ui.empty_state("No recent activity", "Nothing to show yet.")


# ===== Lists =====
elif page == "Lists":
    ui.hero(
        eyebrow="Lists",
        title="Saved lists",
        subtitle="Reusable sets of subreddits and keywords. Load them from any tab that takes a list.",
    )

    ui.tip("<strong>How it works:</strong> Create named lists of subreddits or keywords here, or save them directly from any input using the <strong>Save as…</strong> button. Load them on any tab via the dropdown above each input field.")

    def _render_list_kind(kind: str, display: str) -> None:
        ui.section_title(display)

        # New list form
        new_key = f"new_{kind}"
        open_key = f"new_{kind}_open"

        if st.button(f"+ New {display[:-1].lower()} list", key=f"btn_{open_key}"):
            st.session_state[open_key] = not st.session_state.get(open_key, False)

        if st.session_state.get(open_key):
            with st.container():
                n1, n2 = st.columns([1, 2])
                with n1:
                    new_name = st.text_input(
                        "Name", key=f"{new_key}_name",
                        placeholder="e.g. SaaS communities",
                    )
                with n2:
                    new_values = st.text_input(
                        "Values (comma-separated)", key=f"{new_key}_values",
                        placeholder="SaaS, indiehackers, startups" if kind == "subreddits" else "looking for, need help",
                    )
                save_col, cancel_col, _ = st.columns([1, 1, 3])
                with save_col:
                    if st.button("Create", type="primary", key=f"{new_key}_create"):
                        if new_name.strip() and new_values.strip():
                            save_list(new_name, kind, new_values)
                            st.session_state[open_key] = False
                            st.toast(f"Created '{new_name}'")
                            st.rerun()
                        else:
                            st.warning("Both fields required.")
                with cancel_col:
                    if st.button("Cancel", key=f"{new_key}_cancel_new"):
                        st.session_state[open_key] = False
                        st.rerun()

        # Existing lists
        lists = get_lists(kind)
        if not lists:
            ui.empty_state(
                f"No saved {display.lower()} yet",
                "Create one above, or hit 'Save as…' on any input.",
            )
            return

        for lst in lists:
            edit_key = f"edit_{kind}_{lst['id']}"
            with st.container():
                st.markdown(
                    f"""
                    <div class="rs-card" style="margin-bottom: 0.4rem;">
                      <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:0.4rem;">
                        <div style="font-weight:600; font-size:1rem;">{lst['name']}</div>
                        <div style="color:var(--text-3); font-size:0.78rem;">Updated {lst['updated_at'][:16]}</div>
                      </div>
                      <div style="color:var(--text-2); font-size:0.9rem; line-height:1.5;">{lst['values']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                c1, c2, c3, _ = st.columns([1, 1, 1, 4])
                with c1:
                    if st.button("Edit", key=f"{edit_key}_btn"):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                with c2:
                    confirm_key = f"confirm_delete_{kind}_{lst['id']}"
                    if st.session_state.get(confirm_key):
                        if st.button("Really?", key=f"{confirm_key}_do", type="primary"):
                            delete_list(lst["name"], kind)
                            st.session_state[confirm_key] = False
                            st.toast(f"Deleted '{lst['name']}'")
                            st.rerun()
                    else:
                        if st.button("Delete", key=f"{confirm_key}_ask"):
                            st.session_state[confirm_key] = True
                            st.rerun()

                if st.session_state.get(edit_key):
                    e1, e2 = st.columns([1, 2])
                    with e1:
                        new_name = st.text_input(
                            "Name", value=lst["name"], key=f"{edit_key}_name"
                        )
                    with e2:
                        new_values = st.text_input(
                            "Values", value=lst["values"], key=f"{edit_key}_values"
                        )
                    s_col, c_col, _ = st.columns([1, 1, 3])
                    with s_col:
                        if st.button("Save changes", type="primary", key=f"{edit_key}_save"):
                            if new_name.strip() != lst["name"]:
                                renamed = rename_list(lst["name"], new_name, kind)
                                if not renamed:
                                    st.warning(f"A list named '{new_name}' already exists.")
                                    continue
                                effective_name = new_name
                            else:
                                effective_name = lst["name"]
                            if new_values.strip() != lst["values"]:
                                save_list(effective_name, kind, new_values)
                            st.session_state[edit_key] = False
                            st.toast("Updated")
                            st.rerun()
                    with c_col:
                        if st.button("Cancel", key=f"{edit_key}_cancel"):
                            st.session_state[edit_key] = False
                            st.rerun()

    _render_list_kind("subreddits", "Subreddit lists")
    _render_list_kind("keywords", "Keyword lists")
