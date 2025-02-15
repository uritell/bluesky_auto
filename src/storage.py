# storage.py

import json

def load_posted_entries(filepath='posted_entries.json') -> dict:
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_posted_entries(posted_entries: dict, filepath='posted_entries.json'):
    with open(filepath, 'w') as f:
        json.dump(posted_entries, f)
