# RedditScout

A Python CLI + web dashboard for Reddit reconnaissance — discover subreddits, scan for keywords, find engagement opportunities, AI-score pain points, and track your karma.

## Setup

### 1. Prerequisites

- Python 3.9+
- A Reddit account
- Reddit API credentials (create an app at https://www.reddit.com/prefs/apps — choose "script" type)
- OpenAI API key (optional — needed for AI scoring)

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=RedditScout/1.0 by your_username
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# Optional — for AI scoring
OPENAI_API_KEY=sk-your-openai-key-here
```

## Usage

### Web Dashboard

```bash
python scout.py web
```

Opens a Streamlit dashboard at `http://localhost:8501` with tabs for all features.

### CLI Commands

#### Discover subreddits by topic

```bash
python scout.py discover --topic "ai tools"
python scout.py discover --topic "saas" --limit 50
```

#### Scan subreddits for keywords

```bash
python scout.py scan --keywords "micro saas,side project" --subreddits "SaaS,indiehackers,startups"
```

#### Find engagement opportunities

```bash
python scout.py opportunities --subreddits "SaaS,startups,indiehackers"
python scout.py opportunities --subreddits "SaaS,startups" --keywords "looking for,recommendations" --max-age 12
```

Finds posts where someone is asking for recommendations, feedback, or tool suggestions. Uses 30+ built-in pain-point patterns. Filters for posts that are:
- Less than 24 hours old (configurable with `--max-age`)
- Under 50 comments (configurable with `--max-comments`)
- Prioritizes subreddits you haven't engaged in yet

#### AI-score posts for pain-point potential

```bash
python scout.py analyze --subreddits "SaaS,startups" --max-score-count 10
```

Scores each post on 5 dimensions using GPT-4o-mini:
- **Relevance** — alignment with software/SaaS market
- **Pain Clarity** — how clearly a problem is articulated
- **Emotional Intensity** — urgency and frustration level
- **Implementability** — feasibility and willingness to pay
- **Technical Depth** — engineering complexity and defensibility

Results are stored in SQLite for tracking over time.

#### Track your karma

```bash
python scout.py karma
```

## Options

All commands support:
- `--no-export` — skip saving results to CSV
- `--help` — show help for any command

## Output

- **CSV exports** saved to `output/` with timestamped filenames
- **SQLite database** (`redditscout.db`) persists all results across runs

## Project Structure

```
├── scout.py           # CLI entry point (discover, scan, opportunities, analyze, karma, web)
├── dashboard.py       # Streamlit web dashboard
├── reddit_client.py   # Reddit API authentication
├── scanner.py         # Keyword scanning
├── discovery.py       # Subreddit discovery
├── opportunities.py   # Opportunity finder (30+ pain-point patterns)
├── analyzer.py        # AI scoring with GPT-4o-mini
├── database.py        # SQLite persistence layer
├── karma.py           # Karma tracker
├── exporter.py        # CSV export
├── requirements.txt   # Python dependencies
├── .env.example       # Credential template
├── .gitignore         # Git ignore rules
└── output/            # CSV exports
```
