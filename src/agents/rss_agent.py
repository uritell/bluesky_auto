# agents/rss_agent.py

import feedparser
import hashlib

def fetch_rss_feed(url: str):
    """Fetch and return the parsed RSS feed."""
    return feedparser.parse(url)

def get_new_entries(feed, posted_entries: dict) -> list:
    """Return a list of (entry_id, entry) tuples for new entries."""
    new_entries = []
    for entry in feed.entries:
        entry_id = hashlib.md5(entry.link.encode()).hexdigest()
        if entry_id not in posted_entries:
            new_entries.append((entry_id, entry))
    return new_entries
