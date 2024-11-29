import requests
from datetime import datetime
import os

# Environment variables
BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME", "your_username")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD", "your_password")
BLUESKY_API_URL = "https://bsky.social/xrpc/com.atproto.repo.createRecord"

def get_auth_token():
    """Authenticate and get access token from Bluesky."""
    auth_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    response = requests.post(auth_url, json={"identifier": BLUESKY_USERNAME, "password": BLUESKY_PASSWORD})
    if response.status_code == 200:
        return response.json()["accessJwt"]
    else:
        raise Exception(f"Authentication failed: {response.text}")

def create_post(content):
    """Post content to Bluesky."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    post_data = {
        "collection": "app.bsky.feed.post",
        "repo": BLUESKY_USERNAME,
        "record": {
            "$type": "app.bsky.feed.post",
            "text": content,
            "createdAt": datetime.utcnow().isoformat() + "Z"
        }
    }
    response = requests.post(BLUESKY_API_URL, json=post_data, headers=headers)
    if response.status_code == 200:
        print("Post successful!")
    else:
        print(f"Failed to post: {response.text}")

if __name__ == "__main__":
    # Define your content
    content = "Hello, Bluesky! Automated post from GitHub Actions. 🌤️"
    create_post(content)
