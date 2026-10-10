import json
import sqlite3
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlparse, parse_qs

import app as web
from sgkp_core import PRESENCE_FIELDS, PRESENCE_FIELD_VERSIONS, PRESENCE_FILTER_VERSION, normalize, passages, presence_flags
from sgkp_services import filter_expression
from sgkp_enable_presence_filters import stage_documents, update_indexes


class PresenceTests(unittest.TestCase):
    def test_parish_filter_options_passages_and_api(self):
        row = {"ID": "01-00001", "nazwa": "A", "text": "Opis.", "tom": "01", "strona": 1,
               "typ_punktu_osadniczego": ["wieś"], "parafia_katolicka": ["Warszawa", "Raszyn"]}
        indexed = normalize(row, "sgkp_01.json", 0)
        self.assertEqual(passages(indexed)[0]["parafia_katolicka"], row["parafia_katolicka"])
        self.assertTrue(web.source_matches_filters(indexed, {"parafia_katolicka": "Raszyn"}))
        self.assertFalse(web.source_matches_filters(indexed, {"parafia_katolicka": "Inna"}))
        with patch.object(web, "iter_entries", return_value=iter([indexed])):
            options = web.cached_filter_options("/tmp/parish-test", "parish-test")
        self.assertEqual(options["parafia_katolicka"], ["Raszyn", "Warszawa"])
        config = {"source_dir": "/tmp", "entries_index": "e", "passages_index": "p",
                  "vectors": False, "catholic_parish_filter_version": 1}
        with patch.object(web, "manifest", return_value=config), \
             patch.object(web, "cached_filter_options", return_value=options), \
             patch.object(web.Meili, "search", return_value={"hits": []}) as search, \
             patch.object(web, "model_interpret_question", return_value={
                 "names": [], "district": None, "many_localities": False}), \
             patch.object(web, "model_metadata_searches", return_value=[]):
            client = web.app.test_client()
            self.assertTrue(client.get("/api/v1/filter-options").json["catholic_parish_filter_available"])
            response = client.get("/api/v1/search", query_string={
                "q": "szkoła", "mode": "text", "parafia_katolicka": "Raszyn"})
            self.assertEqual(response.status_code, 200)
            self.assertIn('parafia_katolicka = "Raszyn"', search.call_args.args[1]["filter"])
            response = client.post("/api/v1/chat", json={"question": "Jakie były szkoły?",
                "verify": False, "filters": {"parafia_katolicka": "Raszyn"}})
            self.assertEqual(response.status_code, 200)
            self.assertIn('parafia_katolicka = "Raszyn"', search.call_args.args[1]["filter"])

    def test_flags_distinguish_annotations_from_headword_and_body(self):
        row = {"ID": "01-00001", "nazwa": "Młyn", "text": "Szkoła i biblioteka.",
               "rodzaj": "indywidualne", "tom": "01", "strona": 1,
               "młyny": ["  "], "szkoły": ["szkoła"], "archeo": [],
               "uzdrowiska": ["zakład kąpielowy"], "celne": ["komora celna"]}
        flags = presence_flags(row)
        self.assertFalse(flags["has_młyny"])
        self.assertFalse(flags["has_biblioteki"])
        self.assertTrue(flags["has_szkoły"])
        self.assertTrue(flags["has_uzdrowiska"])
        self.assertTrue(flags["has_celne"])
        indexed = normalize(row, "sgkp_01.json", 0)
        self.assertEqual({key: indexed[key] for key in PRESENCE_FIELDS}, flags)
        self.assertTrue(passages(indexed)[0]["has_szkoły"])
        self.assertTrue(passages(row)[0]["has_szkoły"])
        child = {**row, "ID": "01-00001-001", "nr": "1", "szkoły": [], "celne": []}
        self.assertFalse(normalize(row, "sgkp_01.json", 0, child, 0)["has_szkoły"])
        self.assertFalse(normalize(row, "sgkp_01.json", 0, child, 0)["has_celne"])

    def test_boolean_filters_and_historical_source_matching(self):
        for flag in PRESENCE_FIELDS:
            self.assertEqual(filter_expression({flag: "true"}), [f"{flag} = true"])
            self.assertEqual(filter_expression({flag: False}), [f"{flag} = false"])
            with self.assertRaises(ValueError):
                filter_expression({flag: "anything"})
        source = {"has_szkoły": True, "has_biblioteki": False}
        self.assertTrue(web.source_matches_filters(source, {"has_szkoły": "true"}))
        self.assertFalse(web.source_matches_filters(source, {
            "has_szkoły": "true", "has_biblioteki": "true"}))

    def test_filters_reach_search_and_chat_and_availability_is_explicit(self):
        client = web.app.test_client()
        config = {"source_dir": "/tmp", "entries_index": "entries", "passages_index": "passages",
                  "vectors": False, "presence_filters_version": 1}
        with patch.object(web, "manifest", return_value=config), \
             patch.object(web, "cached_filter_options", return_value={}), \
             patch.object(web.Meili, "search", return_value={"hits": []}) as search, \
             patch.object(web, "model_interpret_question", return_value={
                 "names": [], "district": None, "many_localities": False}), \
             patch.object(web, "model_metadata_searches", return_value=[]):
            self.assertTrue(client.get("/api/v1/filter-options").json["presence_filters_available"])
            self.assertNotIn("has_celne", client.get("/api/v1/filter-options").json["presence_filter_fields"])
            config["presence_filters_version"] = 2
            self.assertIn("has_celne", client.get("/api/v1/filter-options").json["presence_filter_fields"])
            self.assertNotIn("has_poczta", client.get("/api/v1/filter-options").json["presence_filter_fields"])
            config["presence_filters_version"] = 3
            available = client.get("/api/v1/filter-options").json["presence_filter_fields"]
            for field in ("budownictwo_palacowe", "poczta", "stacje_drogi_zelaznej", "handel", "rzemioslo"):
                self.assertIn("has_" + field, available)
            for flag, version in PRESENCE_FIELD_VERSIONS.items():
                if version == 4:
                    self.assertNotIn(flag, available)
            config["presence_filters_version"] = PRESENCE_FILTER_VERSION
            self.assertEqual(set(client.get("/api/v1/filter-options").json["presence_filter_fields"]),
                             set(PRESENCE_FIELDS))
            response = client.get("/api/v1/search", query_string={
                "q": "szkoła", "mode": "text", "has_szkoły": "true", "has_biblioteki": "true"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("has_szkoły = true", search.call_args.args[1]["filter"])
            self.assertIn("has_biblioteki = true", search.call_args.args[1]["filter"])
            response = client.post("/api/v1/chat", json={
                "question": "Jakie były szkoły?", "verify": False,
                "filters": {"has_szkoły": "true", "has_biblioteki": "true"}})
            self.assertEqual(response.status_code, 200)
            self.assertIn("has_szkoły = true", search.call_args.args[1]["filter"])
            self.assertIn("has_biblioteki = true", search.call_args.args[1]["filter"])
            config.pop("presence_filters_version")
            self.assertFalse(client.get("/api/v1/filter-options").json["presence_filters_available"])

    def test_migration_updates_only_existing_ids_flags_and_parish(self):
        flags = {"01-00001": {**presence_flags({"szkoły": ["szkoła"]}),
                              "parafia_katolicka": ["Raszyn"]}}
        docs = {"entries": [{"ID": "01-00001"}],
                "passages": [{"passage_id": "01-00001_p0001", "entry_id": "01-00001"}]}
        config = {"entries_index": "entries", "passages_index": "passages",
                  "counts": {"entries": 1, "passages": 1}}
        meili = Mock()
        def request(method, path, **kwargs):
            if method == "GET" and "?" in path:
                parsed = urlparse(path)
                kind = parsed.path.split("/")[2]
                offset = int(parse_qs(parsed.query)["offset"][0])
                return {"results": docs[kind][offset:offset+1]}
            if method == "GET" and path.endswith("filterable-attributes"):
                return ["entry_id"]
            if method == "GET" and "/documents/" in path:
                return {"_vectors": {"jina": [0.2]}, **flags["01-00001"]}
            return {"taskUid": 1}
        meili.request.side_effect = request
        meili.stats.return_value = {"numberOfDocuments": 1}
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE patches (kind TEXT, identifier TEXT, payload TEXT, "
                       "PRIMARY KEY (kind, identifier))")
            self.assertEqual(stage_documents(meili, config, flags, db, 1), config["counts"])
            update_indexes(meili, config, db, 1, 30, extra_fields=("parafia_katolicka",))
        updates = [call for call in meili.request.call_args_list if call.args[0] == "PUT"]
        self.assertEqual(len(updates), 2)
        for update in updates:
            payload = update.kwargs["body"][0]
            self.assertEqual(set(payload) - set(PRESENCE_FIELDS), {
                "passage_id" if "passages" in update.args[1] else "ID", "parafia_katolicka"})
            self.assertTrue(payload["has_szkoły"])
            self.assertEqual(payload["parafia_katolicka"], ["Raszyn"])
            self.assertNotIn("_vectors", payload)
        settings = [call.kwargs["body"]["filterableAttributes"]
                    for call in meili.request.call_args_list if call.args[0] == "PATCH"]
        self.assertTrue(all("parafia_katolicka" in fields and "entry_id" in fields for fields in settings))

    def test_migration_rejects_unknown_source_before_writes(self):
        meili = Mock()
        meili.request.return_value = {"results": [{"ID": "unknown"}]}
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE patches (kind TEXT, identifier TEXT, payload TEXT)")
            with self.assertRaises(ValueError):
                stage_documents(meili, {"entries_index": "entries"}, {}, db, 10)
        self.assertTrue(all(call.args[0] == "GET" for call in meili.request.call_args_list))


if __name__ == "__main__":
    unittest.main()
