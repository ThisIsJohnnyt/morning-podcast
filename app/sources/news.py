"""Headlines per topic from Google News RSS."""
from urllib.parse import quote_plus

import feedparser
import httpx


# Broad topics map to Google News' curated section feeds; anything else becomes a search.
SECTIONS = {
    "top": "", "world": "WORLD", "nation": "NATION", "us": "NATION", "business": "BUSINESS",
    "technology": "TECHNOLOGY", "tech": "TECHNOLOGY", "entertainment": "ENTERTAINMENT",
    "sports": "SPORTS", "science": "SCIENCE", "health": "HEALTH",
}
LOCALE = "hl=en-US&gl=US&ceid=US:en"


def _feed_url(topic: str) -> str:
    key = topic.strip().lower()
    if key in SECTIONS:
        section = SECTIONS[key]
        if not section:
            return f"https://news.google.com/rss?{LOCALE}"
        return f"https://news.google.com/rss/headlines/section/topic/{section}?{LOCALE}"
    return f"https://news.google.com/rss/search?q={quote_plus(topic)}+when:1d&{LOCALE}"


def get_headlines(cfg: dict) -> dict[str, list[dict]]:
    per_topic = cfg.get("headlines_per_topic", 3)
    seen, result = set(), {}
    for topic in cfg.get("news_topics", []):
        r = httpx.get(_feed_url(topic), timeout=15, follow_redirects=True)
        r.raise_for_status()
        items = []
        for entry in feedparser.parse(r.text).entries:
            # Google News titles look like "Headline - Source"
            title, _, source = entry.title.rpartition(" - ")
            title = title or entry.title
            if title.lower() in seen:
                continue
            seen.add(title.lower())
            items.append({"title": title, "source": source})
            if len(items) >= per_topic:
                break
        result[topic] = items
    return result


if __name__ == "__main__":
    from app.config import load_config
    print(get_headlines(load_config()))
