import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRESS_PATH = ROOT / "data" / "pipeline_progress.json"

def write_progress(stage: str, current_item: str, processed: int, total: int):
    try:
        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        percent = int((processed / total) * 100) if total > 0 else 0
        status = {
            "stage": stage,
            "current_item": current_item,
            "processed": processed,
            "total": total,
            "percent": percent
        }
        PROGRESS_PATH.write_text(json.dumps(status), encoding="utf-8")
    except Exception:
        pass

def clear_progress():
    try:
        if PROGRESS_PATH.exists():
            PROGRESS_PATH.unlink()
    except Exception:
        pass
