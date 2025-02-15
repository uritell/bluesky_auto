import os
import feedparser
import time
from atproto import Client
from datetime import datetime, timezone
import json
import hashlib
import google.generativeai as genai
import re
from dotenv import load_dotenv
import requests
from io import BytesIO
from bs4 import BeautifulSoup

load_dotenv()

def setup_gemini():
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-pro')
    return model

def load_posted_entries():
    try:
        with open('posted_entries.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_posted_entries(posted):
    with open('posted_entries.json', 'w') as f:
        json.dump(posted, f)

def generate_hashtags_with_gemini(model, title, description):
    prompt = f"""
    Generate 5 relevant hashtags for a social media post with the following content:
    Title: {title}
    Description: {description}

    Rules for hashtags:
    1. No spaces in hashtags
    2. Use camelCase for multiple words
    3. Keep them relevant to the content
    4. No special characters except numbers
    5. Return only the hashtags, one per line, starting with #
    """

    try:
        response = model.generate_content(prompt)
        hashtags = response.text.strip().split('\n')

        # Clean and validate hashtags
        cleaned_hashtags = []
        for tag in hashtags:
            # Remove any extra # symbols and spaces
            tag = tag.strip().replace(' ', '')
            if not tag.startswith('#'):
                tag = f"#{tag}"
            # Validate hashtag format
            if re.match(r'^#[a-zA-Z0-9]+$', tag):
                cleaned_hashtags.append(tag)

        # Ensure we have at least some hashtags, even if AI fails
        if not cleaned_hashtags:
            # Fallback to basic hashtag generation
            words = title.split()[:3]
            cleaned_hashtags = [f"#{word.lower()}" for word in words if word.isalnum()]

        return cleaned_hashtags[:5]  # Return maximum 5 hashtags
    except Exception as e:
        print(f"Error generating hashtags with Gemini: {str(e)}")
        # Fallback to basic hashtag generation
        words = title.split()[:3]
        return [f"#{word.lower()}" for word in words if word.isalnum()]

def fetch_embed_url_card(access_token: str, url: str) -> dict:
    # the required fields for every embed card
    card = {
        "uri": url,
        "title": "",
        "description": "",
    }

    # fetch the HTML
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # parse out the "og:title" and "og:description" HTML meta tags
    title_tag = soup.find("meta", property="og:title")
    if title_tag:
        card["title"] = title_tag["content"]
    description_tag = soup.find("meta", property="og:description")
    if description_tag:
        card["description"] = description_tag["content"]

    # if there is an "og:image" HTML meta tag, fetch and upload that image
    image_tag = soup.find("meta", property="og:image")
    if image_tag:
        img_url = image_tag["content"]
        # naively turn a "relative" URL (just a path) into a full URL, if needed
        if "://" not in img_url:
            img_url = url + img_url
        resp = requests.get(img_url)
        resp.raise_for_status()

        blob_resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Content-Type": resp.headers.get('content-type', 'image/jpeg'),
                "Authorization": f"Bearer {access_token}",
            },
            data=resp.content,
        )
        blob_resp.raise_for_status()
        card["thumb"] = blob_resp.json()["blob"]

    return {
        "$type": "app.bsky.embed.external",
        "external": card,
    }

def create_bluesky_post(entry, hashtags, access_token):
    title = entry.get('title', '')
    link = entry.get('link', '')
    
    # Create post content with link and hashtags
    hashtag_text = ' '.join(hashtags[:3])  # Limit to 3 hashtags
    content = f"{link}\n\n{hashtag_text}"
    
    # Create facets for both the link and hashtags
    facets = []
    
    # Add link facet
    link_start = 0  # Link starts at beginning
    facets.append({
        'index': {
            'byteStart': link_start,
            'byteEnd': len(link)
        },
        'features': [{'$type': 'app.bsky.richtext.facet#link', 'uri': link}]
    })
    
    # Add hashtag facets
    for hashtag in hashtags[:3]:
        tag_start = content.find(hashtag)
        if tag_start != -1:
            facets.append({
                'index': {
                    'byteStart': tag_start,
                    'byteEnd': tag_start + len(hashtag)
                },
                'features': [{
                    '$type': 'app.bsky.richtext.facet#tag',
                    'tag': hashtag[1:]  # Remove the # symbol for the tag
                }]
            })

    # Fetch and create the embed card
    embed = fetch_embed_url_card(access_token, link)

    return content, facets, embed

def main():
    try:
        # Initialize Gemini
        model = setup_gemini()
        print("Gemini model initialized")

        # Initialize Bluesky client
        client = Client()
        client.login(os.environ['BLUESKY_HANDLE'], os.environ['BLUESKY_PASSWORD'])
        print("Successfully logged into Bluesky")

        # Get the access token
        access_token = client._session.access_jwt

        # RSS feed URL
        rss_url = "https://www.theguardian.com/uk/culture/rss"
        print(f"Fetching RSS feed from: {rss_url}")

        # Load previously posted entries
        posted_entries = load_posted_entries()
        print(f"Loaded {len(posted_entries)} previously posted entries")

        # Parse RSS feed
        feed = feedparser.parse(rss_url)
        print(f"Found {len(feed.entries)} entries in the RSS feed")

        if not feed.entries:
            print("No entries found in the RSS feed. Check if the feed URL is accessible.")
            return

        entries_posted = 0

        for entry in feed.entries:
            # Create unique identifier for entry
            entry_id = hashlib.md5(entry.link.encode()).hexdigest()

            # Skip if already posted
            if entry_id in posted_entries:
                continue

            # Generate hashtags using Gemini
            hashtags = generate_hashtags_with_gemini(
                model,
                entry.title,
                entry.get('description', '')
            )

            # Create post content with access token
            content, facets, embed = create_bluesky_post(entry, hashtags, access_token)

            try:
                # Post to Bluesky
                client.send_post(
                    text=content,
                    facets=facets,
                    embed=embed
                )
                entries_posted += 1

                # Save entry as posted
                posted_entries[entry_id] = {
                    'title': entry.title,
                    'date_posted': datetime.now(timezone.utc).isoformat(),
                    'hashtags': hashtags
                }

                print(f"Successfully posted: {entry.title}")
                print(f"Generated hashtags: {' '.join(hashtags)}")

                # Wait between posts to avoid rate limiting
                time.sleep(2)

            except Exception as e:
                print(f"Error posting {entry.title}: {str(e)}")

        # Save updated posted entries
        save_posted_entries(posted_entries)
        print(f"Finished processing. Posted {entries_posted} new entries.")

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main()

# Created/Modified files during execution:
print("posted_entries.json")
