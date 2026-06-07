"""
social_scraper.py
-----------------
Real-time social media popularity scraper for Karnataka election parties.

Sources:
  1. Google Trends (pytrends) — search interest in Karnataka (geo=IN-KA)
  2. Google News RSS + TextBlob — headline sentiment analysis

Results are cached for 15 minutes to avoid rate limits.
"""

import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ── Monkeypatch urllib3.util.retry.Retry for pytrends compatibility ──────────
try:
    import urllib3
    if hasattr(urllib3.util, "retry"):
        original_init = urllib3.util.retry.Retry.__init__
        def patched_init(self, *args, **kwargs):
            if "method_whitelist" in kwargs:
                kwargs["allowed_methods"] = kwargs.pop("method_whitelist")
            original_init(self, *args, **kwargs)
        urllib3.util.retry.Retry.__init__ = patched_init
except Exception as e:
    logger.warning(f"Could not monkeypatch urllib3: {e}")

# ── Optional dependencies ──────────────────────────────────────────────────

try:
    from pytrends.request import TrendReq
    HAS_PYTRENDS = True
except ImportError:
    HAS_PYTRENDS = False
    logger.warning("pytrends not installed. Google Trends data unavailable.")

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    logger.warning("feedparser not installed. News RSS data unavailable.")

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False
    logger.warning("textblob not installed. Sentiment analysis unavailable.")

# ── Constants ──────────────────────────────────────────────────────────────

PARTIES = ["BJP", "INC", "JD(S)", "Others"]

# Search terms per party for Google Trends (Karnataka-focused)
PARTY_SEARCH_TERMS = {
    "BJP":    "BJP Karnataka",
    "INC":    "Congress Karnataka",
    "JD(S)":  "JDS Karnataka",
    "Others": "Independent Karnataka"
}

# News RSS query terms per party
PARTY_NEWS_QUERIES = {
    "BJP":    "BJP Karnataka election",
    "INC":    "Congress INC Karnataka election",
    "JD(S)":  "JDS Janata Dal Karnataka",
    "Others": "Independent parties Karnataka election"
}

# Cache TTL in seconds (15 minutes)
CACHE_TTL = 900

# Default scores when all else fails
DEFAULT_SCORES = {"BJP": 46.0, "INC": 44.0, "JD(S)": 7.0, "Others": 3.0}

# ── Cache ──────────────────────────────────────────────────────────────────

_cache: Optional[Dict[str, Any]] = None
_cache_time: float = 0.0
_cache_lock = threading.Lock()


# ── Google Trends ──────────────────────────────────────────────────────────

def _fetch_google_trends() -> Dict[str, float]:
    """
    Fetches 7-day average search interest for Karnataka parties via pytrends.
    Returns a raw dict {party: score_0_to_100}.
    """
    if not HAS_PYTRENDS:
        return {}

    scores: Dict[str, float] = {}
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        pytrends = TrendReq(hl="en-US", tz=330, timeout=(10, 25), retries=2, backoff_factor=0.5, requests_args={'verify': False})

        # Google Trends only allows comparing ≤5 terms at a time
        # We group BJP, INC, JD(S) together, then Others separately
        terms = list(PARTY_SEARCH_TERMS.values())[:3]  # BJP, INC, JDS
        party_keys = list(PARTY_SEARCH_TERMS.keys())[:3]

        pytrends.build_payload(terms, cat=0, timeframe="now 7-d", geo="IN-KA")
        data = pytrends.interest_over_time()

        if data is not None and not data.empty:
            for i, party in enumerate(party_keys):
                col = terms[i]
                if col in data.columns:
                    scores[party] = float(data[col].mean())

        # Separately fetch Others (low-volume likely)
        pytrends.build_payload([PARTY_SEARCH_TERMS["Others"]], cat=0, timeframe="now 7-d", geo="IN-KA")
        data2 = pytrends.interest_over_time()
        if data2 is not None and not data2.empty:
            col = PARTY_SEARCH_TERMS["Others"]
            if col in data2.columns:
                scores["Others"] = float(data2[col].mean())
        else:
            scores.setdefault("Others", 5.0)

        logger.info(f"Google Trends scores fetched: {scores}")
    except Exception as e:
        logger.error(f"Google Trends fetch error: {e}")

    return scores


# ── Google News RSS Sentiment ──────────────────────────────────────────────

