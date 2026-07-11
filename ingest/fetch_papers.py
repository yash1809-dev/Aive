import json
import re
import sqlite3
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.init_db import DB_PATH, init_db

QUERY = "all:education AND (all:AI OR all:machine learning)"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _ssl_context() -> ssl.SSLContext:
    """Return an SSL context using certifi's CA bundle.

    macOS Python 3.14 ships without system CA certs configured in the
    Python framework. arXiv HTTP redirects to HTTPS, so requests fail
    with SSL_CERTIFICATE_VERIFY_FAILED. Using certifi's bundled CAs
    fixes this without disabling certificate verification.
    """
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        # Fall back to default context if certifi not installed
        ctx = ssl.create_default_context()
    return ctx


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug[:60] or "untitled"


def fetch_arxiv(query: str, start: int, max_results: int) -> bytes:
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"http://export.arxiv.org/api/query?{params}"
    with urllib.request.urlopen(url, timeout=30, context=_ssl_context()) as response:
        return response.read()


def parse_entries(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    items = []
    for entry in root.findall("atom:entry", ATOM_NS):
        arxiv_id = entry.find("atom:id", ATOM_NS).text.split("/abs/")[-1]
        title = entry.find("atom:title", ATOM_NS).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ATOM_NS).text.strip()
        published = entry.find("atom:published", ATOM_NS).text[:10]
        link = next(
            l.attrib["href"]
            for l in entry.findall("atom:link", ATOM_NS)
            if l.attrib.get("rel") == "alternate"
        )
        items.append(
            {
                "id": f"paper_{slugify(arxiv_id)}",
                "title": title,
                "source": "arxiv",
                "source_url": link,
                "type": "paper",
                "raw_text": summary,
                "year": published[:4],
                "extraction_status": "pending",
            }
        )
    return items


def save_items(items: list[dict], db_path: Path = DB_PATH) -> int:
    saved = 0
    with sqlite3.connect(db_path) as conn:
        for item in items:
            conn.execute(
                """
                INSERT OR IGNORE INTO items
                (id, title, source, source_url, type, raw_text, year, extraction_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["title"],
                    item["source"],
                    item["source_url"],
                    item["type"],
                    item["raw_text"],
                    item["year"],
                    item["extraction_status"],
                ),
            )
            if conn.total_changes:
                saved += 1
    return saved


def fetch_and_save(count: int = 20, query: str = QUERY) -> dict:
    init_db()
    xml_bytes = fetch_arxiv(query, start=0, max_results=count)
    items = parse_entries(xml_bytes)
    saved = save_items(items)

    cache_dir = ROOT / "data" / "raw" / "papers"
    cache_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    cache_file = cache_dir / f"arxiv_{stamp}.json"
    cache_file.write_text(json.dumps(items, indent=2), encoding="utf-8")

    return {"fetched": len(items), "saved": saved, "cache": str(cache_file)}


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    result = fetch_and_save(count=count)
    print(f"Fetched: {result['fetched']}")
    print(f"Saved:   {result['saved']} new papers")
    print(f"Cache:   {result['cache']}")


if __name__ == "__main__":
    main()
