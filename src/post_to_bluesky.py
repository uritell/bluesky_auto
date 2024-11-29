import os
import feedparser
import time
from atproto import Client
from datetime import datetime, timezone
import json
import hashlib

def load_posted_entries():
    try:
        with open('posted_entries.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_posted_entries(posted):
    with open('posted_entries.json', 'w') as f:
        json.dump(posted, f)

def extract_hashtags(title, description):
    # List of common words to exclude
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}

    # Combine title and description, split into words
    text = f"{title} {description}"
    words = text.lower().split()

    # Extract potential hashtags (words longer than 3 letters, not in common_words)
    hashtags = {word for word in words if len(word) > 3 and word not in common_words}

    # Convert to hashtag format and limit to 5 most relevant
    return [f"#{word}" for word in list(hashtags)[:5]]

def create_bluesky_post(entry, hashtags):
    title = entry.get('title', '')
    link = entry.get('link', '')

    # Create post content with title, link, and hashtags
    content = f"{title}\n\n{link}\n\n{' '.join(hashtags)}"

    # Ensure content doesn't exceed Bluesky's character limit (300)
    if len(content) > 300:
        # Truncate title if necessary
        available_space = 300 - len(link) - len(' '.join(hashtags)) - 4  # 4 for newlines
        title = title[:available_space] + '...'
        content = f"{title}\n\n{link}\n\n{' '.join(hashtags)}"

    return content

def main():
    # Initialize Bluesky client
    client = Client()
    client.login(os.environ['BLUESKY_HANDLE'], os.environ['BLUESKY_PASSWORD'])

    # RSS feed URL - replace with your desired RSS feed
    rss_url = "https://www.theguardian.com/environment/climate-crisis/rss"

    # Load previously posted entries
    posted_entries = load_posted_entries()

    # Parse RSS feed
    feed = feedparser.parse(rss_url)

    for entry in feed.entries:
        # Create unique identifier for entry
        entry_id = hashlib.md5(entry.link.encode()).hexdigest()

        # Skip if already posted
        if entry_id in posted_entries:
            continue

        # Extract hashtags
        hashtags = extract_hashtags(entry.title, entry.get('description', ''))

        # Create post content
        content = create_bluesky_post(entry, hashtags)

        try:
            # Post to Bluesky
            client.send_post(text=content)

            # Save entry as posted
            posted_entries[entry_id] = {
                'title': entry.title,
                'date_posted': datetime.now(timezone.utc).isoformat()
            }

            # Wait between posts to avoid rate limiting
            time.sleep(2)

        except Exception as e:
            print(f"Error posting {entry.title}: {str(e)}")

    # Save updated posted entries
    save_posted_entries(posted_entries)

if __name__ == "__main__":
    main()

# Created/Modified files during execution:
print("posted_entries.json")
