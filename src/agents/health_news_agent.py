import requests
from datetime import datetime, timezone, timedelta
import time
from storage import load_posted_entries  # Assumes this returns a list or set of used article URLs

def fetch_health_news(api_key, query='health tips'):
    """
    Fetch health-related news articles from the last 30 days using NewsAPI.
    Uses date ranges and popularity sorting for better results.
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)  # Last 30 days
    
    # Format dates for NewsAPI (YYYY-MM-DD)
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    # Define trusted health news domains
    trusted_domains = "medicalnewstoday.com,healthline.com,webmd.com,health.com,everydayhealth.com"
    
    url = "https://newsapi.org/v2/everything"  # Using the 'everything' endpoint
    all_articles = []
    
    params = {
        "q": "health OR medicine OR wellness OR nutrition",
        "apiKey": api_key,
        "domains": trusted_domains,
        "language": "en",
        "from": start_date_str,
        "to": end_date_str,
        "sortBy": "popularity",
        "pageSize": 100  # Maximum articles per request
    }
    
    # Create the full URL (excluding API key for security)
    full_url = requests.Request('GET', url, params=params).prepare().url
    safe_url = full_url.replace(api_key, "API_KEY_HIDDEN")
    
    print(f"\n=== [Health News Agent] News API Request ===")
    print(f"Date Range: {start_date_str} to {end_date_str}")
    print(f"Full URL: {safe_url}")
    print("==========================================")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        articles = data.get("articles", [])
        print(f"\n=== [Health News Agent] News API Response ===")
        print(f"Total Results Available: {data.get('totalResults', 0)}")
        print(f"Articles Retrieved: {len(articles)}")
        all_articles.extend(articles)
    except Exception as e:
        print(f"[Health News Agent] Error fetching articles: {str(e)}")
        return []
    
    return all_articles

def filter_recent_articles(articles):
    """
    Filters articles to include only those published in the current month (UTC).
    Only articles with the same year and month as today will be kept.
    """
    today = datetime.now(timezone.utc).date()
    current_year = today.year
    current_month = today.month
    
    print(f"\n=== [Health News Agent] Checking Articles for {current_year}-{current_month:02d} ===")
    
    recent_articles = []
    for article in articles:
        published_str = article.get("publishedAt")
        if published_str:
            try:
                # Convert publishedAt string to a datetime object
                published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                published_date = published_dt.date()
                
                if published_date.year == current_year and published_date.month == current_month:
                    recent_articles.append(article)
                    print(f"\n✓ MATCHED ARTICLE:")
                    print(f"   Title: {article.get('title', 'No Title')}")
                    print(f"   Date: {published_date}")
                    print(f"   Time: {published_dt.strftime('%H:%M:%S UTC')}")
                    print(f"   Source: {article.get('source', {}).get('name', 'Unknown Source')}")
                    print(f"   URL: {article.get('url', 'No URL')}")
                else:
                    print(f"\n✗ SKIPPED: {article.get('title', 'No Title')} (Published: {published_date})")
            except Exception as e:
                print(f"\n! ERROR processing article: {article.get('title', 'No Title')}")
                print(f"   Error: {str(e)}")
    
    # Sort articles by published date, newest first
    recent_articles.sort(key=lambda a: a.get('publishedAt', ''), reverse=True)
    
    print(f"\n=== Summary ===")
    print(f"Total articles checked: {len(articles)}")
    print(f"Articles published in current month: {len(recent_articles)}")
    print("=====================\n")
    
    return recent_articles

def validate_article_with_gemini(article, model):
    """
    Uses Gemini to validate whether the article is truly about health advice.
    The Gemini model should respond with a single word:
      - "yes" if the article is related to genuine health advice/tips.
      - "no" otherwise.
    """
    title = article.get("title", "")
    description = article.get("description", "")
    prompt = f"""
    Evaluate the following news article and determine whether it is truly about health advice and tips rather than political commentary, drugs or medicine.
    
    Title: {title}
    Description: {description}
    
    Please respond with a single word: "yes" if it is health advice, or "no" if it is not.
    """
    try:
        response = model.generate_content(prompt)
        answer = response.text.strip().lower()
        print(f"Gemini validation for article '{title}': {answer}")
        return answer == "yes"
    except Exception as e:
        print(f"Error validating article with Gemini: {e}")
        return False

def validate_url_accessibility(url: str) -> bool:
    """
    Validate if a URL is accessible with detailed error reporting.
    Returns True if the URL is accessible, False otherwise.
    """
    print(f"[Health News Agent] Checking URL accessibility: {url}")
    
    if not url:
        print("✗ SKIPPED: Empty URL provided")
        return False
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, timeout=10, allow_redirects=True, headers=headers)
        
        # Log the response status
        print(f"[Health News Agent] URL check status code: {response.status_code}")
        
        if response.status_code == 403:
            print("✗ SKIPPED: URL Access Forbidden (403) - Site blocking access")
            return False
        elif response.status_code == 404:
            print("✗ SKIPPED: URL Not Found (404)")
            return False
        elif response.status_code == 429:
            print("✗ SKIPPED: Too Many Requests (429) - Rate limited by site")
            return False
        elif response.status_code >= 400:
            print(f"✗ SKIPPED: URL Error (Status {response.status_code})")
            return False
            
        print("✓ PASSED: URL is accessible")
        return True
        
    except requests.exceptions.SSLError:
        print("✗ SKIPPED: SSL Certificate Error")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ SKIPPED: Connection Error - Could not reach the site")
        return False
    except requests.exceptions.Timeout:
        print("✗ SKIPPED: Request Timeout - Site took too long to respond")
        return False
    except requests.exceptions.TooManyRedirects:
        print("✗ SKIPPED: Too Many Redirects")
        return False
    except Exception as e:
        print(f"✗ SKIPPED: Unexpected error checking URL: {str(e)}")
        return False

def get_latest_health_news(api_key, model, query='health'):
    """
    Fetches health news and validates each article with detailed error reporting,
    ensuring that the article was not already used.
    """
    articles = fetch_health_news(api_key, query)
    recent_articles = filter_recent_articles(articles)
    
    # Load used article URLs (should return a list or set)
    used_articles = load_posted_entries()
    
    print(f"\n=== [Health News Agent] Processing {len(recent_articles)} Recent Articles ===")
    
    for i, article in enumerate(recent_articles, 1):
        title = article.get('title', 'No Title')
        url = article.get('url', '')
        source = article.get('source', {}).get('name', 'Unknown Source')
        published = article.get('publishedAt', 'No Date')
        
        print(f"\n[Health News Agent] Checking article {i}/{len(recent_articles)}")
        print(f"Title: {title}")
        print(f"Source: {source}")
        print(f"Published: {published}")
        print(f"URL: {url}")
        
        # Skip if the article has already been used
        if url in used_articles:
            print(f"✗ SKIPPED: Article already used: {url}")
            continue
        
        try:
            # Basic validation checks
            if not url:
                print("✗ SKIPPED: Missing URL")
                continue
                
            if not title:
                print("✗ SKIPPED: Missing title")
                continue
                
            # Check for blocked domains
            blocked_domains = ['facebook.com', 'twitter.com', 'instagram.com', 'youtube.com']
            if any(domain in url.lower() for domain in blocked_domains):
                print("✗ SKIPPED: Blocked domain detected in URL")
                continue
            
            # Add delay between Gemini API calls
            if i > 1:
                print("[Health News Agent] Waiting before next Gemini API call...")
                time.sleep(2)
            
            # Validate content with Gemini
            if not validate_article_with_gemini(article, model):
                print("✗ SKIPPED: Failed Gemini content validation - Not health advice related")
                continue
            
            print("✓ PASSED: Gemini content validation")
            
            # Validate URL accessibility
            if not validate_url_accessibility(url):
                continue  # Detailed error message already printed inside the function
            
            print("✓ PASSED: URL accessibility check")
            
            print("\n=== [Health News Agent] Selected Article for Posting ===")
            print(f"Title: {title}")
            print(f"Published: {published}")
            print(f"Source: {source}")
            print(f"URL: {url}")
            print("================================\n")
            return article
            
        except Exception as e:
            print(f"✗ SKIPPED: Error processing article: {str(e)}")
            continue
    
    print("\n=== [Health News Agent] No Suitable Articles Found ===")
    print(f"Checked {len(recent_articles)} articles but none were suitable")
    print("\nCommon skip reasons:")
    print("- Missing or invalid URLs")
    print("- Blocked domains")
    print("- Inaccessible content (403, 404, etc.)")
    print("- Not health advice related")
    print("- SSL/Connection errors")
    print("- Rate limiting")
    print("- Already used article")
    print("=====================================================\n")
    return None
