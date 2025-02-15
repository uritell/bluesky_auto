# main.py

import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from atproto import Client

from agents.gemini_agent import setup_gemini, generate_hashtags
from agents.rss_agent import fetch_rss_feed, get_new_entries
from agents.bluesky_agent import create_post_content
from storage import load_posted_entries, save_posted_entries

load_dotenv()  # Load environment variables from .env

def main():
    # Initialize Gemini agent
    model = setup_gemini()
    print("Gemini model initialized")

    # Initialize Bluesky client and login
    client = Client()
    client.login(os.environ['BLUESKY_HANDLE'], os.environ['BLUESKY_PASSWORD'])
    print("Logged into Bluesky")
    access_token = client._session.access_jwt

    # Fetch RSS feed
    rss_url = "https://www.theguardian.com/uk/culture/rss"
    print(f"Fetching RSS feed from: {rss_url}")
    feed = fetch_rss_feed(rss_url)
    print(f"Found {len(feed.entries)} entries")

    # Load posted entries and determine new entries
    posted_entries = load_posted_entries()
    new_entries = get_new_entries(feed, posted_entries)
    print(f"{len(new_entries)} new entries to post")

    for entry_id, entry in new_entries:
        # Generate hashtags using Gemini
        hashtags = generate_hashtags(entry.title, entry.get('description', ''), model)
        # Create post content with facets and embed card
        content, facets, embed = create_post_content(entry, hashtags, access_token)
        try:
            # Send post to Bluesky
            client.send_post(text=content, facets=facets, embed=embed)
            # Mark entry as posted
            posted_entries[entry_id] = {
                'title': entry.title,
                'date_posted': datetime.now(timezone.utc).isoformat(),
                'hashtags': hashtags
            }
            print(f"Posted: {entry.title}")
            time.sleep(2)  # Wait to avoid rate limiting
        except Exception as e:
            print(f"Error posting {entry.title}: {e}")

    # Save updated posted entries list
    save_posted_entries(posted_entries)
    print("Finished processing.")

if __name__ == '__main__':
    main()
