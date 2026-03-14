#!/usr/bin/env python3
"""
Normalize raw data into standard format.
Combines data from multiple sources.
"""

import json
from datetime import date
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file."""
    if not path.exists():
        return []

    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return items


def main():
    today = date.today().isoformat()
    raw_dir = Path(__file__).parent.parent / "data" / "raw" / today
    normalized_dir = Path(__file__).parent.parent / "data" / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    # Combine all news/IR documents
    all_events = []

    # Load company documents
    company_docs = load_jsonl(raw_dir / "companies.jsonl")
    for doc in company_docs:
        all_events.append({
            "id": doc.get("id", ""),
            "date": doc.get("published_at", today)[:10] if doc.get("published_at") else today,
            "companies": [doc.get("company_id", "")],
            "topics": doc.get("tags", []),
            "impact": "neutral",
            "title": doc.get("title", ""),
            "summary": doc.get("content", "")[:200] if doc.get("content") else "",
            "sources": [{
                "type": doc.get("doc_type", "news"),
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "fetchedAt": doc.get("fetched_at", ""),
                "excerpt": doc.get("content", "")[:500] if doc.get("content") else ""
            }]
        })

    # Load RSS articles
    rss_articles = load_jsonl(raw_dir / "rss.jsonl")
    for article in rss_articles:
        all_events.append({
            "id": f"rss-{hash(article.get('url', '')) % 100000}",
            "date": article.get("published_at", today)[:10] if article.get("published_at") else today,
            "companies": [],  # Will be tagged later
            "topics": ["news"],
            "impact": "neutral",
            "title": article.get("title", ""),
            "summary": article.get("summary", "")[:200] if article.get("summary") else "",
            "sources": [{
                "type": "news",
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "fetchedAt": article.get("fetched_at", ""),
                "excerpt": article.get("summary", "")[:500] if article.get("summary") else ""
            }]
        })

    # Save events
    with open(normalized_dir / "events.json", "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    print(f"Normalized {len(all_events)} events to {normalized_dir / 'events.json'}")

    # Generate companies.json for visualization
    companies_yml = Path(__file__).parent.parent / "configs" / "companies.yml"
    if companies_yml.exists():
        import yaml
        with open(companies_yml, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Convert to visualization format
        viz_companies = []
        viz_links = []

        # Position mapping for visualization
        positions = {
            "upstream": {"y": 0.12, "row_count": 0},
            "midstream": {"y": 0.50, "row_count": 0},
            "downstream": {"y": 0.88, "row_count": 0}
        }

        for company in config.get("companies", []):
            pos = company.get("position", "midstream")
            row = positions[pos]
            x = 0.1 + (row["row_count"] * 0.18)
            row["row_count"] += 1

            viz_companies.append({
                "id": company.get("id"),
                "name": company.get("name"),
                "position": pos,
                "role": company.get("role", ""),
                "x": min(x, 0.95),
                "y": row["y"]
            })

            # Add links for downstream relationships
            for downstream_id in company.get("downstream", []):
                viz_links.append({
                    "source": company.get("id"),
                    "target": downstream_id,
                    "strength": 2
                })

        viz_data = {
            "companies": viz_companies,
            "links": viz_links
        }

        with open(normalized_dir / "companies.json", "w", encoding="utf-8") as f:
            json.dump(viz_data, f, ensure_ascii=False, indent=2)

        print(f"Generated {normalized_dir / 'companies.json'}")


if __name__ == "__main__":
    main()
