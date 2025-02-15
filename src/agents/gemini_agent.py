# agents/gemini_agent.py

import os
import re
import google.generativeai as genai

def setup_gemini():
    """Initialize and return a Gemini generative model."""
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    return genai.GenerativeModel('gemini-pro')

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
        print(f"Error generating hashtags with Gemini: {str(e)}")
        words = title.split()[:3]
        return [f"#{word.lower()}" for word in words if word.isalnum()]
