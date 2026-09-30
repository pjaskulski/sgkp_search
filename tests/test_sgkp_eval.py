"""Checks for the curated relevance benchmark and its scoring rules."""

import unittest
from pathlib import Path

from sgkp_eval import evaluate_chat, evaluate_search, read_cases, validate_cases


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    status_code = 200

    def __init__(self, data):
        self.json = data


class EvaluationTests(unittest.TestCase):
    def test_curated_targets_exist_in_source_json(self):
        report = validate_cases(read_cases(ROOT / "relevance_cases.json"),
                                read_cases(ROOT / "conversation_cases.json"), ROOT / "json")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["search_cases"], 60)
        self.assertEqual(report["chat_turns"], 9)

    def test_search_accepts_alternative_ids_and_reports_categories(self):
        class Client:
            def get(self, _path, query_string):
                self.params = query_string
                return FakeResponse({"hits": [{"ID": "another"}, {"ID": "second"}]})

        client = Client()
        report = evaluate_search([{"case_id": "ambiguous", "category": "name",
                                   "q": "Name", "expected_ids": ["first", "second"]}],
                                 client, ("text",))
        self.assertEqual(report["results"][0]["rank"], 2)
        self.assertEqual(report["by_category"]["name"]["text"]["hit_at_3"], 1)
        self.assertEqual(client.params["q"], "Name")

    def test_service_error_is_not_counted_as_missed_target(self):
        class Client:
            calls = 0

            def get(self, _path, query_string):
                self.calls += 1
                if query_string["mode"] == "hybrid":
                    response = FakeResponse({"error": "Embedding unavailable"})
                    response.status_code = 503
                    return response
                return FakeResponse({"hits": [{"ID": "target"}]})

        client = Client()
        cases = [{"case_id": str(i), "q": "Name", "expected_ids": ["target"]} for i in range(2)]
        report = evaluate_search(cases, client, ("text", "hybrid"))
        self.assertEqual(client.calls, 3)
        self.assertEqual(report["summary"]["hybrid"]["service_errors"], 2)
        self.assertEqual(report["summary"]["hybrid"]["evaluated"], 0)
        self.assertEqual(report["summary"]["text"]["hit_at_1"], 2)

    def test_chat_followup_carries_only_cited_passages(self):
        class Client:
            def __init__(self):
                self.calls = []

            def post(self, _path, json):
                self.calls.append(json)
                if len(self.calls) == 1:
                    return FakeResponse({"answer": "Tak [1].", "sources": [
                        {"entry_id": "07-03365", "passage_id": "07-03365_p0001", "nazwa": "Okuniew"}]})
                return FakeResponse({"answer": "Kościół parafialny [1].", "sources": [
                    {"entry_id": "07-03365", "passage_id": "07-03365_p0001", "nazwa": "Okuniew"}]})

        client = Client()
        report = evaluate_chat([{"case_id": "followup", "turns": [
            {"question": "Czy był w Polsce?", "required_source_groups": [["07-03365"]]},
            {"question": "A kościół?", "required_source_groups": [["07-03365"]],
             "required_terms": ["kościół"]}]}], client)
        self.assertTrue(report["results"][0]["passed"])
        self.assertEqual(client.calls[1]["history"][0]["source_ids"], ["07-03365_p0001"])
        self.assertEqual(report["summary"]["turns_passed"], 2)


if __name__ == "__main__":
    unittest.main()
