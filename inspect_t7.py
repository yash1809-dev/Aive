"""
Inspect the T7 and T9 full details from validation.db for run 15e0da19966c.
"""
import json
import sqlite3
from pathlib import Path

DB = Path("data/validation.db")
run_id = "15e0da19966c"

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT test_id, passed, scores_json, details_json FROM test_results WHERE run_id=?",
    (run_id,)
).fetchall()
conn.close()

for row in rows:
    if row["test_id"] not in ("T7", "T9"):
        continue

    print(f"\n{'='*60}")
    print(f"Test: {row['test_id']}  |  passed={row['passed']}")
    scores = json.loads(row["scores_json"])
    print(f"Scores: {scores}")

    details = json.loads(row["details_json"])

    if row["test_id"] == "T7":
        edge_audits = details.get("edge_audits", [])
        invalid = [e for e in edge_audits if not e.get("is_valid")]
        valid   = [e for e in edge_audits if e.get("is_valid")]
        print(f"Audited: {details.get('total_audited')}  Valid: {details.get('valid_count')}  Errors: {details.get('error_count')}")
        print(f"\n--- 10 INVALID edges ---")
        for e in invalid[:10]:
            print(f"  {e.get('relationship', '')[:100]}")
            print(f"  {e.get('reasoning', '')[:130]}")
        print(f"\n--- 5 VALID edges ---")
        for e in valid[:5]:
            print(f"  {e.get('relationship', '')[:100]}")

    if row["test_id"] == "T9":
        verdicts = details.get("commercialization_verdicts", [])
        print(f"\nOpportunities evaluated: {details.get('evaluated')}")
        print(f"buyer_hits={details.get('buyer_hits')}  chain_hits={details.get('chain_hits')}  competitor_hits={details.get('competitor_hits')}")
        print(f"\n--- 3 sample opportunities (adoption chain detail) ---")
        for v in verdicts[:3]:
            chain = v.get("adoption_chain", {})
            print(f"\n  Title: {v.get('title','')[:70]}")
            print(f"  model complete flag: {chain.get('complete')}")
            print(f"  user:           {chain.get('user','')[:80]}")
            print(f"  influencer:     {chain.get('influencer','')[:80]}")
            print(f"  decision_maker: {chain.get('decision_maker','')[:80]}")
            print(f"  buyer:          {chain.get('buyer','')[:80]}")
