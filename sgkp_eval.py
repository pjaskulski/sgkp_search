"""Measure expected SGKP entry ranks for a small curated query set."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app import app, manifest
from sgkp_services import ROOT


def evaluate(cases_path: Path) -> dict:
    cases = json.loads(cases_path.read_text())
    client = app.test_client()
    results = []
    for number, case in enumerate(cases, 1):
        for mode in ("text", "hybrid", "semantic"):
            response = client.get("/api/v1/search", query_string={
                "q": case["q"], "tom": case["tom"], "mode": mode, "page_size": 20})
            if response.status_code != 200:
                raise RuntimeError(f"{case['ID']} {mode}: HTTP {response.status_code}: {response.json}")
            identifiers = [hit["ID"] for hit in response.json["hits"]]
            rank = identifiers.index(case["ID"]) + 1 if case["ID"] in identifiers else None
            results.append({"ID": case["ID"], "tom": case["tom"], "q": case["q"], "mode": mode,
                "rank": rank, "top3": identifiers[:3]})
        if number % 4 == 0:
            print(f"Sprawdzono {number}/{len(cases)} pytań", flush=True)
    summary = {}
    for mode in ("text", "hybrid", "semantic"):
        ranks = [item["rank"] for item in results if item["mode"] == mode]
        summary[mode] = {"hit_at_10": sum(rank is not None and rank <= 10 for rank in ranks),
            "hit_at_20": sum(rank is not None for rank in ranks), "questions": len(ranks)}
    return {"created_at": datetime.now(timezone.utc).isoformat(),
        "entries_index": manifest()["entries_index"], "cases": str(cases_path),
        "summary": summary, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "relevance_cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "relevance_report.json")
    args = parser.parse_args()
    report = evaluate(args.cases)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summary": report["summary"], "report": str(args.output)}, ensure_ascii=False))
