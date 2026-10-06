"""Compare the two embedding endpoints directly, without automatic fallback."""
import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from sgkp_services import Embeddings


def compare_vectors(left, right, atol=1e-6, rtol=1e-5):
    result = {"left_dimensions": len(left), "right_dimensions": len(right)}
    if len(left) != len(right):
        return {**result, "comparable": False, "reason": "different_dimensions"}
    if not left or any(not math.isfinite(x) for x in left + right):
        raise ValueError("Empty or non-finite vectors")
    norm_left = math.sqrt(math.fsum(x * x for x in left))
    norm_right = math.sqrt(math.fsum(x * x for x in right))
    differences = [abs(a - b) for a, b in zip(left, right)]
    cosine = math.fsum(a * b for a, b in zip(left, right)) / (norm_left * norm_right) if norm_left and norm_right else None
    return {**result, "comparable": True, "exactly_equal": left == right,
            "within_tolerance": all(abs(a - b) <= atol + rtol * abs(b) for a, b in zip(left, right)),
            "atol": atol, "rtol": rtol, "left_norm": norm_left, "right_norm": norm_right,
            "cosine_similarity": max(-1.0, min(1.0, cosine)) if cosine is not None else None,
            "l2_distance": math.sqrt(math.fsum(d * d for d in differences)),
            "max_absolute_difference": max(differences),
            "mean_absolute_difference": math.fsum(differences) / len(differences)}


def request_vector(session, url, key, payload, timeout):
    started = time.monotonic()
    if not key:
        return {"status": "error", "error": "missing_api_key"}
    try:
        response = session.post(url, json=payload, headers={"Authorization": f"Bearer {key}"},
                                timeout=(10, timeout))
        if not response.ok:
            return {"status": "error", "error": "http_error", "http_status": response.status_code,
                    "seconds": time.monotonic() - started}
        body = response.json()
        items = body["data"]
        if len(items) != 1 or items[0].get("index", 0) != 0:
            raise ValueError("Unexpected number or index of vectors")
        values = items[0]["embedding"]
        if not isinstance(values, list) or not values or any(
                isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
            raise ValueError("Invalid embedding")
        return {"status": "ok", "vector": values, "seconds": time.monotonic() - started,
                "response_model": body.get("model"), "usage": body.get("usage")}
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        # Do not print exception bodies, headers, or credentials.
        return {"status": "error", "error": type(exc).__name__, "seconds": time.monotonic() - started}


def main():
    service = Embeddings()  # Loads the project's .env via sgkp_services.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="uzdowiska", help="Exact text; default: uzdowiska")
    parser.add_argument("--local-task", help="Send task to the local endpoint; omitted by default, as in the app")
    parser.add_argument("--jina-task", default=service.jina_task)
    parser.add_argument("--repeats", type=int, default=2, help="Calls per endpoint; default: 2")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output", type=Path, help="JSON report including the complete vectors")
    args = parser.parse_args()
    if args.repeats < 1 or args.timeout <= 0 or not args.query.strip():
        parser.error("Use a nonempty query, positive timeout and at least one repeat")
    local_payload = {"model": service.model, "input": [args.query]}
    if args.local_task:
        local_payload["task"] = args.local_task
    jina_payload = {"model": service.jina_model, "task": args.jina_task, "input": [args.query]}
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "query": args.query,
              "configured_dimensions": service.dimensions,
              "requests": {"local": local_payload, "jina": jina_payload},
              "runs": {"local": [], "jina": []}, "comparisons": []}
    print(f"Zapytanie (dokładny zapis): {args.query!r}", flush=True)
    print(f"Lokalnie: model={service.model}, task={args.local_task or 'pominięty'}", flush=True)
    print(f"Jina API: model={service.jina_model}, task={args.jina_task}", flush=True)
    with requests.Session() as session:
        for number in range(args.repeats):
            for name, url, key, payload in (
                    ("local", service.url, service.key, local_payload),
                    ("jina", service.jina_url, service.jina_key, jina_payload)):
                print(f"Wywołanie {name} {number + 1}/{args.repeats}…", flush=True)
                run = request_vector(session, url, key, payload, args.timeout)
                report["runs"][name].append(run)
                if run["status"] == "ok":
                    print(f"  OK: {len(run['vector'])} wymiarów, {run['seconds']:.2f} s", flush=True)
                else:
                    print(f"  Błąd: {run['error']}, HTTP={run.get('http_status', 'n/d')}", flush=True)
    for number, (local, remote) in enumerate(zip(report["runs"]["local"], report["runs"]["jina"]), 1):
        if local["status"] == remote["status"] == "ok":
            comparison = compare_vectors(local["vector"], remote["vector"])
            report["comparisons"].append({"type": "local_vs_jina", "run": number, **comparison})
            print(f"\nPorównanie usług, próba {number}:\n{json.dumps(comparison, indent=2, ensure_ascii=False)}")
    for name, runs in report["runs"].items():
        if runs[0]["status"] == "ok":
            for number, run in enumerate(runs[1:], 2):
                if run["status"] == "ok":
                    comparison = compare_vectors(runs[0]["vector"], run["vector"])
                    report["comparisons"].append({"type": "repeatability", "endpoint": name, "run": number, **comparison})
                    print(f"Powtarzalność {name}, próba 1/{number}: dokładnie identyczne={comparison.get('exactly_equal')}")
    output = args.output or Path("runtime") / ("jina_comparison_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nRaport i pełne wektory: {output}")
    if not any(item["type"] == "local_vs_jina" for item in report["comparisons"]):
        print("Nie udało się pobrać obu wektorów do porównania.", file=sys.stderr)
        return 1
    print("Ocena jednej pary wektorów nie przesądza o zgodności całego indeksu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
