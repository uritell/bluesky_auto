# storage.py

import json
import os

POSTED_ENTRIES_FILE = 'posted_entries.json'

def load_posted_entries(filepath=POSTED_ENTRIES_FILE):
    """
    Load the list of posted article URLs.
    Returns a set for efficient membership testing.
    """
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
            print(f"[storage] Loaded {len(data)} entries from {filepath}")
            return set(data)
        except json.JSONDecodeError as e:
            print(f"[storage] JSON decode error in {filepath}: {e}")
            return set()
    else:
        print(f"[storage] No {filepath} file found. Starting fresh.")
        return set()

def save_posted_entry(new_url, filepath=POSTED_ENTRIES_FILE):
    """
    Add a new URL to the set and update the JSON file.
    """
    entries = load_posted_entries(filepath)
    if new_url in entries:
        print(f"[storage] URL already exists in {filepath}: {new_url}")
        return
    entries.add(new_url)
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(list(entries), file, indent=4)
        print(f"[storage] Successfully updated {filepath} with URL: {new_url}")
    except Exception as e:
        print(f"[storage] Error updating {filepath}: {e}")
