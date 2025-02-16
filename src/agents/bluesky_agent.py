# agents/bluesky_agent.py

import requests
from bs4 import BeautifulSoup
import regex
import time
from storage import load_posted_entries  # Example import if needed
from typing import Tuple, Optional, Any, Dict

def fetch_embed_url_card(access_token: str, url: str) -> dict:
    """Create embed card for URL with proper error handling."""
    if not url:
        print("[Bluesky Agent] Warning: Empty URL provided to fetch_embed_url_card")
        return None
        
    # Ensure URL has a scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # the required fields for every embed card
    card = {
        "uri": url,
        "title": "",
        "description": "",
    }

    try:
        print(f"[Bluesky Agent] Fetching embed card for URL: {url}")
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get title and description from meta tags
        title_tag = soup.find("meta", property="og:title")
        if title_tag:
            card["title"] = title_tag["content"]
        description_tag = soup.find("meta", property="og:description")
        if description_tag:
            card["description"] = description_tag["content"]

        # Get image if available
        image_tag = soup.find("meta", property="og:image")
        if image_tag:
            img_url = image_tag["content"]
            if "://" not in img_url:
                img_url = url + img_url
            img_resp = requests.get(img_url)
            img_resp.raise_for_status()

            blob_resp = requests.post(
                "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
                headers={
                    "Content-Type": img_resp.headers.get('content-type', 'image/jpeg'),
                    "Authorization": f"Bearer {access_token}",
                },
                data=img_resp.content,
            )
            blob_resp.raise_for_status()
            card["thumb"] = blob_resp.json()["blob"]

        return {
            "$type": "app.bsky.embed.external",
            "external": card,
        }
    except Exception as e:
        print(f"[Bluesky Agent] Error fetching embed card for URL: {url}, Error: {e}")
        return None

def validate_url_accessibility(url: str) -> bool:
    """Validate if a URL is accessible."""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

def count_graphemes(text: str) -> int:
    """Count the number of graphemes in the text."""
    return len(regex.findall(r'\X', text))

def truncate_to_graphemes(text: str, limit: int) -> str:
    """Truncate text to specified number of graphemes."""
    graphemes = regex.findall(r'\X', text)
    if len(graphemes) <= limit:
        return text
    return ''.join(graphemes[:limit])

def create_post_content(entry: Dict[str, Any], hashtags: list, access_token: str) -> Tuple[Optional[str], Optional[list], Optional[Any]]:
    """
    Build clean, engaging post content for Bluesky.
    Uses proper byte indexing for facets as per Bluesky documentation.
    """
    try:
        title = entry.get('title', '')
        description = entry.get('description', '')
        link = entry.get('url', entry.get('link', ''))
        
        # Select emoji and create title line
        leading_emoji = get_emoji_for_title(title)  # Your existing emoji selection logic
        title_line = f"{leading_emoji} {title}"
        
        # Keep full description
        description = description.strip()
        
        # Clean hashtags and ensure they're properly formatted
        cleaned_hashtags = []
        for tag in hashtags[:3]:
            # Remove # and clean the tag
            clean_tag = tag.lstrip('#')
            # Remove spaces and join with camelCase
            clean_tag = ''.join(word.capitalize() for word in clean_tag.split())
            cleaned_hashtags.append(f"#{clean_tag}")
        
        # Assemble content
        content = f"{title_line}\n\n{description}\n\n{' '.join(cleaned_hashtags)}"
        
        # Create facets with proper byte indexing
        facets = []
        content_bytes = content.encode('utf-8')
        
        for tag in cleaned_hashtags:
            # Find the tag in the content
            tag_start_char = content.find(tag)
            if tag_start_char != -1:
                # Convert character position to byte position
                tag_start_byte = len(content[:tag_start_char].encode('utf-8'))
                tag_end_byte = tag_start_byte + len(tag.encode('utf-8'))
                
                facets.append({
                    'index': {
                        'byteStart': tag_start_byte,
                        'byteEnd': tag_end_byte
                    },
                    'features': [{
                        '$type': 'app.bsky.richtext.facet#tag',
                        'tag': tag.lstrip('#')
                    }]
                })
        
        # Create embed card for the URL
        embed = fetch_embed_url_card(access_token, link) if link else None
        
        print(f"[Bluesky Agent] Post content created with {len(facets)} facets")
        return content, facets, embed

    except Exception as e:
        print(f"[Bluesky Agent] Error creating post content: {str(e)}")
        return None, None, None

def get_emoji_for_title(title: str) -> str:
    """Helper function to select appropriate emoji for the title."""
    emoji_map = {
        'fasting': '⏱️',
        'aging': '⌛',
        'longevity': '🧬',
        'health': '💚',
        'nutrition': '🥗',
        'supplement': '💊',
        'news': '📰',
        'roundup': '📅',
        'cardiac': '❤️',
        'diabetes': '💉',
        'ketones': '💪',
        'exercise': '💪',
        'muscle': '💪',
    }
    
    leading_emoji = '🔬'  # default emoji
    for keyword, emoji in emoji_map.items():
        if keyword.lower() in title.lower():
            leading_emoji = emoji
            break

    return leading_emoji
