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
from sgkp_services import OpenAIChat, ServiceError, filter_expression, scan_url


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
    def setUp(self):
        self.client = web.app.test_client()
        self.manifest_patch = patch.object(web, "manifest", return_value={
            "entries_index": "entries", "passages_index": "passages", "vectors": False,
            "source_dir": "/tmp", "lookup_db": "/tmp/lookup.sqlite",
        })
        self.manifest_patch.start()

    def tearDown(self):
        self.manifest_patch.stop()

    def test_filter_escapes_value_and_rejects_expression(self):
        self.assertEqual(filter_expression({"powiat_ujednolicony": 'a" OR tom = "16'}),
                         ['powiat_ujednolicony = "a\\" OR tom = \\"16"'])
        with self.assertRaises(ValueError):
            filter_expression({"jest_miejscowoscia": "maybe"})

    def test_filter_options_include_only_locality_values_for_locality_fields(self):
        entries = [
            {"tom": "01", "powiat_ujednolicony": "warszawski", "jest_miejscowoscia": True,
             "typ_punktu_osadniczego": ["Wieś"], "gmina": "Wilanów", "gubernia_ujednolicona": "warszawska"},
            {"tom": "02", "powiat_ujednolicony": "krakowski", "jest_miejscowoscia": False,
             "typ_punktu_osadniczego": None, "gmina": "Nie dotyczy", "gubernia_ujednolicona": "Nie dotyczy"},
            {"tom": "03", "powiat_ujednolicony": "łomżyński", "jest_miejscowoscia": True,
             "typ_punktu_osadniczego": ["Wieś"], "gmina": "?omża", "gubernia_ujednolicona": "łomżyńska"},
            {"tom": "04", "powiat_ujednolicony": "łomżyński", "jest_miejscowoscia": True,
             "typ_punktu_osadniczego": ["Wieś"], "gmina": "  Łomża ", "gubernia_ujednolicona": "łomżyńska"},
        ]
        web.cached_filter_options.cache_clear()
        with patch.object(web, "iter_entries", return_value=iter(entries)):
            response = self.client.get("/api/v1/filter-options")
        self.assertEqual(response.status_code, 200)
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

    def test_chat_includes_names_and_pages_for_broader_question(self):
        hits = [{"passage_id": f"01-{number:05d}_p0001", "entry_id": f"01-{number:05d}",
                 "nazwa": f"Uzdrowisko {number}", "tom": "01", "text": "Miejscowość uzdrowiskowa.",
                 "start_offset": 0, "end_offset": 25} for number in range(1, 21)]
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
        self.assertIn("nazwa=Uzdrowisko 16", answer.call_args.args[0][1]["content"])
        self.assertNotIn("nazwa=Uzdrowisko 17", answer.call_args.args[0][1]["content"])
        self.assertEqual(response.json["sources"][0]["strona"], 42)

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
