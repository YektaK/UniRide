import os
import json
import platform
import sys
from datetime import datetime

# Check for numpy and numba for env logging
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tuned_parameters_db.json")

def get_environment_info():
    """Gathers hardware and library version information for academic logging."""
    info = {
        "os": platform.system(),
        "os_release": platform.release(),
        "python": sys.version.split()[0],
        "numpy": np.__version__ if HAS_NUMPY else "N/A",
        "numba": numba.__version__ if HAS_NUMBA else "N/A",
        "cpu": platform.processor() or "Unknown",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return info

def validate_config(config):
    """Basic validation of the configuration dictionary."""
    if not isinstance(config, dict):
        return False, "Config must be a dictionary."
    
    required_keys = ["problem", "algorithms"]
    for key in required_keys:
        if key not in config:
            return False, f"Missing required key: {key}"
            
    if not config.get("algorithms"):
        return False, "At least one algorithm must be specified."
        
    return True, "Success"

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
    # Add timestamp and ID (use max existing ID to avoid collisions after deletions)
    existing_ids = [item.get("id", 0) for item in db]
    entry["id"] = max(existing_ids, default=0) + 1
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
