import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

QUERY = "all:education AND (all:AI OR all:machine learning)"
MAX_RESULTS = 10

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_papers():
    params = urllib.parse.urlencode(
        {
            "search_query": QUERY,
            "start": 0,
            "max_results": MAX_RESULTS,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"http://export.arxiv.org/api/query?{params}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def main():
    print(f"Query: {QUERY}\n")
    root = ET.fromstring(fetch_papers())
    entries = root.findall("atom:entry", ATOM_NS)

    if not entries:
        print("No papers found.")
        return

    for i, entry in enumerate(entries, 1):
        title = entry.find("atom:title", ATOM_NS).text.strip().replace("\n", " ")
        published = entry.find("atom:published", ATOM_NS).text[:10]
        summary = entry.find("atom:summary", ATOM_NS).text.strip().replace("\n", " ")
        link = next(
            l.attrib["href"]
            for l in entry.findall("atom:link", ATOM_NS)
            if l.attrib.get("rel") == "alternate"
        )
        print(f"{i}. {title}")
        print(f"   Date: {published}")
        print(f"   URL:  {link}")
        print(f"   {summary[:200]}...")
        print()


if __name__ == "__main__":
    main()
