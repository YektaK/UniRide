import csv
import json
import math
import os
from datetime import datetime
from typing import Dict, List, Any

def compute_gap(actual_cost: float, optimal_cost: float) -> float:
    """Compute percentage gap from optimal."""
    if optimal_cost is None or optimal_cost <= 0:
        return float('nan')
    return ((actual_cost - optimal_cost) / optimal_cost) * 100.0

def export_summary_csv(results: List[Dict[str, Any]], filepath: str) -> None:
    """Export benchmark results to a summary CSV."""
    if not results:
        return
        
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    fields = [
        "problem", "strategy", "avg_length", "avg_gap", 
        "avg_time_ms", "n_runs", "gap_type"
    ]
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in fields})

def save_metadata(filepath: str, metadata: Dict[str, Any]) -> None:
    """Save metadata JSON to disk."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

def load_metadata(filepath: str) -> Dict[str, Any]:
    """Load metadata JSON from disk."""
    if not os.path.exists(filepath):
        return {"results": {}, "last_run": None}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"results": {}, "last_run": None}
