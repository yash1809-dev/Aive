"""
run.py — Unified AIVE Discovery Operating System CLI

Usage:
    python run.py daily                    # Full 6-stage pipeline
    python run.py discover --count 30      # Discovery only
    python run.py critic                   # Critic only
    python run.py validate                 # Validation scoring
    python run.py report                   # Markdown portfolio report
    python run.py learn                    # Learning engine analysis
    python run.py ingest [--pack NAME]     # Ingest from domain packs
    python run.py serve [--port 5001]      # Launch web dashboard
    python run.py workspace list           # List workspaces
    python run.py workspace create NAME    # Create a new workspace
    python run.py workspace checkpoint ID  # Checkpoint (Time Machine)
    python run.py workspace restore ID V   # Restore workspace to version V
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def cmd_daily(args):
    print("=" * 60)
    print("AIVE Full Pipeline — Discovery → Novelty → Critic → Validation → Report → Learn")
    print("=" * 60)
    from engines.orchestrator import Orchestrator
    orc = Orchestrator()
    res = orc.run_full_pipeline(count=args.count)
    print(f"\nDiscovered:  {res['discovery']['count']}")
    print(f"Novelty OK:  {res['novelty']['passed']}  Blocked: {res['novelty']['blocked']}")
    print(f"Survived:    {res['critique']['survived']}  Killed: {res['critique']['rejected']}")
    if res["report"].get("report_path"):
        print(f"Report:      {res['report']['report_path']}")
    if res.get("learning"):
        print(f"\nLearning Recommendations:")
        for rec in res["learning"]:
            print(f"  ⚠  {rec}")
    print("=" * 60)


def cmd_discover(args):
    from engines.orchestrator import Orchestrator
    orc = Orchestrator()
    res = orc.run({"action": "discover", "count": args.count})
    print(f"Generated {res['result']['count']} candidates.")


def cmd_critic(args):
    from engines.orchestrator import Orchestrator
    orc = Orchestrator()
    res = orc.run({"action": "critique"})
    r = res["result"]
    print(f"Survived: {r['survived']}  Rejected: {r['rejected']}  Total: {r['total']}")


def cmd_validate(args):
    from engines.orchestrator import Orchestrator
    orc = Orchestrator()
    res = orc.run({"action": "validate"})
    print(f"Validated {len(res['result'].get('validated_opportunities', []))} opportunities.")


def cmd_report(args):
    from engines.report_engine import ReportEngine
    rep = ReportEngine()
    res = rep.run({"output_filename": "manual_report.md"})
    path = res.get("report_path")
    if path:
        print(f"Report saved: {path}")
    else:
        print("No surviving opportunities to report.")


def cmd_learn(args):
    from engines.learning_engine import LearningEngine
    le = LearningEngine()
    res = le.run({"action": "full_report"})
    print(f"Kill Rate: {res['rejection_analysis']['kill_rate_pct']}%")
    print(f"Survival Rate: {res['rejection_analysis']['survival_rate_pct']}%")
    print(f"Graph: {res['graph_health']['total_nodes']} nodes, {res['graph_health']['total_edges']} edges")
    print(f"Orphan Rate: {res['graph_health']['orphan_rate_pct']}%")
    for rec in res.get("overall_recommendations", []):
        print(f"  ⚠  {rec}")


def cmd_ingest(args):
    from ingest.pack_ingest import main as pack_main
    import sys
    if args.pack:
        sys.argv = ["pack_ingest.py", "--pack", args.pack]
    else:
        sys.argv = ["pack_ingest.py"]
    pack_main()


def cmd_serve(args):
    from app.main import app
    print(f"Launching AIVE Dashboard on http://localhost:{args.port}")
    # threaded=True lets Flask handle multiple simultaneous requests
    # (pipeline runs while copilot/other endpoints stay responsive)
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)


def cmd_workspace(args):
    from engines.workspace_runtime import WorkspaceRuntime
    wr = WorkspaceRuntime()

    if args.action == "list":
        res = wr.run({"action": "list"})
        print("\nWorkspaces:")
        for w in res.get("workspaces", []):
            print(f"  ID: {w['id']} | Name: {w['name']} | Status: {w['status']} | Updated: {w['updated_at']}")
        print()
    elif args.action == "create":
        res = wr.run({"action": "create", "workspace_name": args.name})
        print(f"Created Workspace: {res['name']} (ID: {res['id']})")
    elif args.action == "checkpoint":
        res = wr.run({"action": "checkpoint", "workspace_id": args.workspace_id, "created_by": "CLI"})
        print(f"Checkpoint version {res['version']} saved (History ID: {res['history_id']})")
    elif args.action == "restore":
        res = wr.run({"action": "restore", "workspace_id": args.workspace_id, "version": args.version})
        print(f"Workspace {args.workspace_id} successfully restored to version {args.version}")


def main():
    parser = argparse.ArgumentParser(
        description="AIVE Discovery Operating System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_daily = sub.add_parser("daily", help="Full 6-stage pipeline")
    p_daily.add_argument("--count", type=int, default=30)
    p_daily.set_defaults(func=cmd_daily)

    p_disc = sub.add_parser("discover", help="Discovery stage only")
    p_disc.add_argument("--count", type=int, default=30)
    p_disc.set_defaults(func=cmd_discover)

    p_crit = sub.add_parser("critic", help="Critic stage only")
    p_crit.set_defaults(func=cmd_critic)

    p_val = sub.add_parser("validate", help="Validation scoring only")
    p_val.set_defaults(func=cmd_validate)

    p_rep = sub.add_parser("report", help="Generate Markdown portfolio")
    p_rep.set_defaults(func=cmd_report)

    p_learn = sub.add_parser("learn", help="Learning Engine analysis")
    p_learn.set_defaults(func=cmd_learn)

    p_ingest = sub.add_parser("ingest", help="Pack-driven data ingestion")
    p_ingest.add_argument("--pack", type=str, default=None, help="Domain pack name (e.g. healthcare)")
    p_ingest.set_defaults(func=cmd_ingest)

    p_serve = sub.add_parser("serve", help="Launch web dashboard")
    p_serve.add_argument("--port", type=int, default=5001)
    p_serve.set_defaults(func=cmd_serve)

    p_ws = sub.add_parser("workspace", help="Workspace & Time Machine operations")
    ws_sub = p_ws.add_subparsers(dest="action", required=True)

    ws_sub.add_parser("list", help="List workspaces")
    
    p_create = ws_sub.add_parser("create", help="Create a workspace")
    p_create.add_argument("name", type=str)

    p_chk = ws_sub.add_parser("checkpoint", help="Save checkpoint (Time Machine)")
    p_chk.add_argument("workspace_id", type=str)

    p_rst = ws_sub.add_parser("restore", help="Restore to historical version")
    p_rst.add_argument("workspace_id", type=str)
    p_rst.add_argument("version", type=int)

    p_ws.set_defaults(func=cmd_workspace)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
