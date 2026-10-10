"""Regression tests for source fidelity, indexing units, and API contracts."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as web
import sgkp_activate
import sgkp_ingest
from sgkp_core import file_hash, normalize, passages, validate
from sgkp_services import Chat, OpenAIChat, ServiceError, filter_expression, scan_url


class SourceTests(unittest.TestCase):
    def test_embedding_cache_deduplicates_and_reuses_vectors(self):
        class FakeEmbeddings:
            url, model, key, dimensions = "unused", "fake", "unused", 2
            requests = []

            def embed(self, texts):
                self.requests.append(list(texts))
                return [[float(len(text)), 1.0] for text in texts]

        with tempfile.TemporaryDirectory() as directory, patch.object(sgkp_ingest, "Embeddings", FakeEmbeddings):
            cache = sgkp_ingest.EmbeddingCache(Path(directory) / "cache.sqlite", "fake")
            service = FakeEmbeddings()
            first = cache.embed(["A", "BB", "A"], service, batch_size=2)
            second = cache.embed(["A", "BB"], service, batch_size=2)
            self.assertEqual(first, [[1.0, 1.0], [2.0, 1.0], [1.0, 1.0]])
            self.assertEqual(second, first[:2])
            self.assertEqual(len(FakeEmbeddings.requests), 1)
            self.assertEqual(set(FakeEmbeddings.requests[0]), {"A", "BB"})
            cache.db.close()

    def test_validator_reports_duplicate_and_bad_child_relation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for number in range(1, 17):
                (root / f"sgkp_{number:02d}.json").write_text("[]", encoding="utf-8")
            rows = [
                {"ID": "01-00001", "nazwa": "A", "rodzaj": "indywidualne", "tom": "01", "strona": 1, "text": "A"},
                {"ID": "01-00001", "nazwa": "B", "rodzaj": "zbiorcze", "tom": "01", "strona": 1, "text": "B",
                 "elementy": [{"ID": "01-00002-001", "nazwa": "B", "nr": "1", "rodzaj": "element", "text": "B"}]},
            ]
            (root / "sgkp_01.json").write_text(json.dumps(rows), encoding="utf-8")
            report = validate(root)
            self.assertEqual({item["issue"] for item in report["errors"]}, {"duplicate_id", "invalid_parent_id"})

    def test_element_keeps_own_fields_and_parent_reference(self):
        parent = {"ID": "14-00123", "nazwa": "Zawady", "rodzaj": "zbiorcze", "tom": "14", "strona": 12,
                  "powiat_ujednolicony": "rodzica"}
        child = {"ID": "14-00123-001", "nazwa": "Zawady", "nr": "1", "text": "Element",
                 "powiat_ujednolicony": "dziecka", "typ_punktu_osadniczego": ["Wieś"]}
        result = normalize(parent, "sgkp_14.json", 7, child, 0)
        self.assertEqual(result["powiat_ujednolicony"], "dziecka")
        self.assertEqual(result["parent_id"], parent["ID"])
        self.assertEqual((result["tom"], result["strona"]), ("14", 12))
        self.assertTrue(result["jest_miejscowoscia"])

    def test_passages_preserve_source_and_cover_long_text(self):
        content = ("Zażółć gęślą jaźń. " * 180) + "\nKONIEC"
        entry = {"ID": "01-00001", "nazwa": "Próba", "text": content, "tom": "01", "strona": 1}
        chunks = passages(entry, max_chars=150, overlap=20)
        self.assertGreater(len(chunks), 10)
        self.assertEqual(chunks[0]["start_offset"], 0)
        self.assertEqual(chunks[-1]["end_offset"], len(content))
        self.assertEqual((chunks[0]["tom"], chunks[0]["strona"]), ("01", 1))
        previous_end = 0
        for item in chunks:
            start, end = item["start_offset"], item["end_offset"]
            self.assertLessEqual(start, previous_end)
            self.assertEqual(item["text"], content[start:end])
            self.assertLessEqual(len(item["text"]), 150)
            previous_end = end


class ApiTests(unittest.TestCase):
    def test_browse_name_filter_matches_substring_before_pagination(self):
        entries = tuple({"ID": f"01-{i:05d}", "nazwa": "Żyrardów Wielki",
                         "tom": "01", "strona": 42} for i in range(53)) + (
            {"ID": "01-00054", "nazwa": "Inna miejscowość", "preview": "Żyrardów",
             "tom": "01", "strona": 43},)
        with patch.object(web, "cached_browse_entries", return_value=entries) as cached:
            first = self.client.get("/api/v1/browse", query_string={
                "tom": "01", "name": "  ŻYRARD  "}).json
            second = self.client.get("/api/v1/browse", query_string={
                "tom": "01", "name": "żyrard", "page": 2}).json
            self.assertEqual(cached.call_args.args[2], "01")
            self.assertEqual(first["estimated_total_hits"], 53)
            self.assertEqual(len(first["hits"]), 50)
            self.assertTrue(first["has_next"])
            self.assertEqual([hit["ID"] for hit in second["hits"]],
                             ["01-00050", "01-00051", "01-00052"])
            self.assertFalse(second["has_next"])
            self.assertEqual(self.client.get("/api/v1/browse", query_string={
                "name": "Nieistniejąca"}).json["estimated_total_hits"], 0)
            self.assertEqual(self.client.get("/api/v1/browse", query_string={
                "name": " "}).json["estimated_total_hits"], 54)

    def test_browse_rejects_overlong_name(self):
        with patch.object(web, "cached_browse_entries", return_value=()):
            response = self.client.get("/api/v1/browse", query_string={"name": "a" * 301})
        self.assertEqual(response.status_code, 400)

    def setUp(self):
        self.client = web.app.test_client()
        self.manifest_patch = patch.object(web, "manifest", return_value={
            "entries_index": "entries", "passages_index": "passages", "vectors": False,
            "source_dir": "/tmp", "lookup_db": "/tmp/lookup.sqlite",
        })
        self.manifest_patch.start()
        self.subjects_patch = patch.object(web, "model_interpret_question",
            side_effect=lambda question, config, history, **kwargs: {
                "names": web.names_in_question(question), "district": None, "many_localities": False})
        self.subjects_patch.start()
        self.metadata_plan_patch = patch.object(web, "model_metadata_searches", return_value=[])
        self.metadata_plan_patch.start()
        self.selection_patch = patch.object(
            web.ChatPassageVerifier, "select",
            side_effect=lambda candidates, limit=web.CHAT_SOURCE_LIMIT, **kwargs: candidates[:limit])
        self.selection_patch.start()

    def tearDown(self):
        self.selection_patch.stop()
        self.metadata_plan_patch.stop()
        self.subjects_patch.stop()
        self.manifest_patch.stop()

    def test_model_recognizes_lowercase_subject_and_omits_question_word(self):
        self.subjects_patch.stop()
        with patch.object(web.Chat, "answer",
                          return_value='{"names":["warmbrunn"]}') as answer:
            names = web.model_interpret_question("Czym wyróżniało się warmbrunn?", {}, [])["names"]
        self.assertEqual(names, ["warmbrunn"])
        self.assertEqual(answer.call_count, 1)
        with patch.object(web.Chat, "answer",
                          return_value='{"names":["Nieobecna","warmbrunn"]}'):
            self.assertEqual(web.model_interpret_question("Czym wyróżniało się warmbrunn?", {}, [])["names"],
                             ["warmbrunn"])

    def test_lowercase_name_is_used_for_named_retrieval(self):
        self.subjects_patch.stop()
        passage = {"passage_id": "13-00002_p0001", "entry_id": "13-00002",
                   "nazwa": "Warmbrunn", "tom": "13", "strona": 5,
                   "text": "Warmbrunn posiadał zakład kąpielowy."}

        def search_result(_index, payload):
            return {"hits": [passage] if payload["q"] == "warmbrunn" else []}

        with patch.object(web.Meili, "search", side_effect=search_result) as search, \
             patch.object(web.Chat, "answer", side_effect=[
                 '{"names":["warmbrunn"]}', "Warmbrunn miał zakład kąpielowy [1]."]):
            response = self.client.post("/api/v1/chat", json={
                "question": "Czy w warmbrunn działał zakład kąpielowy?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args_list[0].args[1]["q"], "warmbrunn")
        self.assertEqual(response.json["sources"][0]["entry_id"], "13-00002")

    def test_filter_escapes_value_and_rejects_expression(self):
        self.assertEqual(filter_expression({"powiat_ujednolicony": 'a" OR tom = "16'}),
                         ['powiat_ujednolicony = "a\\" OR tom = \\"16"'])
        with self.assertRaises(ValueError):
            filter_expression({"jest_miejscowoscia": "maybe"})

    def test_filter_options_include_only_locality_values_for_locality_fields(self):
        entries = [
            {"tom": "01", "powiat_ujednolicony": "warszawski", "jest_miejscowoscia": True,
             "typ_punktu_osadniczego": ["Wieś"], "typ": ["wieś", "rzeka"], "gmina": "Wilanów", "gubernia_ujednolicona": "warszawska"},
            {"tom": "02", "powiat_ujednolicony": "krakowski", "jest_miejscowoscia": False,
             "typ_punktu_osadniczego": None, "typ": ["rzeka", "jezioro", "wieś"], "gmina": "Nie dotyczy", "gubernia_ujednolicona": "Nie dotyczy"},
            {"tom": "03", "powiat_ujednolicony": "łomżyński", "jest_miejscowoscia": True,
             "typ_punktu_osadniczego": ["Wieś"], "gmina": "?omża", "gubernia_ujednolicona": "łomżyńska"},
            {"tom": "04", "powiat_ujednolicony": "łomżyński", "jest_miejscowoscia": True,
             "typ_punktu_osadniczego": ["Wieś"], "gmina": "  Łomża ", "gubernia_ujednolicona": "łomżyńska"},
        ]
        web.cached_filter_options.cache_clear()
        with patch.object(web, "iter_entries", return_value=iter(entries)):
            response = self.client.get("/api/v1/filter-options")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["options"]["typ"], ["jezioro", "rzeka"])
        self.assertEqual(response.json["options"]["gmina"], ["Wilanów", "Łomża"])
        self.assertEqual(response.json["options"]["gubernia_ujednolicona"], ["warszawska", "łomżyńska"])
        self.assertEqual(response.json["options"]["powiat_ujednolicony"], ["krakowski", "warszawski", "łomżyński"])
        web.cached_filter_options.cache_clear()

    def test_chat_searches_proper_name_before_full_question(self):
        passage = {"passage_id": "14-03861_a-001_p0001", "entry_id": "14-03861_a-001", "nazwa": "Zawady",
                   "tom": "14", "strona": 400, "text": "Zawady nad Wisłą.", "start_offset": 0, "end_offset": 18}
        with patch.object(web.Meili, "search", side_effect=[{"hits": [passage]}, {"hits": []}]) as search, \
             patch.object(web.Chat, "answer", return_value="Nad Wisłą [1]."):
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leżą Zawady?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args_list[0].args[1]["q"], "Zawady")
        self.assertEqual(response.json["sources"][0]["entry_id"], passage["entry_id"])

    def test_chat_reserves_sources_for_each_inflected_place_name(self):
        self.assertEqual(web.names_in_question("Czy Okuniew należał do Królestwa Polskiego?"),
                         ["Okuniew", "Królestwa Polskiego"])
        self.assertEqual(web.names_in_question("Porównaj Warszawę i Kraków."),
                         ["Warszawę", "Kraków"])
        self.assertGreater(web.name_match_score("Borysławiu", "Borysław"), 0)
        self.assertGreater(web.name_match_score("Wieliczce", "Wieliczka"), 0)
        first = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Borysław",
                 "tom": "01", "strona": 332, "text": "Wydobywano ropę.",
                 "start_offset": 0, "end_offset": 17}
        second = {**first, "passage_id": "13-00001_p0001", "entry_id": "13-00001",
                  "nazwa": "Wieliczka", "tom": "13", "strona": 319, "text": "Wydobywano sól."}

        def search_result(_index, payload):
            return {"hits": {"Borysław": [first], "Wieliczkę": [], "wieliczk": [second]}
                    .get(payload["q"], [])}

        with patch.object(web.Meili, "search", side_effect=search_result) as search, \
             patch.object(web.Chat, "answer", return_value="Borysław [1] i Wieliczka [2]."):
            response = self.client.post("/api/v1/chat", json={"question": "Co łączy Borysław i Wieliczkę?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([source["nazwa"] for source in response.json["sources"]],
                         ["Borysław", "Wieliczka"])
        self.assertEqual([call.args[1]["q"] for call in search.call_args_list[:3]],
                         ["Borysław", "Wieliczkę", "wieliczk"])

    def test_chat_includes_names_and_pages_for_broader_question(self):
        hits = [{"passage_id": f"01-{number:05d}_p0001", "entry_id": f"01-{number:05d}",
                 "nazwa": f"Uzdrowisko {number}", "tom": "01", "text": "Miejscowość uzdrowiskowa.",
                 "start_offset": 0, "end_offset": 25} for number in range(1, 26)]
        def search_result(index, payload):
            if index == "passages":
                return {"hits": hits}
            return {"hits": [{"ID": payload["q"], "tom": "01", "strona": 42}]}

        with patch.object(web.Meili, "search", side_effect=search_result) as search, \
             patch.object(web.Chat, "answer", return_value="Uzdrowisko 1 [1].") as answer:
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie były uzdrowiska?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args_list[0].args[1]["limit"], web.CHAT_SEARCH_LIMIT)
        self.assertEqual(len(search.call_args_list), 1 + web.CHAT_SOURCE_LIMIT)
        self.assertIn("nazwa=Uzdrowisko 20", answer.call_args.args[0][1]["content"])
        self.assertNotIn("nazwa=Uzdrowisko 21", answer.call_args.args[0][1]["content"])
        self.assertEqual(response.json["sources"][0]["strona"], 42)

    def test_supplement_continues_same_vector_skips_assessed_and_streams_progress(self):
        self.selection_patch.stop()
        first = [{"passage_id": f"01-{i:05d}_p0001", "entry_id": f"01-{i:05d}",
                  "nazwa": f"Village {i}", "tom": "01", "strona": 42,
                  "text": "accepted" if i == 0 else "unrelated"} for i in range(50)]
        another_passage = {**first[0], "passage_id": "01-00000_p0002", "text": "accepted additional evidence"}
        new_entry = {**first[0], "passage_id": "01-00051_p0001", "entry_id": "01-00051"}
        extra = [first[0], first[1], another_passage, new_entry]
        def search_result(index, payload):
            return {"hits": extra if payload.get("offset") == 50 else first}
        for streaming in (False, True):
            with patch.object(web, "manifest", return_value={"passages_index": "passages",
                     "entries_index": "entries", "vectors": True}), \
                 patch.object(web, "model_interpret_question", return_value={
                     "names": [], "district": None, "many_localities": True}), \
                 patch.object(web.Embeddings, "embed", return_value=[[0.2, 0.3]]) as embedding, \
                 patch.object(web.Meili, "search", side_effect=search_result) as search, \
                 patch.object(web.RelevanceDiagnostic, "assess", side_effect=lambda q, hit, *a, **kw:
                    {"score": 0.9 if hit["text"].startswith("accepted") else 0.1,
                     "would_reject": not hit["text"].startswith("accepted")}) as assess, \
                 patch.object(web.Chat, "answer", return_value="Answer [1][2]."), \
                 patch.object(web.Chat, "stream", return_value=iter(["Answer [1][2]."])):
                response = self.client.post("/api/v1/chat", json={"question": "Pytanie?", "verify": True},
                     headers={"Accept": "text/event-stream"} if streaming else {})
                content = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(embedding.call_count, 1)
            self.assertEqual(search.call_count, 2)
            original, supplementary = [call.args[1] for call in search.call_args_list]
            self.assertEqual(supplementary, {**original, "offset": 50})
            self.assertEqual(assess.call_count, 52)
            if streaming:
                self.assertIn('"phase": "supplementary_search"', content)
                self.assertLess(content.index("event: progress"), content.index("event: answer"))
            else:
                self.assertTrue(response.json["supplementary_search"])
                self.assertEqual(len(response.json["sources"]), 2)
                self.assertEqual(len(response.json["sources"][0]["passage_ids"]), 2)

    def test_single_place_does_not_fetch_second_semantic_batch(self):
        self.selection_patch.stop()
        first = [{"passage_id": f"01-{i:05d}_p0001", "entry_id": f"01-{i:05d}",
                  "nazwa": f"Village {i}", "tom": "01", "strona": 42, "text": "Evidence"}
                 for i in range(50)]
        with patch.object(web, "manifest", return_value={"passages_index": "passages", "vectors": True}), \
             patch.object(web, "model_interpret_question", return_value={
                 "names": [], "district": None, "many_localities": False}) as classifier, \
             patch.object(web.Embeddings, "embed", return_value=[[0.2, 0.3]]), \
             patch.object(web.Meili, "search", return_value={"hits": first}) as search, \
             patch.object(web.RelevanceDiagnostic, "assess", side_effect=lambda q, hit, *a, **kw:
                 {"score": 0.9 if hit["entry_id"] == "01-00000" else 0.1,
                  "would_reject": hit["entry_id"] != "01-00000"}), \
             patch.object(web.Chat, "answer", return_value="Answer [1]."):
            response = self.client.post("/api/v1/chat", json={"question": "Pytanie?", "verify": True})
        self.assertEqual(response.status_code, 200)
        classifier.assert_called_once()
        self.assertEqual(search.call_count, 1)
        self.assertFalse(response.json["supplementary_search"])

    def test_deeper_analysis_overrides_final_qwen_for_json_and_stream(self):
        hit = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Village",
               "tom": "01", "strona": 42, "text": "Evidence."}
        actual_chat = web.Chat
        for streaming in (False, True):
            for enabled in (False, True, None):
                body = {"question": "Question?", "verify": False}
                if enabled is not None:
                    body["deeper_analysis"] = enabled
                with patch.object(web.Meili, "search", return_value={"hits": [hit]}), \
                     patch.object(actual_chat, "answer", return_value="Answer [1]."), \
                     patch.object(actual_chat, "stream", return_value=iter(["Answer [1]."])), \
                     patch.object(web, "Chat", wraps=actual_chat) as constructor:
                    response = self.client.post("/api/v1/chat", json=body,
                        headers={"Accept": "text/event-stream"} if streaming else {})
                    response.get_data()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(constructor.call_args.kwargs["enable_thinking"], enabled is True)

    def test_verified_chat_sends_more_than_twenty_fragments_including_one_entry(self):
        self.selection_patch.stop()
        candidates = [{"passage_id": f"01-00001_p{i:04d}", "entry_id": "01-00001",
                       "nazwa": "Village", "tom": "01", "strona": 42,
                       "text": "Evidence " * 200 + f"END{i}"} for i in range(30)]
        with patch.object(web.Meili, "search", return_value={"hits": candidates}), \
             patch.object(web.RelevanceDiagnostic, "assess", return_value={
                 "score": 0.9, "would_reject": False}), \
             patch.object(web.Chat, "answer", return_value="Answer [1].") as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Question?", "verify": True, "diagnostics": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["retrieved_passage_ids"]), 30)
        self.assertIn("END29", answer.call_args.args[0][1]["content"])
        self.assertEqual(len(response.json["sources"]), 1)

    def test_generic_chat_selects_evidence_from_description_not_place_name(self):
        self.selection_patch.stop()
        misleading = {"passage_id": "14-05196_p0001", "entry_id": "14-05196",
                      "nazwa": "Zielony Młyn", "tom": "14", "strona": 1,
                      "text": "Zielony Młyn, pow. toszecko-gliwicki, ob. Kottischowitz."}
        direct = {"passage_id": "01-00001_p0001", "entry_id": "01-00001",
                  "nazwa": "Inna wieś", "tom": "01", "strona": 1,
                  "text": "Inna wieś, pow. warszawski, posiada młyn wodny."}
        self.assertEqual(web.descriptive_source_text(misleading),
                         "pow. toszecko-gliwicki, ob. Kottischowitz.")
        self.assertEqual(web.descriptive_source_text({**misleading,
            "nazwa": "Huta-szklana", "text": "104.) Huta-szklana, pow. kielecki."}),
            "pow. kielecki.")
        self.assertIn("posiada młyn wodny", web.descriptive_source_text(direct))

        with patch.object(web.Meili, "search", return_value={"hits": [misleading, direct]}), \
             patch.object(web.RelevanceDiagnostic, "assess", side_effect=lambda q, hit, *a, **kw:
                 {"score": 0.9 if hit["passage_id"] == direct["passage_id"] else 0.1,
                  "would_reject": hit["passage_id"] != direct["passage_id"]}), \
             patch.object(web.Chat, "answer", return_value="Młyn znajdował się w Innej wsi [1].") as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Gdzie znajdowały się młyny?", "diagnostics": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["retrieved_passage_ids"], [direct["passage_id"]])
        self.assertEqual(answer.call_count, 1)
        self.assertIn("posiada młyn wodny", answer.call_args.args[0][1]["content"])
        self.assertEqual(response.json["sources"][0]["entry_id"], direct["entry_id"])

        with patch.object(web.Meili, "search", return_value={"hits": [misleading]}), \
             patch.object(web.RelevanceDiagnostic, "assess", return_value={"score": 0.1, "would_reject": True}), \
             patch.object(web.Chat, "answer") as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Gdzie znajdowały się młyny?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["sources"], [])
        self.assertIn("nie pozwalają odpowiedzieć", response.json["answer"])
        answer.assert_not_called()

    def test_metadata_search_supplements_semantic_passages_with_citable_entry(self):
        self.metadata_plan_patch.stop()
        entry = {"ID": "01-00033", "nazwa": "Abramówka", "tom": "01", "strona": 10,
                 "text": "Abramówka, wś w pow. warszawskim. Wymieniona w źródłach.",
                 "przemysłowe": ["huta szklana"], "jest_miejscowoscia": True}
        semantic = {"passage_id": "02-00001_p0001", "entry_id": "02-00001",
                    "nazwa": "Inna wieś", "tom": "02", "strona": 20,
                    "text": "Inna wieś, działała tu huta szkła."}

        def search_result(index, payload):
            if index == "entries":
                self.assertEqual(payload["attributesToSearchOn"], ["przemysłowe"])
                self.assertEqual(payload["q"], "huta szklana")
                return {"hits": [entry]}
            return {"hits": [semantic]}

        with patch.object(web, "model_metadata_searches",
                          return_value=[("przemysłowe", "huta szklana")]), \
             patch.object(web.Meili, "search", side_effect=search_result), \
             patch.object(web.Chat, "answer",
                          return_value="Huta działała w Innej wsi [1], a w metadanych Abramówki odnotowano hutę szklaną [2].") as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Gdzie znajdowała się huta szkła?", "diagnostics": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["retrieved_passage_ids"],
                         ["02-00001_p0001", "01-00033_p0001"])
        self.assertEqual(response.json["sources"][1]["przemysłowe"], ["huta szklana"])
        self.assertIn("Metadane hasła: obiekty i działalność przemysłowa: huta szklana",
                      answer.call_args.args[0][1]["content"])

    def test_metadata_search_plan_accepts_only_indexed_fields(self):
        self.metadata_plan_patch.stop()
        with patch.object(web.Chat, "answer", return_value=json.dumps({"searches": [
            {"field": "młyny", "q": "młyn wodny"},
            {"field": "text", "q": "młyn"},
            {"field": "młyny", "q": "młyn wodny"},
        ]})):
            self.assertEqual(web.model_metadata_searches("Gdzie znajdowały się młyny?"),
                             [("młyny", "młyn wodny")])

    def test_interpretation_validates_fields_independently_and_fails_open(self):
        self.subjects_patch.stop()
        config = {"source_dir": "/tmp"}
        question = "Co wiadomo o Okuniewie w powiecie warszawskim?"
        with patch.object(web, "cached_filter_options", return_value={
                "powiat_ujednolicony": ["warszawski", "wileński"]}), \
             patch.object(web, "preliminary_chat_answer", side_effect=[
                 '{"names":["Okuniewie","Nieobecna"],"district":"warszawski","many_localities":false}',
                 '{"names":"invalid","district":"warszawski","many_localities":true}',
                 '{"names":["Okuniewie"],"district":"nieznany","many_localities":"true"}',
                 'invalid JSON', ServiceError("chat", message="timeout")]) as model:
            result = web.model_interpret_question(question, config, [])
            self.assertEqual(result, {"names": ["Okuniewie"], "district": "warszawski",
                                      "many_localities": False, "information_categories": [],
                                      "count_entries": False})
            model.assert_called_once()
            result = web.model_interpret_question(question, config, [])
            self.assertEqual(result["district"], "warszawski")
            self.assertTrue(result["many_localities"])
            result = web.model_interpret_question(question, config, [])
            self.assertEqual(result["names"], ["Okuniewie"])
            self.assertIsNone(result["district"])
            self.assertFalse(result["many_localities"])
            for _ in range(2):
                result = web.model_interpret_question(question, config, [])
                self.assertIsNone(result["district"])
                self.assertFalse(result["many_localities"])

    def test_interpretation_skips_county_list_for_manual_scope(self):
        self.subjects_patch.stop()
        with patch.object(web, "cached_filter_options") as options, \
             patch.object(web, "preliminary_chat_answer", return_value=
                 '{"names":[],"district":"warszawski","many_localities":true}') as model:
            result = web.model_interpret_question("Gdzie były młyny?", {}, [],
                                                  resolve_district=False)
        options.assert_not_called()
        model.assert_called_once()
        self.assertIsNone(result["district"])
        self.assertTrue(result["many_localities"])

    def test_archeo_available_to_planner_and_source_prompt(self):
        self.metadata_plan_patch.stop()
        with patch.object(web, "preliminary_chat_answer", return_value=
                          '{"searches":[{"field":"archeo","q":"wykopaliska"}]}'):
            self.assertEqual(web.model_metadata_searches("Jakie były znaleziska?"),
                             [("archeo", "wykopaliska")])
        self.assertIn("informacje archeologiczne: kurhany",
                      web.source_metadata_text({"archeo": ["kurhany"]}))

    def test_batch_selections_are_retained_when_they_fit_limit(self):
        self.selection_patch.stop()
        candidates = [{"passage_id": f"entry{i}_p0001", "entry_id": f"entry{i}",
                       "text": "Opis znalezisk " * 20} for i in range(2)]
        with patch.object(web, "CHAT_SELECTION_BATCH_CHARS", 300), \
             patch.object(web, "preliminary_chat_answer", side_effect=[
                 '{"passage_ids":["entry0_p0001"]}',
                 '{"passage_ids":["entry1_p0001"]}']) as model:
            selected = web.select_relevant_passages("Jakie znaleziska?", candidates, [],
                                                     limit=20, force=True)
        self.assertEqual(len(selected), 2)
        self.assertEqual(model.call_count, 2)

    def test_empty_merge_preserves_previously_selected_evidence(self):
        self.selection_patch.stop()
        candidates = [{"passage_id": f"entry{i}_p0001", "entry_id": f"entry{i}",
                       "text": "Opis znalezisk " * 20} for i in range(2)]
        with patch.object(web, "CHAT_SELECTION_BATCH_CHARS", 300), \
             patch.object(web, "preliminary_chat_answer", side_effect=[
                 '{"passage_ids":["entry0_p0001"]}',
                 '{"passage_ids":["entry1_p0001"]}', '{"passage_ids":[]}']):
            selected = web.select_relevant_passages("Jakie znaleziska?", candidates, [],
                                                     limit=1, force=True)
        self.assertEqual(len(selected), 1)

    def test_question_district_filters_retrieval_and_preserves_manual_filter(self):
        with patch.object(web, "model_interpret_question", return_value={
                "names": [], "district": "warszawski", "many_localities": True}) as district, \
             patch.object(web.Meili, "search", return_value={"hits": []}) as search:
            response = self.client.post("/api/v1/chat", json={
                "question": "Jakie znaleziska były w powiecie warszawskim?"})
            self.assertEqual(response.status_code, 200)
            self.assertIn('powiat_ujednolicony = "warszawski"',
                          search.call_args.args[1]["filter"])
            district.reset_mock()
            response = self.client.post("/api/v1/chat", json={
                "question": "Jakie znaleziska były w powiecie warszawskim?",
                "filters": {"powiat_ujednolicony": "wileński"}})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(district.call_args.kwargs["resolve_district"])
            self.assertIn('powiat_ujednolicony = "wileński"',
                          search.call_args.args[1]["filter"])

    def test_followup_uses_previously_cited_passages_as_current_evidence(self):
        busk = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Busk",
                "tom": "01", "strona": 478, "text": "Busk miał zakład kąpielowy.",
                "start_offset": 0, "end_offset": 26}
        warmbrunn = {"passage_id": "13-00001_p0001", "entry_id": "13-00001", "nazwa": "Warmbrunn",
                     "tom": "13", "strona": 5, "text": "Początek. " + "Inne wiadomości. " * 50 +
                     "Zakład kąpielowy korzystał z ciepłych źródeł siarczanych.",
                     "start_offset": 0, "end_offset": 1000}
        history = [{"question": "W jakich miejscowościach były uzdrowiska?",
                    "answer": "Busk [1] i Warmbrunn [2].",
                    "source_ids": [busk["passage_id"], warmbrunn["passage_id"]]}]

        def detail(_source_dir, _lookup_db, identifier):
            item = {busk["entry_id"]: busk, warmbrunn["entry_id"]: warmbrunn}[identifier]
            return {"entry": {"ID": item["entry_id"], "nazwa": item["nazwa"], "text": item["text"],
                              "typ_punktu_osadniczego": ["miejscowość"]},
                    "tom": item["tom"], "strona": item["strona"]}

        with patch.object(web, "source_detail", side_effect=detail) as source_detail, \
             patch.object(web.Meili, "search") as search, \
             patch.object(web.Chat, "answer", side_effect=["TAK", "Warmbrunn miał źródła siarczane [2]."]) as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "W którym z nich były źródła siarczane?", "history": history})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(source_detail.call_count, 2)
        search.assert_not_called()
        self.assertEqual([item["nazwa"] for item in response.json["sources"]], ["Warmbrunn"])
        prompt = answer.call_args.args[0][1]["content"]
        self.assertIn("W jakich miejscowościach były uzdrowiska?", prompt)
        self.assertIn("źródeł siarczanych", prompt)
        self.assertNotIn("Busk [1] i Warmbrunn [2]", prompt)

    def test_inflected_place_name_reuses_both_prior_okuniew_sources(self):
        entries = {
            "07-03365": {"ID": "07-03365", "nazwa": "Okuniew",
                         "text": "Okuniew, pow. warszawski, kościół par. murowany.",
                         "tom": "07", "strona": 441},
            "16-09160": {"ID": "16-09160", "nazwa": "Okuniew",
                         "text": "W roku 1580 wymieniono ibidem sanctuarium.",
                         "tom": "16", "strona": 404},
        }

        def detail(_source_dir, _lookup_db, identifier):
            item = entries[identifier]
            return {"entry": item, "tom": item["tom"], "strona": item["strona"]}

        history = [{"question": "Czy Okuniew należał do Królestwa Polskiego?",
                    "answer": "Tak [1][2].",
                    "source_ids": ["07-03365_p0001", "16-09160_p0001"],
                    "source_names": ["Okuniew", "Okuniew"]}]
        with patch.object(web, "source_detail", side_effect=detail), \
             patch.object(web.Meili, "search", return_value={"hits": []}) as search, \
             patch.object(web.Chat, "answer", side_effect=["TAK", "Tak, był tam murowany kościół parafialny [1]."]) as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Czy w Okuniwie znajdował się kościół?", "history": history})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args.args[1]["q"], "Okuniew kościół")
        self.assertEqual(response.json["sources"][0]["entry_id"], "07-03365")
        self.assertIn("kościół par. murowany", answer.call_args.args[0][1]["content"])

    def test_followup_finds_direct_entry_when_previous_answer_cited_only_supplement(self):
        supplement = {"ID": "16-09160", "nazwa": "Okuniew", "text": "Wspomniano ibidem sanctuarium.",
                      "powiat_ujednolicony": "warszawski", "tom": "16", "strona": 404}
        direct = {"passage_id": "07-03365_p0001", "entry_id": "07-03365", "nazwa": "Okuniew",
                  "text": "Okuniew, pow. warszawski, kościół par. murowany.",
                  "powiat_ujednolicony": "warszawski", "tom": "07", "strona": 441}
        history = [{"question": "Czy Okuniew należał do Królestwa Polskiego?", "answer": "Tak [1].",
                    "source_ids": ["16-09160_p0001"], "source_names": ["Okuniew"]}]
        with patch.object(web, "source_detail", return_value={"entry": supplement, "tom": "16", "strona": 404}), \
             patch.object(web.Meili, "search", return_value={"hits": [direct]}) as search, \
             patch.object(web.Chat, "answer", side_effect=["TAK", "Tak, istniał kościół murowany [1]."]) as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Czy w Okuniwie znajdował się kościół?", "history": history})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args.args[1]["q"], "Okuniew kościół")
        self.assertEqual(response.json["sources"][0]["entry_id"], "07-03365")
        self.assertIn("kościół par. murowany", answer.call_args.args[0][1]["content"])

    def test_chat_rejects_oversized_or_invalid_history(self):
        turn = {"question": "Gdzie?", "answer": "Tutaj [1].", "source_ids": ["01-00001_p0001"]}
        self.assertEqual(len(web.validated_chat_history([turn] * web.CHAT_HISTORY_TURNS)), 8)
        for history in ([turn] * (web.CHAT_HISTORY_TURNS + 1),
                        [{**turn, "source_ids": ["../sekret"]}],
                        [{**turn, "source_names": ["Okuniew", "Warszawa"]}],
                        [{**turn, "answer": "x" * (web.CHAT_HISTORY_ANSWER_CHARS + 1)}]):
            response = self.client.post("/api/v1/chat", json={"question": "A gdzie?", "history": history})
            self.assertEqual(response.status_code, 400)

    def test_history_prompt_keeps_recent_turns_within_budget(self):
        history = [{"question": f"Pytanie {number}", "answer": "x" * 5000, "source_ids": []}
                   for number in range(8)]
        prompt = web.history_for_prompt(history)
        self.assertLessEqual(len(prompt), web.CHAT_HISTORY_PROMPT_CHARS)
        self.assertIn("Pytanie 7", prompt)
        self.assertNotIn("Pytanie 0", prompt)

    def test_followup_selects_relevant_later_passage_of_cited_entry(self):
        detail = {"entry": {"ID": "13-00001", "nazwa": "Warmbrunn",
                            "text": ("Wiadomości historyczne. " * 80) +
                            "Zakład kąpielowy korzystał ze źródeł siarczanych."},
                  "tom": "13", "strona": 5}
        config = {"source_dir": "/tmp", "lookup_db": "/tmp/lookup.sqlite"}
        with patch.object(web, "source_detail", return_value=detail):
            result = web.historical_passage(config, "13-00001_p0001", "Które miało źródła siarczane?")
        self.assertNotEqual(result["passage_id"], "13-00001_p0001")
        self.assertIn("źródeł siarczanych", result["text"])

    def test_followup_uses_model_to_find_semantically_related_later_passage(self):
        self.selection_patch.stop()
        entry_id = "01-04658"
        entry = {"ID": entry_id, "nazwa": "Borysław",
                 "text": ("Dawne dzieje miejscowości. " * 75) +
                         "Kopanie studni nie jest bez niebezpieczeństwa. "
                         "Z pokładów wydobywają się zabijające gazy."}
        history = [{"question": "Co wydobywano w Borysławiu?",
                    "answer": "Wydobywano naftę [1].",
                    "source_ids": [entry_id + "_p0001"], "source_names": ["Borysław"]}]
        chunks = web.passages({**entry, "tom": "01", "strona": 332})
        relevant = next(chunk for chunk in chunks if "zabijające gazy" in chunk["text"])
        with patch.object(web, "source_detail", return_value={"entry": entry, "tom": "01", "strona": 332}), \
             patch.object(web.Meili, "search", return_value={"hits": []}) as search, \
             patch.object(web.RelevanceDiagnostic, "assess", side_effect=lambda q, hit, *a, **kw:
                 {"score": 0.9 if hit["passage_id"] == relevant["passage_id"] else 0.1,
                  "would_reject": hit["passage_id"] != relevant["passage_id"]}), \
             patch.object(web.Chat, "answer", side_effect=[
                 "TAK", "Tak, wydobywające się gazy były niebezpieczne [1]."]) as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Czy praca stwarzała tam zagrożenia dla robotników?",
                "history": history, "diagnostics": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["retrieved_passage_ids"][0], relevant["passage_id"])
        self.assertIn("zabijające gazy", answer.call_args.args[0][1]["content"])
        self.assertEqual(response.json["sources"][0]["entry_id"], entry_id)
        search.assert_not_called()

    def test_named_entry_passages_take_priority_over_unrelated_results(self):
        self.selection_patch.stop()
        named = [
            {"passage_id": "13-00002_p0001", "entry_id": "13-00002", "nazwa": "Warmbrunn",
             "tom": "13", "strona": 5, "text": "Wiadomości historyczne."},
            {"passage_id": "13-00002_p0002", "entry_id": "13-00002", "nazwa": "Warmbrunn",
             "tom": "13", "strona": 5, "text": "Zakład przy ciepłych źródłach siarczanych."},
        ]
        unrelated = [{"passage_id": f"01-{i:05d}_p0001", "entry_id": f"01-{i:05d}",
                      "nazwa": f"Inne hasło {i}", "tom": "01", "strona": 1,
                      "text": "Inna informacja."} for i in range(15)]
        misleading = {"passage_id": "01-99999_p0001", "entry_id": "01-99999",
                      "nazwa": "Czym", "tom": "01", "strona": 1,
                      "text": "Inne hasło przypadkowo zgodne ze słowem pytającym."}

        def search_result(_index, payload):
            return {"hits": {"Warmbrunn": named, "Czym": [misleading]}
                    .get(payload["q"], unrelated)}

        with patch.object(web.Meili, "search", side_effect=search_result), \
             patch.object(web.RelevanceDiagnostic, "assess", side_effect=lambda q, hit, *a, **kw:
                 {"score": 0.9 if hit["passage_id"] == "13-00002_p0002" else 0.1,
                  "would_reject": hit["passage_id"] != "13-00002_p0002"}), \
             patch.object(web.Chat, "answer", return_value=
                 "Zakład korzystał z ciepłych źródeł siarczanych [1].") as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Czym wyróżniał się zakład kąpielowy w Warmbrunn?",
                "diagnostics": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["retrieved_passage_ids"][0], "13-00002_p0002")
        self.assertLessEqual(len(response.json["retrieved_passage_ids"]),
                             1 + web.CHAT_NAMED_BACKGROUND_LIMIT)
        self.assertNotIn("Wiadomości historyczne", answer.call_args.args[0][1]["content"])
        self.assertNotIn("przypadkowo zgodne", answer.call_args.args[0][1]["content"])
        self.assertEqual(response.json["sources"][0]["entry_id"], "13-00002")

    def test_model_passage_selection_cannot_invent_sources(self):
        self.assertEqual(web.parse_passage_selection(
            '{"passage_ids":["01-00001_p0001","99-99999_p0001"]}', {"01-00001_p0001"}),
            ["01-00001_p0001"])

    def test_passage_selection_falls_back_when_local_model_is_unavailable(self):
        self.selection_patch.stop()
        candidates = [
            {"passage_id": f"01-00001_p{i:04d}", "entry_id": "01-00001",
             "nazwa": "Hasło", "text": "Treść."} for i in (1, 2)]
        with patch.object(web.Chat, "answer",
                          side_effect=ServiceError("chat", message="timeout")):
            self.assertIsNone(web.select_relevant_passages("Pytanie?", candidates, []))

    def test_model_classifies_every_question_with_history_before_search(self):
        history = [{"question": "Gdzie leżały Zawady?", "answer": "Wśród nich była osada karczemna.",
                    "source_ids": ["14-03861_a-002_p0001"], "source_names": ["Zawady"]}]
        with patch.object(web.Chat, "answer", return_value="TAK") as classify:
            self.assertTrue(web.model_resolves_followup("Czy osada karczemna miała szkołę?", history))
            self.assertTrue(web.model_resolves_followup("Czy w Zawadach była szkoła?", history))
        self.assertEqual(classify.call_count, 2)
        with patch.object(web.Chat, "answer", return_value="NIE") as classify:
            self.assertFalse(web.model_resolves_followup("Jakie typy osad wymieniono w powiecie wileńskim?", history))
            self.assertFalse(web.model_resolves_followup("A kiedy powstała Warszawa?", history))
        self.assertEqual(classify.call_count, 2)
        with patch.object(web.Chat, "answer", return_value="NIE") as classify:
            self.assertFalse(web.model_resolves_followup("Czy w Warszawie był kościół?", history))
        classify.assert_called_once()

    def test_followup_about_second_zawady_uses_previous_element(self):
        entries = {
            "14-03861_a-001": {"ID": "14-03861_a-001", "nazwa": "Zawady",
                                 "text": "1.) wieś i folwark nad Wisłą, gm. Wilanów."},
            "14-03861_a-002": {"ID": "14-03861_a-002", "nazwa": "Zawady",
                                 "text": "2.) Z., os. karcz., pow. warszawski, gm. Falenty, par. Raszyn."},
        }

        def detail(_source_dir, _lookup_db, identifier):
            return {"entry": entries[identifier], "tom": "14", "strona": 479}

        history = [{"question": "Gdzie leżały Zawady w powiecie warszawskim?",
                    "answer": "1. Wieś i folwark [1]. 2. Osada karczemna w gminie Falenty [2].",
                    "source_ids": ["14-03861_a-001_p0001", "14-03861_a-002_p0001"],
                    "source_names": ["Zawady", "Zawady"]}]
        with patch.object(web, "source_detail", side_effect=detail), \
             patch.object(web.Meili, "search") as search, \
             patch.object(web.Chat, "answer", side_effect=["TAK", "Hasło podaje tylko gminę Falenty i parafię Raszyn [2]."]):
            response = self.client.post("/api/v1/chat", json={
                "question": "Czy wiadomo coś więcej o tej osadzie karczemnej?", "history": history})
        self.assertEqual(response.status_code, 200)
        search.assert_not_called()
        self.assertEqual(response.json["sources"][0]["entry_id"], "14-03861_a-002")

    def test_new_topic_after_zawady_uses_fresh_search(self):
        history = [{"question": "Gdzie leżały Zawady w powiecie warszawskim?",
                    "answer": "Wieś w Wilanowie [1] i osada karczemna w Falentach [2].",
                    "source_ids": ["14-03861_a-001_p0001", "14-03861_a-002_p0001"],
                    "source_names": ["Zawady", "Zawady"]}]
        wileński = {"passage_id": "15-00001_p0001", "entry_id": "15-00001", "nazwa": "Przykład",
                    "tom": "15", "strona": 10, "text": "Wieś w powiecie wileńskim.",
                    "start_offset": 0, "end_offset": 30}
        with patch.object(web, "source_detail") as detail, \
             patch.object(web.Meili, "search", return_value={"hits": [wileński]}) as search, \
             patch.object(web.Chat, "answer", side_effect=["NIE", "Wymieniono wieś [1]."]) as answer:
            response = self.client.post("/api/v1/chat", json={
                "question": "Jakie typy osad wymieniono w powiecie wileńskim?", "history": history})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args.args[1]["q"], "Jakie typy osad wymieniono w powiecie wileńskim?")
        detail.assert_not_called()
        self.assertEqual(answer.call_count, 2)
        self.assertNotIn("Zawady", answer.call_args.args[0][1]["content"])
        self.assertEqual(response.json["sources"][0]["entry_id"], "15-00001")

    def test_search_returns_cropped_text_without_full_record(self):
        formatted = "…" + web.HIGHLIGHT_START + "Wisłą" + web.HIGHLIGHT_END + "…"
        backend = {"hits": [{"ID": "14-00001", "nazwa": "Zawady", "tom": "14", "strona": 3,
                            "_formatted": {"text": formatted}}], "estimatedTotalHits": 1}
        with patch.object(web.Meili, "search", return_value=backend) as search:
            response = self.client.get("/api/v1/search?q=Wisła")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["hits"][0]["snippet"], "…Wisłą…")
        self.assertEqual(response.json["hits"][0]["snippet_highlights"], [[1, 6]])
        self.assertEqual(search.call_args.args[1]["attributesToHighlight"], ["text"])
        self.assertNotIn("text", search.call_args.args[1]["attributesToRetrieve"])
        self.assertNotIn("text", response.json["hits"][0])

    def test_element_detail_has_number_parent_and_source_format(self):
        source = {"entry": {"ID": "14-03861_a-001", "nazwa": "Zawady", "rodzaj": "element", "nr": "1",
                            "text": "1.) wieś nad Wisłą."},
                  "parent": {"ID": "14-03861_a", "nazwa": "Zawady", "text": "Hasło zbiorcze",
                             "markdown": "**Zawady**"}, "tom": "14", "strona": 400}
        with patch.object(web, "source_detail", return_value=source):
            response = self.client.get("/api/v1/entries/14-03861_a-001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["nr"], "1")
        self.assertEqual(response.json["parent_id"], "14-03861_a")
        self.assertEqual(response.json["display_format"], "text")

    def test_entry_detail_renders_headings_and_collapsed_tables_safely(self):
        source = {"entry": {"ID": "13-00118", "nazwa": "Warszawa", "rodzaj": "indywidualne",
                            "text": "Warszawa", "markdown": "### Statystyka\n\n"
                            "| Rok | Liczba | |-----|--------| | 1880 | 123 | | 1890 | 456 |\n\n"
                            "<script>alert(1)</script><img src=x onerror=alert(1)>"
                            "<br>[odnośnik](javascript:alert)"},
                  "parent": None, "tom": "13", "strona": 1}
        with patch.object(web, "source_detail", return_value=source):
            response = self.client.get("/api/v1/entries/13-00118")
        rendered = response.json["rendered_html"]
        self.assertEqual(response.status_code, 200)
        self.assertIn("<h3>Statystyka</h3>", rendered)
        self.assertIn("<table>", rendered)
        self.assertIn("<td>456</td>", rendered)
        self.assertIn("<br>", rendered)
        self.assertNotIn("<script", rendered)
        self.assertNotIn("onerror", rendered)
        self.assertNotIn("javascript:", rendered)

    def test_bad_parameters_and_embedding_outage(self):
        self.assertEqual(self.client.get("/api/v1/search?q=x&page=500&page_size=50").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/search?q=x&mode=semantic").status_code, 503)
        self.assertEqual(self.client.post("/api/v1/chat", json=["wrong"]).status_code, 400)

    def test_health_reports_vector_readiness_separately_from_configuration(self):
        with patch.object(web.Meili, "health", return_value={"status": "available"}):
            response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["vector_index_ready"])
        self.assertIn("chat_model", response.json)

    def test_chat_only_returns_cited_sources(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}
        with patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "answer", return_value="Warszawa leży nad Wisłą [1]. Inna wzmianka [9]."):
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["sources"]), 1)
        self.assertNotIn("[9]", response.json["answer"])
        self.assertIn("[1]", response.json["answer"])

    def test_chat_repairs_useful_answer_without_citations(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}
        with patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "answer", side_effect=["Warszawa leży nad Wisłą.",
                                                          "Warszawa leży nad Wisłą [1]."]) as answer:
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(answer.call_count, 2)
        self.assertEqual(response.json["answer"], "Warszawa leży nad Wisłą [1].")
        self.assertEqual(response.json["sources"][0]["entry_id"], passage["entry_id"])
        self.assertEqual(answer.call_args.args[0][-2]["role"], "assistant")

    def test_chat_stream_emits_deltas_and_verified_answer(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}
        with patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "stream", return_value=iter(["Nad ", "Wisłą [1]."])):
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"},
                                        headers={"Accept": "text/event-stream"})
            body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("event: delta", body)
        self.assertIn("event: answer", body)
        self.assertIn("Wisłą [1].", body)

    def test_chat_stream_repairs_uncited_final_answer(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}
        with patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "stream", return_value=iter(["Warszawa leży nad Wisłą."])), \
             patch.object(web.Chat, "answer", return_value="Warszawa leży nad Wisłą [1].") as repair:
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"},
                                        headers={"Accept": "text/event-stream"})
            body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(repair.call_count, 1)
        self.assertIn('"answer": "Warszawa leży nad Wisłą [1]."', body)
        self.assertNotIn("weryfikowalnymi odsyłaczami", body)

    def test_chat_uses_openai_when_local_model_fails(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}
        with patch.dict("os.environ", {"OPENAI_CHAT_MODEL": "gpt-6-luna"}), \
             patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "answer", side_effect=ServiceError("chat", message="timeout")), \
             patch.object(web.OpenAIChat, "answer", return_value="Warszawa leży nad Wisłą [1].") as fallback:
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["provider"], "openai")
        self.assertEqual(response.json["model"], "gpt-6-luna")
        self.assertEqual(response.json["sources"][0]["entry_id"], passage["entry_id"])
        self.assertEqual(fallback.call_count, 1)

    def test_chat_retrieves_textually_when_embeddings_fail(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}
        config = {"entries_index": "entries", "passages_index": "passages", "vectors": True,
                  "source_dir": "/tmp", "lookup_db": "/tmp/lookup.sqlite"}
        with patch.object(web, "manifest", return_value=config), \
             patch.object(web.Embeddings, "embed", side_effect=ServiceError("embedding", message="timeout")), \
             patch.object(web.Meili, "search", return_value={"hits": [passage]}) as search, \
             patch.object(web.Chat, "answer", return_value="Warszawa leży nad Wisłą [1]."):
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["provider"], "local")
        self.assertTrue(all("vector" not in call.args[1] for call in search.call_args_list))

    def test_chat_semantic_retrieval_for_natural_language_mining_question(self):
        question = "Co wiadomo o wydobywaniu surowców?"
        relevant = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Borysław",
                    "tom": "01", "strona": 332, "text": "W Borysławiu wydobywano ropę naftową.",
                    "start_offset": 0, "end_offset": 38}
        unrelated = {**relevant, "passage_id": "02-00001_p0001", "entry_id": "02-00001",
                     "nazwa": "Gronowo", "text": "Wieś w powiecie."}
        config = {"entries_index": "entries", "passages_index": "passages", "vectors": True,
                  "source_dir": "/tmp", "lookup_db": "/tmp/lookup.sqlite"}

        def search_result(index, payload):
            if index == "entries":
                return {"hits": []}
            ratio = payload.get("hybrid", {}).get("semanticRatio")
            return {"hits": [relevant if ratio == 1.0 else unrelated]}

        with patch.object(web, "manifest", return_value=config), \
             patch.object(web.Embeddings, "embed", return_value=[[0.1, 0.2]]), \
             patch.object(web.Meili, "search", side_effect=search_result) as search, \
             patch.object(web.Chat, "answer", return_value="W Borysławiu wydobywano ropę [1]."):
            response = self.client.post("/api/v1/chat", json={"question": question})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args_list[0].args[1]["hybrid"]["semanticRatio"], 1.0)
        self.assertEqual(response.json["sources"][0]["nazwa"], "Borysław")

    def test_repeated_question_does_not_reuse_sources_from_failed_answer(self):
        question = "Co wiadomo o wydobywaniu surowców?"
        relevant = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Borysław",
                    "tom": "01", "strona": 332, "text": "Wydobywano ropę naftową.",
                    "start_offset": 0, "end_offset": 25}
        history = [{"question": question,
                    "answer": "W wynikach wyszukiwania nie ma informacji o wydobywaniu surowców [1].",
                    "source_ids": ["02-00001_p0001"], "source_names": ["Gronowo"]}]
        with patch.object(web, "historical_passage") as historical, \
             patch.object(web.Meili, "search", return_value={"hits": [relevant]}) as search, \
             patch.object(web.Chat, "answer", side_effect=["TAK", "W Borysławiu wydobywano ropę [1]."]):
            response = self.client.post("/api/v1/chat", json={"question": question, "history": history})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["sources"][0]["nazwa"], "Borysław")
        historical.assert_not_called()
        self.assertEqual(search.call_args_list[0].args[1]["q"], question)

    def test_chat_does_not_list_unrelated_sources_for_insufficient_answer(self):
        source = {"entry_id": "02-00001", "nazwa": "Gronowo", "tom": "02", "strona": 852}
        result = web.chat_response("W wynikach wyszukiwania nie ma informacji o tym [1][2].",
                                   [source, source])
        self.assertEqual(result["sources"], [])
        self.assertNotIn("[1]", result["answer"])
        self.assertNotIn("[2]", result["answer"])
        qualified_source = {**source, "nazwa": "Borysław"}
        qualified = web.chat_response("Nie ma informacji o skali, ale w Borysławiu wydobywano ropę [1].",
                                      [qualified_source])
        self.assertEqual(len(qualified["sources"]), 1)
        self.assertIn("[1]", qualified["answer"])
        two_sentences = web.chat_response("Nie ma informacji o skali. W Borysławiu wydobywano ropę [1].",
                                          [qualified_source])
        self.assertEqual(len(two_sentences["sources"]), 1)

    def test_chat_stream_replaces_partial_local_answer_after_failure(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}

        def interrupted(_messages):
            yield "Niedokończona odpowiedź"
            raise ServiceError("chat", message="incomplete_stream")

        with patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "stream", side_effect=interrupted), \
             patch.object(web.OpenAIChat, "stream", return_value=iter(["Nad Wisłą [1]."])):
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"},
                                        headers={"Accept": "text/event-stream"})
            body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("event: fallback", body)
        self.assertIn('"provider": "openai"', body)
        self.assertIn('"answer": "Nad Wisłą [1]."', body)
        self.assertIn("event: done", body)

    def test_chat_stream_retries_locally_when_answer_hits_output_limit(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}

        def streams(_messages, max_tokens=None):
            if max_tokens is None:
                def partial():
                    yield "Urwana odpo"
                    raise ServiceError("chat", message="output_limit")
                return partial()
            return iter(["Warszawa leży nad Wisłą [1]."])

        with patch.dict("os.environ", {"CHAT_MAX_OUTPUT_TOKENS": "3000"}), \
             patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "stream", side_effect=streams) as stream, \
             patch.object(web.OpenAIChat, "stream") as fallback:
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"},
                                        headers={"Accept": "text/event-stream"})
            body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("event: retry", body)
        self.assertIn('"answer": "Warszawa leży nad Wisłą [1]."', body)
        self.assertIn('"provider": "local"', body)
        self.assertEqual(stream.call_args_list[1].kwargs["max_tokens"], 6000)
        fallback.assert_not_called()

    def test_chat_nonstream_retries_locally_when_answer_hits_output_limit(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}
        with patch.dict("os.environ", {"CHAT_MAX_OUTPUT_TOKENS": "3000"}), \
             patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "answer", side_effect=[ServiceError("chat", message="output_limit"),
                                                          "Warszawa leży nad Wisłą [1]."]) as answer:
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["answer"], "Warszawa leży nad Wisłą [1].")
        self.assertEqual(answer.call_args_list[1].kwargs["max_tokens"], 6000)

    def test_chat_reports_missing_openai_model_access(self):
        passage = {"passage_id": "01-00001_p0001", "entry_id": "01-00001", "nazwa": "Warszawa",
                   "tom": "01", "strona": 1, "text": "Warszawa leży nad Wisłą.", "start_offset": 0, "end_offset": 25}
        with patch.object(web.Meili, "search", return_value={"hits": [passage]}), \
             patch.object(web.Chat, "stream", side_effect=ServiceError("chat", message="request_failed")), \
             patch.object(web.OpenAIChat, "stream", side_effect=ServiceError(
                 "openai", status=403, message="model_not_found")):
            response = self.client.post("/api/v1/chat", json={"question": "Gdzie leży Warszawa?"},
                                        headers={"Accept": "text/event-stream"})
            body = response.get_data(as_text=True)
        self.assertIn("event: fallback", body)
        self.assertIn("Projekt OpenAI nie ma dostępu", body)
        self.assertNotIn("event: answer", body)

    def test_openai_response_stream_parses_text_and_completion(self):
        class FakeResponse:
            status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def iter_lines(self, decode_unicode=False):
                return iter([
                    'event: response.output_text.delta',
                    'data: {"type":"response.output_text.delta","delta":"Nad Wisłą [1]."}',
                    'data: {"type":"response.completed","response":{"status":"completed"}}',
                ])

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "OPENAI_CHAT_MODEL": "gpt-6-luna"}), \
             patch("sgkp_services.requests.post", return_value=FakeResponse()) as post:
            parts = list(OpenAIChat().stream([{"role": "user", "content": "Gdzie?"}]))
        self.assertEqual(parts, ["Nad Wisłą [1]."])
        self.assertEqual(post.call_args.kwargs["json"]["model"], "gpt-6-luna")
        self.assertFalse(post.call_args.kwargs["json"]["store"])

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "OPENAI_CHAT_MODEL": "gpt-4.1-mini",
                                    "OPENAI_REASONING_EFFORT": ""}), \
             patch("sgkp_services.requests.post", return_value=FakeResponse()) as post:
            list(OpenAIChat().stream([{"role": "user", "content": "Gdzie?"}]))
        self.assertEqual(post.call_args.kwargs["json"]["model"], "gpt-4.1-mini")
        self.assertNotIn("reasoning", post.call_args.kwargs["json"])

    def test_openai_response_extracts_visible_text(self):
        class FakeResponse:
            status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def json(self):
                return {"status": "completed", "output": [
                    {"type": "reasoning", "summary": []},
                    {"type": "message", "content": [{"type": "output_text", "text": "Nad Wisłą [1]."}]},
                ]}

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), \
             patch("sgkp_services.requests.post", return_value=FakeResponse()):
            answer = OpenAIChat().answer([{"role": "user", "content": "Gdzie?"}])
        self.assertEqual(answer, "Nad Wisłą [1].")

    def test_local_chat_reports_output_limit_instead_of_returning_partial_text(self):
        class FakeResponse:
            status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "Urwana odpo"}, "finish_reason": "length"}]}

            def iter_lines(self, decode_unicode=False):
                return iter([
                    'data: {"choices":[{"delta":{"content":"Urwana odpo"},"finish_reason":null}]}',
                    'data: {"choices":[{"delta":{},"finish_reason":"length"}]}',
                    'data: [DONE]',
                ])

        with patch.dict("os.environ", {"AI_TEST_KEY": "test-key", "CHAT_MAX_OUTPUT_TOKENS": "3000"}), \
             patch("sgkp_services.requests.post", return_value=FakeResponse()) as post:
            with self.assertRaises(ServiceError) as streamed:
                list(Chat().stream([{"role": "user", "content": "Gdzie?"}]))
            self.assertEqual(streamed.exception.message, "output_limit")
            with self.assertRaises(ServiceError) as plain:
                Chat().answer([{"role": "user", "content": "Gdzie?"}])
            self.assertEqual(plain.exception.message, "output_limit")
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 3000)

    def test_request_thinking_override_uses_low_and_leaves_helpers_disabled(self):
        with patch.dict("os.environ", {"QWEN_ENABLE_THINKING": "true",
                                      "QWEN_REASONING_EFFORT": "xhigh"}, clear=True):
            for enabled in (False, True):
                chat = Chat(enable_thinking=enabled)
                payload = chat.request_payload([], 100, stream=False)
                self.assertEqual(payload["chat_template_kwargs"]["enable_thinking"], enabled)
                self.assertEqual(payload.get("reasoning_effort"), "low" if enabled else None)
                self.assertEqual(payload["temperature"], 1.0 if enabled else 0.7)
            helper = Chat(preliminary=True, enable_thinking=True)
            self.assertFalse(helper.enable_thinking)
            self.assertEqual(helper.temperature, 0.3)

    def test_qwen_thinking_setting_applies_to_plain_and_streamed_requests(self):
        class FakeResponse:
            status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "Odpowiedź"}}]}

            def iter_lines(self, decode_unicode=False):
                return iter([
                    'data: {"choices":[{"delta":{"content":"Odpowiedź"}}]}',
                    'data: [DONE]',
                ])

        with patch.dict("os.environ", {"AI_TEST_KEY": "test-key"}, clear=True):
            chat = Chat()
            self.assertFalse(chat.enable_thinking)
            payload = chat.request_payload([], 100, stream=False)
            self.assertNotIn("reasoning_effort", payload)
            self.assertEqual(payload["temperature"], 0.7)

        for setting, effort, override, expected in (
            ("true", "medium", "", True), ("1", "low", "", True),
            ("true", "xhigh", "0.35", True), ("true", "", "", True),
            ("FALSE", "medium", "", False), ("0", "", "0.2", False),
        ):
            with self.subTest(setting=setting, effort=effort, override=override), \
                 patch.dict("os.environ", {"AI_TEST_KEY": "test-key", "QWEN_ENABLE_THINKING": setting,
                                            "QWEN_REASONING_EFFORT": effort,
                                            **({"QWEN_TEMPERATURE": override} if override else {})}, clear=True), \
                 patch("sgkp_services.requests.post", return_value=FakeResponse()) as post:
                chat = Chat()
                self.assertEqual(chat.answer([{"role": "user", "content": "Pytanie"}]), "Odpowiedź")
                self.assertEqual(list(chat.stream([{"role": "user", "content": "Pytanie"}])), ["Odpowiedź"])
                for call in post.call_args_list:
                    payload = call.kwargs["json"]
                    self.assertEqual(payload["chat_template_kwargs"]["enable_thinking"], expected)
                    self.assertEqual(payload["temperature"], float(override) if override else
                                     (1.0 if expected else 0.7))
                    if expected and effort:
                        self.assertEqual(payload["reasoning_effort"], effort)
                    else:
                        self.assertNotIn("reasoning_effort", payload)

        with patch.dict("os.environ", {"QWEN_ENABLE_THINKING": "invalid"}):
            with self.assertRaisesRegex(ValueError, "QWEN_ENABLE_THINKING"):
                Chat()
        with patch.dict("os.environ", {"QWEN_ENABLE_THINKING": "true",
                                            "QWEN_REASONING_EFFORT": "high"}):
            with self.assertRaisesRegex(ValueError, "QWEN_REASONING_EFFORT"):
                Chat()
        with patch.dict("os.environ", {"QWEN_TEMPERATURE": "nan"}):
            with self.assertRaisesRegex(ValueError, "QWEN_TEMPERATURE"):
                Chat()

    def test_scan_parts_of_volume_xv(self):
        self.assertIn("XV_cz.1", scan_url("15", 1))
        self.assertIn("XV_cz.2", scan_url("16", 1))
        self.assertIsNone(scan_url("16", 0))


class ManifestTests(unittest.TestCase):
    def test_previous_index_pair_can_be_activated_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "json"
            source.mkdir()
            hashes = {}
            for number in range(1, 17):
                path = source / f"sgkp_{number:02d}.json"
                path.write_text("[]")
                hashes[path.name] = file_hash(path)
            manifest = {"source_dir": str(source), "sha256": hashes,
                        "entries_index": "entries_old", "passages_index": "passages_old",
                        "counts": {"entries": 3, "passages": 4}}
            (root / "manifest_old.json").write_text(json.dumps(manifest))
            with patch.object(sgkp_activate.Meili, "stats", side_effect=[{"numberOfDocuments": 3}, {"numberOfDocuments": 4}]):
                result = sgkp_activate.activate(root, "old")
            self.assertEqual(result["active_entries_index"], "entries_old")
            self.assertEqual(json.loads((root / "active_manifest.json").read_text()), manifest)

    def test_cache_is_cleared_on_manifest_switch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            volume = source / "sgkp_01.json"
            volume.write_text("[]")
            manifest_file = root / "active_manifest.json"
            config = {"source_dir": str(source), "created_at": "one",
                      "source_stat": {volume.name: {"size": volume.stat().st_size, "mtime_ns": volume.stat().st_mtime_ns}}}
            manifest_file.write_text(json.dumps(config))
            with patch.object(web, "RUNTIME", root), patch.object(web.cached_volume, "cache_clear") as clear:
                web._manifest_version = None
                web.manifest()
                web.manifest()
                self.assertEqual(clear.call_count, 1)
                config["created_at"] = "two"
                manifest_file.write_text(json.dumps(config))
                web.manifest()
                self.assertEqual(clear.call_count, 2)


if __name__ == "__main__":
    unittest.main()
