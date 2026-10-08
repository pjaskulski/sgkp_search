"""Decision-model filtering without external network calls."""
import unittest
from unittest.mock import Mock, patch

import app as web


def passage(i):
    return {"passage_id": f"entry{i}_p0001", "entry_id": f"entry{i}",
            "nazwa": f"Name {i}", "text": f"Source text {i}", "archeo": ["finds"]}


class ChatRelevanceTests(unittest.TestCase):
    def engine(self):
        engine = Mock(budget=60, timeout=15, model="decision-test")
        engine.assess.side_effect = lambda q, source, *args, **kwargs: {
            "score": 0.1 if source["entry_id"] == "entry0" else 0.9,
            "would_reject": source["entry_id"] == "entry0"}
        return engine

    def test_rejected_candidates_do_not_count_towards_source_limit(self):
        engine = self.engine()
        with patch.object(web, "RelevanceDiagnostic", return_value=engine), \
             patch.object(web, "preliminary_chat_answer") as qwen:
            verifier = web.ChatPassageVerifier("Polskie pytanie", [], "passages", True)
            selected = verifier.select([passage(i) for i in range(4)], 2)
            self.assertEqual([s["entry_id"] for s in selected], ["entry1", "entry2"])
            self.assertEqual(engine.assess.call_count, 3)
            verifier.select([passage(1)])
            self.assertEqual(engine.assess.call_count, 3)
            qwen.assert_not_called()
        self.assertEqual(engine.assess.call_args.args[0], "Polskie pytanie")
        self.assertIn("archeo", engine.assess.call_args.args[1])

    def test_disabled_does_not_call_any_selection_model(self):
        with patch.object(web, "RelevanceDiagnostic") as engine, \
             patch.object(web, "preliminary_chat_answer") as qwen:
            verifier = web.ChatPassageVerifier("Pytanie", [], "passages", False)
            self.assertEqual(verifier.select([passage(0)]), [passage(0)])
            engine.assert_not_called()
            qwen.assert_not_called()

    def test_followup_includes_history(self):
        engine = self.engine()
        history = [{"question": "Co o Name 1?", "answer": "Informacja o Name 1.",
                    "source_ids": [], "source_names": ["Name 1"]}]
        with patch.object(web, "RelevanceDiagnostic", return_value=engine):
            verifier = web.ChatPassageVerifier("A jego zabytki?", history, "passages", True)
            verifier.select([passage(1)])
        query = engine.assess.call_args.args[0]
        self.assertIn("Name 1", query)
        self.assertIn("A jego zabytki?", query)

    def test_timeout_keeps_only_verified_sources(self):
        engine = self.engine()
        with patch.object(web, "RelevanceDiagnostic", return_value=engine), \
             patch.object(web.time, "monotonic", side_effect=[0, 0, 61]):
            verifier = web.ChatPassageVerifier("Pytanie", [], "passages", True)
            selected = verifier.select([passage(1), passage(2)])
        self.assertEqual(selected, [passage(1)])
        self.assertTrue(verifier.incomplete)
        self.assertEqual(engine.assess.call_count, 1)

    def test_service_failure_is_not_an_empty_selection(self):
        engine = self.engine()
        engine.assess.side_effect = RuntimeError("unavailable")
        with patch.object(web, "RelevanceDiagnostic", return_value=engine):
            verifier = web.ChatPassageVerifier("Pytanie", [], "passages", True)
            with self.assertRaises(web.ServiceError):
                verifier.select([passage(1)])

    def test_api_rejects_string_verify(self):
        with patch.object(web, "manifest", return_value={"passages_index": "passages"}):
            response = web.app.test_client().post("/api/v1/chat", json={
                "question": "Pytanie", "verify": "false"})
        self.assertEqual(response.status_code, 400)
