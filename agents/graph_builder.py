import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from graph.knowledge_graph import build_graph, query_technologies_for_problem


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        keyword = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "teacher"
        results = query_technologies_for_problem(keyword)
        print(f"\nTechnologies connecting to '{keyword}':\n")
        if not results:
            print("  (no matches — try: educator, tutoring, knowledge tracing, integrity)")
            return
        for r in results[:10]:
            print(f"  Problem:    {r['problem'][:80]}")
            print(f"  Technology: {r['technology'][:80]}")
            print(f"  Weight:     {r['weight']:.1f}  Evidence: {len(r['evidence'])} items")
            print()
        return

    print("Building knowledge graph from all extracted items...")
    stats = build_graph(clear=True)
    print(f"Items processed: {stats['items']}")
    print(f"Nodes:           {stats['nodes']}")
    print(f"Edges:           {stats['edges']}")
    print("\nTest query: python agents/graph_builder.py query educator")


if __name__ == "__main__":
    main()
