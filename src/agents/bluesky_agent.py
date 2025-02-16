# agents/bluesky_agent.py

import requests
from bs4 import BeautifulSoup

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
    """
    Check if a URL is accessible by making a HEAD request.
    Returns True if the URL is accessible, False otherwise.
    """
    if not url:
        print("[Bluesky Agent] Empty URL provided")
        return False
        
    try:
        # Ensure URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        print(f"[Bluesky Agent] Validating URL accessibility: {url}")
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        # Check if status code indicates success (2xx) or redirect (3xx)
        if response.status_code < 400:
            print(f"[Bluesky Agent] URL is accessible (Status: {response.status_code})")
            return True
        else:
            print(f"[Bluesky Agent] URL returned error status: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"[Bluesky Agent] Error checking URL accessibility: {str(e)}")
        return False

def create_post_content(entry, hashtags: list, access_token: str):
    """
    Build the content text, facets, and embed for a Bluesky post.
    Returns None if the URL is not accessible.
    """
    title = entry.get('title', '')
    link = entry.get('url', entry.get('link', ''))
    
    print(f"[Bluesky Agent] Creating post for article: {title}")
    print(f"[Bluesky Agent] Using URL: {link}")
    
    # Validate URL accessibility before proceeding
    if not validate_url_accessibility(link):
        print(f"[Bluesky Agent] URL is not accessible, skipping article")
        return None, None, None
    
    hashtag_text = ' '.join(hashtags[:3])  # Limit to 3 hashtags
    content = f"{link}\n\n{hashtag_text}"

    facets = []
    if link:
        link_start = 0
        facets.append({
            'index': {
                'byteStart': link_start,
                'byteEnd': len(link)
            },
            'features': [{
                '$type': 'app.bsky.richtext.facet#link',
                'uri': link
            }]
        })

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
                    'tag': hashtag[1:]
                }]
            })

    embed = fetch_embed_url_card(access_token, link) if link else None
    
    print(f"[Bluesky Agent] Post content created with {len(facets)} facets")
    return content, facets, embed
