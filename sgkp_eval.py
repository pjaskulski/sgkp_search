"""Measure SGKP search ranking and, optionally, cited conversational answers."""

from __future__ import annotations

import argparse
import json
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import app as web
from sgkp_core import read_volume, source_files
from sgkp_services import ROOT, ServiceError


MODES = ("text", "hybrid", "semantic")


def read_cases(path: Path) -> list[dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path}: oczekiwano niepustej listy przypadków")
    return cases


def expected_ids(case: dict) -> list[str]:
    return case["expected_ids"] if "expected_ids" in case else [case.get("ID")]


def validate_cases(search_cases: list[dict], chat_cases: list[dict], source_dir: Path) -> dict:
    """Check gold labels against current JSON sources before measuring relevance."""
    errors, seen, required = [], set(), set()
    for case in search_cases:
        key = case.get("case_id") or case.get("ID")
        if not isinstance(key, str) or key in seen:
            errors.append(f"Powtórzony lub pusty identyfikator próby: {key!r}")
        seen.add(key)
        if case.get("category", "description") not in ("description", "name", "variant"):
            errors.append(f"{key}: nieznana kategoria")
        if not isinstance(case.get("q"), str) or not case["q"].strip():
            errors.append(f"{key}: puste zapytanie")
        ids = expected_ids(case)
        if not isinstance(ids, list) or not ids or not all(isinstance(x, str) for x in ids):
            errors.append(f"{key}: nieprawidłowe expected_ids")
            continue
        required.update(ids)
    for scenario in chat_cases:
        key = scenario.get("case_id")
        if not isinstance(key, str) or key in seen:
            errors.append(f"Powtórzony lub pusty identyfikator scenariusza: {key!r}")
        seen.add(key)
        turns = scenario.get("turns")
        if not isinstance(turns, list) or not turns:
            errors.append(f"{key}: brak pytań")
            continue
        for turn in turns:
            if not isinstance(turn.get("question"), str) or not turn["question"].strip():
                errors.append(f"{key}: puste pytanie")
            for group in turn.get("required_source_groups", []):
                if not isinstance(group, list) or not group or not all(isinstance(x, str) for x in group):
                    errors.append(f"{key}: nieprawidłowa grupa źródeł")
                else:
                    required.update(group)
    found = {}
    for path in source_files(source_dir):
        for row in read_volume(path):
            for entry in row.get("elementy") or [row]:
                if entry.get("ID") in required:
                    found[entry["ID"]] = entry
    for identifier in sorted(required - found.keys()):
        errors.append(f"Brak hasła źródłowego: {identifier}")
    for case in search_cases:
        key = case.get("case_id") or case.get("ID")
        for identifier in expected_ids(case):
            entry = found.get(identifier)
            if not entry:
                continue
            if case.get("tom") and not identifier.startswith(case["tom"] + "-"):
                errors.append(f"{key}: tom nie zgadza się z {identifier}")
            if case.get("category") == "name" and case.get("name") != entry.get("nazwa"):
                errors.append(f"{key}: nazwa nie zgadza się z {identifier}")
            if case.get("category") == "variant":
                variants = {v.get("wariant_nazwy") for v in entry.get("warianty_nazw") or [] if isinstance(v, dict)}
                if case.get("variant") not in variants:
                    errors.append(f"{key}: wariant nie należy do {identifier}")
    return {"search_cases": len(search_cases), "chat_scenarios": len(chat_cases),
            "chat_turns": sum(len(x.get("turns", [])) for x in chat_cases), "errors": errors}


def evaluate_search(cases: list[dict], client, modes: tuple[str, ...] = MODES) -> dict:
    results, mode_errors = [], {}
    for number, case in enumerate(cases, 1):
        targets = expected_ids(case)
        for mode in modes:
            base = {"case_id": case.get("case_id", case.get("ID")),
                    "category": case.get("category", "description"),
                    "q": case["q"], "expected_ids": targets, "mode": mode}
            if mode in mode_errors:
                results.append({**base, "rank": None, "top3": [], "error": mode_errors[mode]})
                continue
            params = {"q": case["q"], "mode": mode, "page_size": 20, **case.get("filters", {})}
            if case.get("tom"):
                params["tom"] = case["tom"]
            response = client.get("/api/v1/search", query_string=params)
            if response.status_code != 200:
                if response.status_code != 503:
                    raise RuntimeError(f"{base['case_id']} {mode}: "
                                       f"HTTP {response.status_code}: {response.json}")
                mode_errors[mode] = f"HTTP 503: {response.json}"
                results.append({**base, "rank": None, "top3": [], "error": mode_errors[mode]})
                continue
            identifiers = [hit["ID"] for hit in response.json["hits"]]
            rank = next((i for i, identifier in enumerate(identifiers, 1) if identifier in targets), None)
            results.append({**base, "rank": rank, "top3": identifiers[:3]})
        if number % 4 == 0:
            print(f"Sprawdzono {number}/{len(cases)} zapytań", flush=True)

    def metrics(items):
        ranks = [item["rank"] for item in items if "error" not in item]
        return {"hit_at_1": sum(rank == 1 for rank in ranks),
                "hit_at_3": sum(rank is not None and rank <= 3 for rank in ranks),
                "hit_at_10": sum(rank is not None and rank <= 10 for rank in ranks),
                "hit_at_20": sum(rank is not None for rank in ranks), "questions": len(items),
                "evaluated": len(ranks), "service_errors": len(items) - len(ranks)}

    categories = sorted({item["category"] for item in results})
    return {"summary": {mode: metrics([x for x in results if x["mode"] == mode]) for mode in modes},
            "by_category": {category: {mode: metrics([x for x in results if x["category"] == category
                                                     and x["mode"] == mode]) for mode in modes}
                            for category in categories}, "mode_errors": mode_errors, "results": results}