def _fetch_news_sentiment() -> Dict[str, Dict[str, Any]]:
    """
    Fetches recent Google News headlines for each party and runs TextBlob sentiment.
    Returns {party: {score: float 0-100, headlines: [...], polarity: float}}
    """
    if not HAS_FEEDPARSER or not HAS_TEXTBLOB:
        return {}

    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    results: Dict[str, Dict[str, Any]] = {}

    for party, query in PARTY_NEWS_QUERIES.items():
        try:
            encoded_query = query.replace(" ", "+")
            url = (
                f"https://news.google.com/rss/search?q={encoded_query}"
                f"&hl=en-IN&gl=IN&ceid=IN:en"
            )
            response = requests.get(url, verify=False, timeout=15)
            feed = feedparser.parse(response.content)
            headlines = []
            polarities = []

            for entry in feed.entries[:15]:  # top 15 headlines
                title = entry.get("title", "")
                if title:
                    blob = TextBlob(title)
                    pol = blob.sentiment.polarity  # -1 to +1
                    headlines.append({
                        "title": title,
                        "polarity": round(pol, 3),
                        "published": entry.get("published", "")
                    })
                    polarities.append(pol)

            avg_polarity = sum(polarities) / len(polarities) if polarities else 0.0
            # Map polarity (-1 to +1) → score (0 to 100), centred at 50
            sentiment_score = 50.0 + (avg_polarity * 50.0)

            results[party] = {
                "score": round(sentiment_score, 2),
                "polarity": round(avg_polarity, 3),
                "headlines": headlines[:5],  # return only top 5 to the frontend
                "article_count": len(headlines)
            }
            logger.info(f"News sentiment for {party}: polarity={avg_polarity:.3f}, score={sentiment_score:.1f}")
        except Exception as e:
            logger.error(f"News RSS error for {party}: {e}")
            results[party] = {"score": 50.0, "polarity": 0.0, "headlines": [], "article_count": 0}

    return results


# ── Composite Score ────────────────────────────────────────────────────────

def _compute_composite(
    trends: Dict[str, float],
    news: Dict[str, Dict[str, Any]]
) -> Dict[str, float]:
    """
    Combines Google Trends + news sentiment into a single 0-100 score per party.
    Formula: 60% Trends + 40% Sentiment (normalized across parties to sum to 100).
    Falls back gracefully when one source is missing.
    """
    composite: Dict[str, float] = {}

    has_trends = bool(trends)
    has_news = news and any(n.get("article_count", 0) > 0 for n in news.values())

    for party in PARTIES:
        t_score = trends.get(party, DEFAULT_SCORES.get(party, 25.0))
        n_score = news.get(party, {}).get("score", 50.0)

        if has_trends and has_news:
            score = 0.60 * t_score + 0.40 * n_score
        elif has_trends:
            score = t_score
        elif has_news:
            score = n_score
        else:
            score = DEFAULT_SCORES.get(party, 25.0)

        composite[party] = max(1.0, score)

    # Normalize so all parties sum to 100
    total = sum(composite.values())
    if total > 0:
        for p in composite:
            composite[p] = round(composite[p] / total * 100, 2)

    return composite


# ── Public API ─────────────────────────────────────────────────────────────

def get_realtime_social_scores(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Returns real-time social popularity scores with metadata.
    Results are cached for CACHE_TTL seconds.

    Returns:
    {
      "scores": {"BJP": 48.2, "INC": 42.1, "JD(S)": 7.3, "Others": 2.4},
      "trends": {"BJP": 62.0, ...},
      "news": {"BJP": {"score": 61, "polarity": 0.22, "headlines": [...], "article_count": 12}, ...},
      "sources": ["google_trends", "google_news"],
      "cached": false,
      "fetched_at": "2024-06-07T10:20:00",
      "cache_expires_in_seconds": 843
    }
    """
    global _cache, _cache_time

    with _cache_lock:
        now = time.time()
        if not force_refresh and _cache and (now - _cache_time) < CACHE_TTL:
            result = dict(_cache)
            result["cached"] = True
            result["cache_expires_in_seconds"] = int(CACHE_TTL - (now - _cache_time))
            return result

        # Fetch fresh data
        logger.info("Fetching fresh real-time social scores...")
        sources_used: List[str] = []

        trends = _fetch_google_trends()
        if trends:
            sources_used.append("google_trends")

        news = _fetch_news_sentiment()
        has_news = news and any(n.get("article_count", 0) > 0 for n in news.values())
        if has_news:
            sources_used.append("google_news")

        composite = _compute_composite(trends, news)

        # If both sources failed, use defaults
        if not trends and not has_news:
            composite = {p: v for p, v in DEFAULT_SCORES.items()}
            sources_used.append("historical_fallback")

        result = {
            "scores": composite,
            "trends": {p: round(v, 2) for p, v in trends.items()} if trends else None,
            "news": news if has_news else None,
            "sources": sources_used,
            "cached": False,
            "fetched_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "cache_expires_in_seconds": CACHE_TTL
        }

        _cache = result
        _cache_time = now

        return result


def get_scores_simple() -> Dict[str, float]:
    """Convenience function that returns just the scores dict."""
    return get_realtime_social_scores()["scores"]


# ── Standalone test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n=== Karnataka Real-Time Social Scores ===")
    result = get_realtime_social_scores(force_refresh=True)
    print(f"Fetched at: {result['fetched_at']}")
    print(f"Sources: {result['sources']}")
    print(f"Composite Scores: {result['scores']}")
    if result.get("trends"):
        print(f"Google Trends: {result['trends']}")
    if result.get("news"):
        for party, data in result["news"].items():
            print(f"\n{party} News (sentiment={data['polarity']}, score={data['score']}):")
            for h in data["headlines"][:3]:
                print(f"  - {h['title']}")
