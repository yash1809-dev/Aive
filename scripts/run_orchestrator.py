#!/usr/bin/env python3
"""
scripts/run_orchestrator.py
============================
Thin wrapper to run the full AIVE orchestrator pipeline as a subprocess.
This ensures AIVE_ACTIVE_WORKSPACE env var is read BEFORE any module-level
DB_PATH constants are evaluated — so all engine writes go to the correct
workspace database.

Usage:
    AIVE_ACTIVE_WORKSPACE=ws_xxx python scripts/run_orchestrator.py 15
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

count = int(sys.argv[1]) if len(sys.argv) > 1 else 5

from engines.orchestrator import Orchestrator

orc = Orchestrator()
res = orc.run_full_pipeline(count=count)

# Emit a compact JSON summary to stdout so the caller can parse results
summary = {
    "discovered":  res["discovery"]["count"],
    "novelty_passed": res["novelty"]["passed"],
    "novelty_blocked": res["novelty"]["blocked"],
    "survived":    res["critique"]["survived"],
    "rejected":    res["critique"]["rejected"],
    "report_path": res["report"].get("report_path", ""),
}
print(json.dumps(summary))