class LocalOnlyOpenAI:
    model = "wyłączony w próbie"

    def answer(self, *_args, **_kwargs):
        raise ServiceError("openai", message="disabled_for_evaluation")


def evaluate_chat(cases: list[dict], client, allow_openai: bool = False) -> dict:
    """Run sequential turns; history contains only the preceding cited passages."""
    results = []
    context = nullcontext() if allow_openai else patch.object(web, "OpenAIChat", LocalOnlyOpenAI)
    with context:
        for scenario in cases:
            history, turns = [], []
            for turn in scenario["turns"]:
                response = client.post("/api/v1/chat", json={"question": turn["question"],
                                                             "history": history,
                                                             "filters": scenario.get("filters", {}),
                                                             "diagnostics": True})
                if response.status_code != 200:
                    turns.append({"question": turn["question"], "passed": False,
                                  "error": f"HTTP {response.status_code}: {response.json}"})
                    break
                answer = response.json["answer"]
                sources = response.json.get("sources", [])
                cited_ids = {source["entry_id"] for source in sources}
                missing_groups = [group for group in turn.get("required_source_groups", [])
                                  if not cited_ids.intersection(group)]
                missing_terms = [term for term in turn.get("required_terms", [])
                                 if term.casefold() not in answer.casefold()]
                turns.append({"question": turn["question"], "answer": answer,
                              "cited_ids": sorted(cited_ids), "provider": response.json.get("provider"),
                              "model": response.json.get("model"),
                              "retrieved_passage_ids": response.json.get("retrieved_passage_ids", []),
                              "missing_source_groups": missing_groups,
                              "missing_terms": missing_terms,
                              "passed": not missing_groups and not missing_terms})
                history.append({"question": turn["question"],
                                "answer": answer[:web.CHAT_HISTORY_ANSWER_CHARS],
                                "source_ids": [source["passage_id"] for source in sources],
                                "source_names": [source["nazwa"] for source in sources]})
                history = history[-web.CHAT_HISTORY_TURNS:]
            results.append({"case_id": scenario["case_id"], "passed": len(turns) == len(scenario["turns"])
                            and all(item["passed"] for item in turns), "turns": turns})
            print(f"Sprawdzono scenariusz rozmowy: {scenario['case_id']}", flush=True)
    return {"summary": {"scenarios_passed": sum(x["passed"] for x in results),
                        "scenarios": len(results),
                        "turns_passed": sum(t["passed"] for x in results for t in x["turns"]),
                        "turns": sum(len(x["turns"]) for x in results)}, "results": results}


def evaluate(cases_path: Path, chat_cases_path: Path, include_chat: bool = False,
             allow_openai: bool = False, modes: tuple[str, ...] = MODES,
             validate_only: bool = False, chat_only: bool = False) -> dict:
    search_cases, chat_cases = read_cases(cases_path), read_cases(chat_cases_path)
    config = web.manifest()
    validation = validate_cases(search_cases, chat_cases, Path(config["source_dir"]))
    if validation["errors"]:
        raise ValueError("Nieprawidłowe przypadki:\n" + "\n".join(validation["errors"]))
    report = {"created_at": datetime.now(timezone.utc).isoformat(),
              "entries_index": config["entries_index"], "passages_index": config["passages_index"],
              "search_cases": str(cases_path), "chat_cases": str(chat_cases_path),
              "validation": validation}
    if validate_only:
        return report
    client = web.app.test_client()
    if not chat_only:
        report["search"] = evaluate_search(search_cases, client, modes)
    if include_chat:
        report["chat"] = evaluate_chat(chat_cases, client, allow_openai)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "relevance_cases.json")
    parser.add_argument("--chat-cases", type=Path, default=ROOT / "conversation_cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "relevance_report.json")
    parser.add_argument("--chat", action="store_true", help="Sprawdź również odpowiedzi konwersacyjne")
    parser.add_argument("--chat-only", action="store_true", help="Sprawdź wyłącznie scenariusze rozmowy")
    parser.add_argument("--allow-openai", action="store_true", help="Pozwól na płatny model awaryjny")
    parser.add_argument("--validate-only", action="store_true", help="Sprawdź przypadki bez odpytywania usług")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=MODES)
    args = parser.parse_args()
    report = evaluate(args.cases, args.chat_cases, args.chat or args.chat_only, args.allow_openai,
                      tuple(dict.fromkeys(args.modes)), args.validate_only, args.chat_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": report["validation"],
                      "search": report.get("search", {}).get("summary"),
                      "chat": report.get("chat", {}).get("summary"),
                      "report": str(args.output)}, ensure_ascii=False))
