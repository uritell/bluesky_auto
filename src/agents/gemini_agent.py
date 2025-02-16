# agents/gemini_agent.py

import os
import re
import time
from datetime import datetime
import google.generativeai as genai
from contextlib import contextmanager

@contextmanager
def gemini_session():
    """Context manager for Gemini model to ensure proper cleanup"""
    try:
        genai.configure(api_key=os.environ['GEMINI_API_KEY'])
        model = genai.GenerativeModel('gemini-pro')
        print("[Gemini Agent] Model initialized successfully")
        yield model
    finally:
        print("[Gemini Agent] Cleaning up Gemini resources")
        # Force cleanup of Gemini resources
        if 'model' in locals():
            del model
        # Clear any remaining configurations
        genai.configure(api_key=None)

def setup_gemini():
    """Initialize and return a Gemini model context manager"""
    return gemini_session()

def generate_hashtags(title: str, description: str, model) -> list:
    """Generate hashtags using the Gemini model."""
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
        cleaned_hashtags = []
        for tag in hashtags:
            tag = tag.strip().replace(' ', '')
            if not tag.startswith('#'):
                tag = f"#{tag}"
            if re.match(r'^#[a-zA-Z0-9]+$', tag):
                cleaned_hashtags.append(tag)
        if not cleaned_hashtags:
            words = title.split()[:3]
            cleaned_hashtags = [f"#{word.lower()}" for word in words if word.isalnum()]
        return cleaned_hashtags[:5]  # Return up to 5 hashtags
    except Exception as e:
        print(f"[Gemini Agent] Error generating hashtags: {str(e)}")
        words = title.split()[:3]
        return [f"#{word.lower()}" for word in words if word.isalnum()]

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """
    Retry a function with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "429" in str(e):  # Rate limit error
                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                print(f"[Gemini Agent] Rate limit hit, waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
                continue
            raise  # Re-raise other exceptions
    raise Exception(f"Failed after {max_retries} retries")

def validate_article_with_gemini(article, model):
    """
    Uses Gemini to validate whether the article is truly about health advice.
    Includes retry logic for rate limits.
    """
    title = article.get("title", "")
    description = article.get("description", "")
    prompt = f"""
    Evaluate the following news article and determine whether it is truly about health advice and tips rather than political commentary.
    
    Title: {title}
    Description: {description}
    
    Please respond with a single word: "yes" if it is health advice, or "no" if it is not.
    """
    
    def generate():
        response = model.generate_content(prompt)
        answer = response.text.strip().lower()
        print(f"[Gemini Agent] Validation for article '{title}': {answer}")
        return answer == "yes"
    
    try:
        return retry_with_backoff(generate)
    except Exception as e:
        print(f"[Gemini Agent] Error validating article: {e}")
        # Default to accepting the article if Gemini fails
        print(f"[Gemini Agent] Defaulting to accepting article due to API error")
        return
