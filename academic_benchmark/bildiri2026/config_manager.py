import os
import json
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tuned_parameters_db.json")

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_to_db(entry):
    db = load_db()
    # Add timestamp and ID
    entry["id"] = len(db) + 1
    entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.append(entry)
    
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)
    
    return entry["id"]

def get_entry(entry_id):
    db = load_db()
    for item in db:
        if item["id"] == entry_id:
            return item
    return None

def list_entries():
    return load_db()
