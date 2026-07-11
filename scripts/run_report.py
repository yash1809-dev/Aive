#!/usr/bin/env python3
"""
scripts/run_report.py
======================
Thin subprocess wrapper for the AIVE Report Engine.
Ensures AIVE_ACTIVE_WORKSPACE is read BEFORE any module-level
DB_PATH constants are evaluated so the report is written from
the correct workspace database.

Usage:
    AIVE_ACTIVE_WORKSPACE=ws_xxx python scripts/run_report.py aive_portfolio_20260711.md
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

filename = sys.argv[1] if len(sys.argv) > 1 else "aive_portfolio.md"

from engines.report_engine import ReportEngine

rep = ReportEngine()
res = rep.run({"output_filename": filename})

print(json.dumps(res))
