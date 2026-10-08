import unittest
import csv
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import app as web
import sgkp_relevance


class DiagnosticTests(unittest.TestCase):
    def test_modes_are_single_source_of_enablement(self):
        for mode, enabled in [('off', False), ('diagnostic', True), ('filter', True)]:
            with patch.dict('os.environ', {'SEARCH_RELEVANCE_MODE': mode}):
                self.assertEqual(sgkp_relevance.RelevanceDiagnostic().enabled, enabled)
        with patch.dict('os.environ', {}, clear=True):
            self.assertFalse(sgkp_relevance.RelevanceDiagnostic().enabled)
        with patch.dict('os.environ', {'SEARCH_RELEVANCE_MODE': 'invalid'}):
            with self.assertRaises(ValueError):
                sgkp_relevance.RelevanceDiagnostic()

    def test_filter_mode_refills_page_and_returns_raw_cursor(self):
        rows = [{"ID": f"01-{i:05d}", "nazwa": f"Hasło {i}", "text": "Tekst"}
                for i in range(80)]
        def search(index, payload):
            if index != 'entries':
                return {'hits': []}
            start = payload.get('offset', 0)
            return {'hits': rows[start:start + payload['limit']], 'estimatedTotalHits': 80}
        def assess(query, hit, *args, **kwargs):
            rejected = int(hit['ID'].split('-')[1]) < 20
            return {'status': 'ok', 'score': 0.1 if rejected else 0.9,
                    'would_reject': rejected}
        with patch.object(web, 'manifest', return_value={'vectors': True, 'entries_index': 'entries', 'passages_index': 'passages'}), \
             patch.object(web.Embeddings, 'embed', return_value=[[1.0]]), \
             patch.object(web.Meili, 'search', side_effect=search), \
             patch.dict('os.environ', {'SEARCH_RELEVANCE_MODE': 'filter'}), \
             patch.object(web.RelevanceDiagnostic, 'assess', side_effect=assess), \
             patch.object(web, 'write_search_csv') as export:
            result = web.search_data({'q': 'temat', 'mode': 'semantic'})
            self.assertEqual(len(result['hits']), 20)
            self.assertEqual(result['next_candidate_offset'], 40)
            self.assertFalse(any('relevance_diagnostic' in hit for hit in result['hits']))
            second = web.search_data({'q': 'temat', 'mode': 'semantic', 'page': '2', 'candidate_offset': '40'})
            self.assertEqual(second['hits'][0]['ID'], '01-00040')
            export.assert_not_called()

    def test_openrouter_decision_api_and_invalid_probability(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 200
        response.json.return_value = {'answers': {'relevant': {'noul': 0.91}}}
        with patch.dict('os.environ', {'SEARCH_RELEVANCE_BACKEND': 'openrouter',
                'OPEN_ROUTER_KEY': 'test-only'}, clear=True), \
             patch.object(sgkp_relevance.requests, 'post', return_value=response) as post:
            service = sgkp_relevance.RelevanceDiagnostic()
            self.assertEqual(service._score_openrouter({'passage': 'tekst'}, 30), 0.91)
            self.assertEqual(post.call_args.args[0], 'https://openrouter.ai/api/alpha/decisions')
            payload = post.call_args.kwargs['json']
            self.assertEqual(payload['model'], 'typesafe/jev-1.13')
            self.assertEqual(payload['questions']['relevant']['type'], 'noul')
            response.json.return_value = {'answers': {'relevant': {'noul': 2}}}
            with self.assertRaises(web.ServiceError):
                service._score_openrouter({}, 30)

    def test_tev1_remote_uses_institute_key_and_base_url(self):
        with patch.dict('os.environ', {'AI_TEST_KEY': 'test-secret'}, clear=True), \
             patch('typesafe_sdk.TypeSafeClient') as client:
            client.return_value.__enter__.return_value.system_one.return_value.nouls['relevant'].noul = 0.8
            diagnostic = sgkp_relevance.RelevanceDiagnostic()
            self.assertEqual(diagnostic._score_tev1({}, 120), 0.8)
            self.assertEqual(client.call_args.kwargs['base_url'], 'https://ai-test.ihpan.edu.pl')
            self.assertEqual(client.call_args.kwargs['api_key'], 'test-secret')
            self.assertEqual(client.call_args.kwargs['timeout'], 120)

    def test_csv_preserves_polish_text_multiline_evidence_and_score(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(sgkp_relevance, "ROOT", Path(directory)):
            path = sgkp_relevance.write_search_csv("młyny", [{
                "nazwa": "Łódź", "relevance_diagnostic": {
                    "status": "ok", "score": 0.9, "evidence": 'Tekst, "cytat"\ndrugi wiersz'}}], "tev1:4b")
            with path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.reader(stream))
            self.assertEqual(rows[1], ["młyny", "Łódź", 'Tekst, "cytat"\ndrugi wiersz', "0.9"])
            self.assertEqual(len(rows[0]), 4)

    def test_basal_probability_cache_and_request_contract(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"answers": {"relevant": {
            "probabilities": {"true": 0.8, "false": 0.2}}}}
        with patch.dict("os.environ", {"SEARCH_RELEVANCE_BACKEND": "basal",
                "SEARCH_RELEVANCE_MODEL": "basal-1.5-mini:q8_0",
                "SEARCH_RELEVANCE_URL": "http://localhost:8000"}), \
             patch.object(sgkp_relevance.requests, "post", return_value=response) as post:
            sgkp_relevance._cache.clear()
            diagnostic = sgkp_relevance.RelevanceDiagnostic()
            first = diagnostic.assess("temat", {"nazwa": "A"}, "tekst", "index")
            second = diagnostic.assess("temat", {"nazwa": "A"}, "tekst", "index")
            self.assertEqual(first["score"], 0.8)
            self.assertFalse(first["would_reject"])
            self.assertTrue(second["cache_hit"])
            self.assertEqual(post.call_count, 1)
            self.assertEqual(post.call_args.args[0], "http://localhost:8000/v1/systemone")
            self.assertEqual(post.call_args.kwargs["json"]["questions"]["relevant"]["type"], "choice")
            response.json.return_value = {"answers": {}}
            with self.assertRaises(web.ServiceError):
                diagnostic.assess("inny temat", {}, "tekst", "index")

    def run_search(self, assess, enabled=True, mode="semantic", verify="true"):
        rows = [{"ID": "01-00001", "nazwa": "A", "text": "Krótki tekst", "tom": "01", "strona": 1},
                {"ID": "01-00002", "nazwa": "B", "text": "Drugi tekst", "tom": "01", "strona": 2}]
        with patch.object(web, "manifest", return_value={"vectors": True, "entries_index": "entries", "passages_index": "passages"}), \
             patch.object(web.Embeddings, "embed", return_value=[[1.0]]), \
             patch.object(web.Meili, "search", side_effect=lambda index, body: {"hits": rows if index == "entries" else [], "estimatedTotalHits": 2}), \
             patch.dict("os.environ", {"SEARCH_RELEVANCE_MODE": "diagnostic" if enabled else "off"}), \
             patch.object(web, "write_search_csv"), \
             patch.object(web.RelevanceDiagnostic, "assess", side_effect=assess) as classifier:
            result = web.search_data({"q": "temat", "mode": mode, "verify": verify})
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
        for enabled, mode in [(False, "semantic"), (True, "text"), (True, "hybrid")]:
            result, classifier = self.run_search([], enabled=enabled, mode=mode)
            classifier.assert_not_called()
            self.assertNotIn("relevance_diagnostic", result["hits"][0])

    def test_unchecked_verification_does_not_call_model(self):
        result, classifier = self.run_search([], verify="false")
        classifier.assert_not_called()
        self.assertNotIn("relevance_diagnostic", result["hits"][0])
