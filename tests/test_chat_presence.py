import json
import unittest
from unittest.mock import patch

import app as web


class ChatPresenceTests(unittest.TestCase):
    def test_interpretation_validates_categories_and_count_intent(self):
        with patch.object(web, "preliminary_chat_answer", return_value=json.dumps({
            "names": [], "many_localities": True,
            "information_categories": ["uzdrowiska", "unknown", "uzdrowiska"],
            "count_entries": True})), patch.object(web, "cached_filter_options", return_value={}):
            result = web.model_interpret_question("W ilu hasłach opisano uzdrowiska?", {}, [], False)
        self.assertEqual(result["information_categories"], ["uzdrowiska"])
        self.assertTrue(result["count_entries"])
        with patch.object(web, "preliminary_chat_answer", return_value=json.dumps({
            "names": [], "information_categories": "uzdrowiska", "count_entries": True})):
            self.assertFalse(web.model_interpret_question("Ile?", {}, [], False)["count_entries"])

    def test_exact_count_respects_scope_and_and_semantics(self):
        entries = [
            {"has_szkoły": True, "has_biblioteki": True, "powiat_ujednolicony": "warszawski"},
            {"has_szkoły": True, "has_biblioteki": False, "powiat_ujednolicony": "warszawski"},
            {"has_szkoły": True, "has_biblioteki": True, "powiat_ujednolicony": "wileński"},
        ]
        web.annotated_entry_count.cache_clear()
        with patch.object(web, "iter_entries", return_value=iter(entries)):
            count = web.annotated_entry_count("/tmp", "test", (("powiat_ujednolicony", "warszawski"),),
                                             ("szkoły", "biblioteki"))
        self.assertEqual(count, 1)
        web.annotated_entry_count.cache_clear()
        with patch.object(web, "iter_entries", return_value=iter(entries)):
            self.assertEqual(web.annotated_entry_count("/tmp", "test", (("has_szkoły", False),),
                                                       ("szkoły",)), 0)
        web.annotated_entry_count.cache_clear()

    def test_count_response_does_not_call_embeddings_or_answer_model(self):
        config = {"source_dir": "/tmp", "passages_index": "p"}
        interpretation = {"names": [], "district": "warszawski", "many_localities": False,
                          "information_categories": ["uzdrowiska"], "count_entries": True}
        with patch.object(web, "manifest", return_value=config), \
             patch.object(web, "model_interpret_question", return_value=interpretation), \
             patch.object(web, "translate_search_query", return_value="Ile haseł?"), \
             patch.object(web, "annotated_entry_count", return_value=7) as count, \
             patch.object(web.Embeddings, "embed") as embed, \
             patch.object(web.Chat, "stream") as model:
            client = web.app.test_client()
            for language, accept in (("pl", "application/json"), ("en", "text/event-stream")):
                response = client.post("/api/v1/chat", json={"question": "Ile haseł?",
                    "language": language, "filters": {"tom": "01"}}, headers={"Accept": accept})
                self.assertEqual(response.status_code, 200)
                if language == "pl":
                    result = response.json
                else:
                    result = next(json.loads(line[6:]) for line in response.text.splitlines()
                                  if line.startswith("data: ") and "\"answer\"" in line)
                    self.assertIn("Entries with annotations", result["answer"])
                self.assertEqual(result["statistics"]["count"], 7)
                self.assertEqual(result["statistics"]["filters"]["powiat_ujednolicony"], "warszawski")
                self.assertIn(("tom", "01"), count.call_args.args[2])
            embed.assert_not_called()
            model.assert_not_called()

    def test_presence_sources_use_annotations_without_filtering_semantic_payload(self):
        config = {"entries_index": "e", "source_dir": "/tmp", "lookup_db": "/tmp/lookup",
                  "presence_filters_version": 1}
        raw = {"ID": "01-00001", "nazwa": "A", "text": "Zakład leczniczy.",
               "uzdrowiska": ["zakład leczniczy"], "typ_punktu_osadniczego": ["wieś"]}
        with patch.object(web.Meili, "search", return_value={"hits": [{"ID": raw["ID"]}]}) as search, \
             patch.object(web, "source_detail", return_value={"entry": raw, "tom": "01", "strona": 1}):
            sources = web.presence_passage_candidates(config, ["uzdrowiska"], ['tom = "01"'])
        self.assertIn("has_uzdrowiska = true", search.call_args.args[1]["filter"])
        self.assertEqual(sources[0]["uzdrowiska"], raw["uzdrowiska"])
        self.assertTrue(sources[0]["jest_miejscowoscia"])
        self.assertIn("zakład leczniczy", web.source_metadata_text(sources[0]))

    def test_list_merges_presence_sources_and_keeps_general_search_scope(self):
        config = {"entries_index": "e", "passages_index": "p", "vectors": False,
                  "source_dir": "/tmp", "presence_filters_version": 1}
        first = {"entry_id": "01-00001", "passage_id": "01-00001_p0001", "nazwa": "A",
                 "text": "Uzdrowisko A.", "tom": "01", "strona": 1}
        second = {**first, "entry_id": "01-00002", "passage_id": "01-00002_p0001",
                  "nazwa": "B", "text": "Zakład B.", "uzdrowiska": ["zakład leczniczy"]}
        interpretation = {"names": [], "district": "warszawski", "many_localities": True,
                          "information_categories": ["uzdrowiska"], "count_entries": False}
        with patch.object(web, "manifest", return_value=config), \
             patch.object(web, "model_interpret_question", return_value=interpretation), \
             patch.object(web, "model_metadata_searches", return_value=[]), \
             patch.object(web, "presence_passage_candidates", return_value=[second]) as presence, \
             patch.object(web.Meili, "search", return_value={"hits": [first]}) as search, \
             patch.object(web.Chat, "answer", return_value="A [1], B [2].") as answer:
            response = web.app.test_client().post("/api/v1/chat", json={
                "question": "Gdzie były uzdrowiska?", "verify": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["sources"]), 2)
        self.assertNotIn("has_uzdrowiska = true", search.call_args.args[1]["filter"])
        self.assertIn('powiat_ujednolicony = "warszawski"', presence.call_args.args[2])
        self.assertIn("zakład leczniczy", answer.call_args.args[0][1]["content"])


if __name__ == "__main__":
    unittest.main()
