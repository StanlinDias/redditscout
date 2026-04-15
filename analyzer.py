from __future__ import annotations

import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SCORING_PROMPT = """You are an expert at evaluating Reddit posts for business opportunity potential.

Analyze the following Reddit post and score it on these 5 dimensions (each 1-10):

1. relevance — How relevant is this to someone building/selling software tools or SaaS?
2. pain_clarity — How clearly does the post articulate a real problem or unmet need?
3. emotional_intensity — How frustrated, urgent, or passionate is the poster?
4. implementability — How feasible is it to build a solution? Is there willingness to pay?
5. technical_depth — How technically complex is the problem? (Higher = more defensible)

Also provide:
- category: One of: workflow, automation, integration, analytics, communication, pricing, support, other
- summary: A 1-sentence summary of the opportunity

POST:
Subreddit: r/{subreddit}
Title: {title}
Body: {body}
"""


def _check_api_key() -> None:
    if not GEMINI_API_KEY:
        raise SystemExit(
            "GEMINI_API_KEY not set in .env file.\n"
            "Add your Gemini API key to use AI scoring:\n"
            "  GEMINI_API_KEY=AIza..."
        )


def _parse_json(text: str) -> dict:
    """Extract and parse JSON from model response, handling code fences."""
    text = text.strip()
    # Remove markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    # Find the JSON object
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        text = brace_match.group(0)
    return json.loads(text)


def score_post(post: dict) -> dict:
    """Score a single post using Gemini Flash. Returns the scores dict."""
    _check_api_key()
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = SCORING_PROMPT.format(
        subreddit=post.get("subreddit", "unknown"),
        title=post.get("title", ""),
        body=(post.get("selftext", "") or post.get("body", ""))[:2000],
    )

    # Enforce exact JSON schema so Gemini always returns the right keys
    response_schema = {
        "type": "object",
        "properties": {
            "relevance": {"type": "number"},
            "pain_clarity": {"type": "number"},
            "emotional_intensity": {"type": "number"},
            "implementability": {"type": "number"},
            "technical_depth": {"type": "number"},
            "category": {"type": "string"},
            "summary": {"type": "string"},
        },
        "required": [
            "relevance", "pain_clarity", "emotional_intensity",
            "implementability", "technical_depth", "category", "summary",
        ],
    }

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=300,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )

    scores = _parse_json(response.text)

    # Gemini sometimes returns scores as strings — coerce to float
    numeric_keys = ["relevance", "pain_clarity", "emotional_intensity",
                    "implementability", "technical_depth"]
    for k in numeric_keys:
        if k in scores:
            try:
                scores[k] = float(scores[k])
            except (ValueError, TypeError):
                scores[k] = 0

    # Calculate composite score (weighted average)
    weights = {
        "relevance": 0.25,
        "pain_clarity": 0.25,
        "emotional_intensity": 0.15,
        "implementability": 0.25,
        "technical_depth": 0.10,
    }
    composite = sum(scores.get(k, 0) * w for k, w in weights.items())
    scores["composite_score"] = round(composite, 2)

    return scores


def score_posts(posts: list[dict], progress_callback=None) -> list[dict]:
    """Score multiple posts. Returns posts with scores attached."""
    _check_api_key()

    scored = []
    total = len(posts)

    for i, post in enumerate(posts, 1):
        if progress_callback:
            progress_callback(i, total, post.get("title", "")[:50])

        try:
            scores = score_post(post)
            post["ai_scores"] = scores
            scored.append(post)
        except Exception as exc:
            exc_str = str(exc)
            if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                print(f"  Rate limited — waiting 10s before retry...")
                time.sleep(10)
                try:
                    scores = score_post(post)
                    post["ai_scores"] = scores
                    scored.append(post)
                except Exception as retry_exc:
                    print(f"  Warning: retry failed for '{post.get('title', '')[:40]}': {retry_exc}")
            else:
                print(f"  Warning: could not score post '{post.get('title', '')[:40]}': {exc}")
            continue

    # Sort by composite score descending
    scored.sort(key=lambda p: p.get("ai_scores", {}).get("composite_score", 0), reverse=True)
    return scored


def print_scored_results(posts: list[dict]) -> None:
    """Pretty-print AI-scored results to the terminal."""
    if not posts:
        print("No scored posts to display.")
        return

    print(f"\n{'='*90}")
    print(f"  AI-Scored Opportunities — {len(posts)} post(s)")
    print(f"{'='*90}\n")

    for p in posts:
        s = p.get("ai_scores", {})
        print(f"  [{s.get('composite_score', 0):.1f}/10]  r/{p.get('subreddit', '?')}")
        print(f"  {p.get('title', 'No title')}")
        print(f"  Category: {s.get('category', '?')}  |  {s.get('summary', '')}")
        print(f"  Relevance: {s.get('relevance', 0)}  Pain: {s.get('pain_clarity', 0)}  "
              f"Emotion: {s.get('emotional_intensity', 0)}  "
              f"Implement: {s.get('implementability', 0)}  "
              f"Technical: {s.get('technical_depth', 0)}")
        print(f"  {p.get('url', '')}")
        print(f"  {'-'*80}")
