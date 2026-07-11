"""
utils/progress.py
=================
Utility functions for pipeline progress tracking.
Writes progress info to a JSON file that the frontend polls.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
PROGRESS_FILE = ROOT / "data" / "pipeline_progress.json"


def write_progress(stage: str, current_item: str, processed: int, total: int):
    """
    Write current pipeline progress to JSON file for frontend polling.
    
    Args:
        stage: Current pipeline stage (extraction, graph_build, discovery)
        current_item: Name/title of item currently being processed
        processed: Number of items completed in this stage
        total: Total items to process in this stage
    """
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    percent = int((processed / total * 100)) if total > 0 else 0
    
    progress_data = {
        "stage": stage,
        "current_item": current_item,
        "processed": processed,
        "total": total,
        "percent": percent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress_data, f, indent=2)
    except Exception:
        pass  # Silent fail - progress tracking is non-critical


def clear_progress():
    """Clear the progress file when pipeline completes or is idle."""
    try:
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
    except Exception:
        pass
