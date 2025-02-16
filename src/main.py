# main.py

import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from atproto import Client
import atexit
import signal
import sys

from agents.gemini_agent import setup_gemini, generate_hashtags
from agents.bluesky_agent import create_post_content
from agents.health_news_agent import get_latest_health_news
from storage import load_posted_entries, save_posted_entry

load_dotenv()  # Load environment variables from .env

def cleanup():
    """Cleanup function to handle graceful shutdown"""
    print("[Main] Performing cleanup...")
    # Add a small delay to allow pending operations to complete
    time.sleep(0.5)

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("[Main] Received shutdown signal. Cleaning up...")
    cleanup()
    sys.exit(0)

def main():
    try:
        # Register cleanup handlers
        atexit.register(cleanup)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Initialize Gemini agent using context manager
        with setup_gemini() as model:
            print("[Main] Gemini model initialized")

            # Initialize Bluesky client and login
            client = Client()
            client.login(os.environ['BLUESKY_HANDLE'], os.environ['BLUESKY_PASSWORD'])
            print("[Main] Logged into Bluesky")
            access_token = client._session.access_jwt

            # Use the Health News agent to get today's news on health tips
            news_api_key = os.environ.get("NEWS_API_KEY")
            if not news_api_key:
                print("[Main] Missing NEWS_API_KEY environment variable.")
                return

            article = get_latest_health_news(news_api_key, model)
            if not article:
                print("[Main] No suitable health news found.")
                return

            hashtags = generate_hashtags(article['title'], article.get('description', ''), model)
            content, facets, embed = create_post_content(article, hashtags, access_token)
            
            if content is None:
                print("[Main] Skipping article due to content issues")
                return

            try:
                client.send_post(text=content, facets=facets, embed=embed)
                print(f"[Main] Posted: {article['title']}")
                # Save the URL to avoid reposting the same article
                save_posted_entry(article['url'])
                print("[Main] Updated posted_entries.json")
            except Exception as e:
                print(f"[Main] Error posting article: {article['title']}, Error: {e}")

    except Exception as e:
        print(f"[Main] Fatal error: {e}")
    finally:
        cleanup()

if __name__ == '__main__':
    main()
