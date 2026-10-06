import unittest
from unittest.mock import patch

import app as web


class DiagnosticTests(unittest.TestCase):
    def run_search(self, assess, enabled=True, mode="semantic"):
        rows = [{"ID": "01-00001", "nazwa": "A", "text": "Krótki tekst", "tom": "01", "strona": 1},
                {"ID": "01-00002", "nazwa": "B", "text": "Drugi tekst", "tom": "01", "strona": 2}]
        with patch.object(web, "manifest", return_value={"vectors": True, "entries_index": "entries", "passages_index": "passages"}), \
             patch.object(web.Embeddings, "embed", return_value=[[1.0]]), \
             patch.object(web.Meili, "search", side_effect=lambda index, body: {"hits": rows if index == "entries" else [], "estimatedTotalHits": 2}), \
             patch.dict("os.environ", {"SEARCH_RELEVANCE_DIAGNOSTIC": str(enabled).lower()}), \
             patch.object(web.RelevanceDiagnostic, "assess", side_effect=assess) as classifier:
            result = web.search_data({"q": "temat", "mode": mode})
        return result, classifier

    def test_rejected_candidate_remains_in_original_order(self):
        result, classifier = self.run_search([
            {"status": "ok", "score": 0.1, "would_reject": True},
            {"status": "ok", "score": 0.9, "would_reject": False}])
        self.assertEqual([hit["ID"] for hit in result["hits"]], ["01-00001", "01-00002"])
        self.assertTrue(result["hits"][0]["relevance_diagnostic"]["would_reject"])
        self.assertEqual(classifier.call_count, 2)

    def test_model_failure_keeps_all_hits_and_stops_repeated_requests(self):
        result, classifier = self.run_search(RuntimeError("offline"))
        self.assertEqual(len(result["hits"]), 2)
        self.assertEqual(classifier.call_count, 1)
        self.assertEqual(result["hits"][0]["relevance_diagnostic"]["status"], "unavailable")
        self.assertEqual(result["hits"][0]["relevance_diagnostic"]["error_type"], "RuntimeError")
        self.assertEqual(result["hits"][1]["relevance_diagnostic"]["status"], "skipped_after_error")

    def test_disabled_and_full_text_do_not_call_classifier(self):
        for enabled, mode in [(False, "semantic"), (True, "text")]:
            result, classifier = self.run_search([], enabled=enabled, mode=mode)
            classifier.assert_not_called()
            self.assertNotIn("relevance_diagnostic", result["hits"][0])
