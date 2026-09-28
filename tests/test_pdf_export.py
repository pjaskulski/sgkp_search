"""PDF conversation export API and document checks."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from app import app


class PdfExportTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_export_contains_full_conversation_and_scan_link(self):
        turns = [
            {"question": "Gdzie były źródła siarczane?",
             "answer": "1. **Warmbrunn** miał źródła siarczane [1].\n2. *Rabka* miała kąpiele [2].",
             "sources": [
                 {"citation": 1, "nazwa": "Warmbrunn", "tom": "13", "strona": 5},
                 {"citation": 2, "nazwa": "Rabka ze Słonką", "tom": "09", "strona": 343},
             ], "provider": "local", "model": "qwen3.8-flash-next-fp8"},
            {"question": "Czy wspomniano o kościele?",
             "answer": "Nie ma o nim danych w przywołanym fragmencie.",
             "sources": [], "provider": "openai", "model": "gpt-6-luna"},
        ]
        response = self.client.post("/api/v1/chat/export", json={"turns": turns})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertTrue(response.data.startswith(b"%PDF-"))
        if shutil.which("pdftotext") and shutil.which("pdfinfo"):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "conversation.pdf"
                path.write_bytes(response.data)
                extracted = subprocess.run(["pdftotext", str(path), "-"], capture_output=True,
                                           text=True, check=True).stdout
                links = subprocess.run(["pdfinfo", "-url", str(path)], capture_output=True,
                                       text=True, check=True).stdout
            self.assertIn("źródła siarczane", extracted)
            self.assertIn("Czy wspomniano o kościele?", extracted)
            self.assertIn("Rabka ze Słonką", extracted)
            self.assertIn("Tom_XIII/5", links)
            self.assertIn("Tom_IX/343", links)

    def test_export_rejects_missing_turns_and_malformed_source(self):
        turn = {"question": "Gdzie?", "answer": "Tam [1].",
                "sources": [{"citation": 1, "nazwa": "Zawady", "tom": "14", "strona": 479}]}
        for payload in ({"turns": []}, {"turns": [{**turn, "sources": [{**turn["sources"][0],
                                                                       "citation": "1"}]}]},
                        {"turns": [{**turn, "answer": "x" * 40_001}]}):
            response = self.client.post("/api/v1/chat/export", json=payload)
            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
