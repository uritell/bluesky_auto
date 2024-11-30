# Bluesky Auto-Poster with AI-Generated Hashtags

Automatically post RSS feed content to Bluesky Social with AI-generated relevant hashtags using GitHub Actions.

## Features

- 🤖 Automated posting from RSS feeds to Bluesky
- 🏷️ AI-powered hashtag generation using Google's Gemini
- 🔄 Runs every hour (configurable)
- 📝 Tracks posted content to avoid duplicates
- ⚡ Easy setup using GitHub Actions

## Setup

### Prerequisites

- A Bluesky account
- A Google Cloud Platform account for Gemini API
- A GitHub account
- An RSS feed to monitor

### Installation

1. **Fork this repository**

2. **Set up environment secrets**

   Go to your repository's Settings > Environments:
   - Create a new environment named `Production`
   - Add the following secrets:
     - `BLUESKY_HANDLE`: Your Bluesky handle (without @)
     - `BLUESKY_PASSWORD`: Your Bluesky password
     - `GEMINI_API_KEY`: Your Google Gemini API key

3. **Configure RSS Feed**

   Edit `src/post_to_bluesky.py` and replace the RSS feed URL: rss_url = "https://your-rss-feed-url.com/feed"

4. **Enable GitHub Actions**

   Go to Actions tab in your repository and enable workflows.

## How It Works

1. The GitHub Action runs every 4 hours (configurable in `.github/workflows/bluesky-poster.yml`)
2. It fetches new posts from your RSS feed
3. For each new post:
   - Generates relevant hashtags using Gemini AI
   - Creates a Bluesky post with the title, link, and hashtags
   - Tracks posted content to avoid duplicates
4. Changes are committed back to the repository

## Configuration

### Modifying Schedule

Edit the cron schedule in `.github/workflows/bluesky-poster.yml`:yaml
on:
schedule:
- cron: '0 */4 * * *'  # Runs every 4 hours

### Customizing Post Format

Edit the `create_bluesky_post` function in `src/post_to_bluesky.py` to modify how posts appear.

## Files

- `src/post_to_bluesky.py`: Main script for posting to Bluesky
- `.github/workflows/bluesky-poster.yml`: GitHub Actions workflow
- `requirements.txt`: Python dependencies
- `posted_entries.json`: Tracks posted content (auto-generated)

## Dependencies

- atproto: Bluesky API client
- feedparser: RSS feed parser
- google-generativeai: Gemini AI API client

## Troubleshooting

1. **Posts not appearing?**
   - Check the Actions tab for error logs
   - Verify your Bluesky credentials
   - Ensure RSS feed URL is correct

2. **No hashtags generated?**
   - Verify your Gemini API key
   - Check API quota limits
   - Review Action logs for errors

3. **Workflow not running?**
   - Ensure GitHub Actions is enabled
   - Check if the Production environment is properly configured
   - Verify workflow file syntax

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL 3 - see the LICENSE file for details.

## Acknowledgments

- Bluesky Social for the platform
- Google for the Gemini AI API
