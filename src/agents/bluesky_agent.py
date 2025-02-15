# agents/bluesky_agent.py

import requests
from bs4 import BeautifulSoup

def fetch_embed_url_card(access_token: str, url: str) -> dict:
    """Fetch metadata and upload an image (if available) for the given URL."""
    card = {
        "uri": url,
        "title": "",
        "description": "",
    }
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

def create_post_content(entry, hashtags: list, access_token: str):
    """
    Build the content text, facets, and embed for a Bluesky post.
    """
    title = entry.get('title', '')
    link = entry.get('link', '')
    hashtag_text = ' '.join(hashtags[:3])  # Limit to 3 hashtags
    content = f"{link}\n\n{hashtag_text}"

    facets = []
    # Create facet for the link
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

    # Create facets for each hashtag
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
                    'tag': hashtag[1:]  # Exclude the '#' symbol
                }]
            })

    embed = fetch_embed_url_card(access_token, link)
    return content, facets, embed
