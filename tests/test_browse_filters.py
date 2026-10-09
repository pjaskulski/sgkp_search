import unittest
from unittest.mock import patch

import app as web


class BrowseFiltersTests(unittest.TestCase):
    def setUp(self):
        web.cached_browse_entries.cache_clear()
        self.rows = [
            {"ID": "01-00002", "nazwa": "Zbiorcze", "rodzaj": "zbiorcze", "tom": "01", "strona": 10,
             "powiat_ujednolicony": "rodzic", "archeo": ["znalezisko rodzica"], "elementy": [
                 {"ID": "01-00002-001", "nazwa": "Wieś A", "nr": "1", "text": "Opis A.",
                  "markdown": "**Wieś A**, opis.", "tom": "16", "strona": 999,
                  "typ_punktu_osadniczego": ["wieś"], "powiat_ujednolicony": "warszawski",
                  "gmina": ["Gmina A"], "parafia_katolicka": ["Parafia A"], "archeo": ["kurhan"]},
                 {"ID": "01-00002-002", "nazwa": "Rzeka B", "nr": "2", "text": "Opis B.", "typ": ["rzeka"]}]},
            {"ID": "01-00001", "nazwa": "Wieś C", "rodzaj": "indywidualne", "tom": "01", "strona": 9,
             "text": "Opis C.", "typ_punktu_osadniczego": ["wieś"], "powiat_ujednolicony": "wileński"},
        ]

    def tearDown(self):
        web.cached_browse_entries.cache_clear()

    def test_atomic_entries_parent_page_and_child_metadata(self):
        with patch.object(web, "cached_volume", return_value=self.rows):
            entries = web.cached_browse_entries("/tmp/browse-test", "test", "01")
        self.assertEqual([entry["ID"] for entry in entries],
                         ["01-00001", "01-00002-001", "01-00002-002"])
        child = entries[1]
        self.assertEqual((child["tom"], child["strona"]), ("01", 10))
        self.assertEqual(child["parent_id"], "01-00002")
        self.assertEqual(child["rodzaj"], "element")
        self.assertTrue(child["preview_is_markdown"])
        self.assertEqual(child["powiat_ujednolicony"], "warszawski")
        self.assertTrue(child["has_archeo"])
        self.assertFalse(entries[2]["has_archeo"])

    def test_filters_apply_before_count_and_pagination(self):
        with patch.object(web, "cached_volume", return_value=self.rows), \
             patch.object(web, "manifest", return_value={"source_dir": "/tmp/browse-test", "created_at": "test"}):
            client = web.app.test_client()
            result = client.get("/api/v1/browse", query_string={"tom": "01"}).json
            self.assertEqual(result["estimated_total_hits"], 3)
            result = client.get("/api/v1/browse", query_string={"tom": "01", "name": "WIEŚ",
                "jest_miejscowoscia": "true", "powiat_ujednolicony": "warszawski",
                "gmina": "Gmina A", "parafia_katolicka": "Parafia A", "has_archeo": "true"}).json
            self.assertEqual(result["estimated_total_hits"], 1)
            self.assertEqual(result["hits"][0]["ID"], "01-00002-001")
            self.assertEqual(result["hits"][0]["strona"], 10)
            self.assertNotIn("source_file", result["hits"][0])
            self.assertEqual(client.get("/api/v1/browse", query_string={"has_archeo": "invalid"}).status_code, 400)

    def test_all_volumes_are_sorted_by_id(self):
        def entries(_, __, volume):
            return ({"ID": volume + "-00001", "nazwa": "A", "tom": volume, "strona": 1},)
        with patch.object(web, "cached_browse_entries", side_effect=entries), \
             patch.object(web, "manifest", return_value={"source_dir": "/tmp"}):
            result = web.app.test_client().get("/api/v1/browse", query_string={"tom": ""}).json
        self.assertEqual(result["estimated_total_hits"], 16)
        self.assertEqual(result["hits"][0]["tom"], "01")
        self.assertEqual(result["hits"][-1]["tom"], "16")


if __name__ == "__main__":
    unittest.main()
