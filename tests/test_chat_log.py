"""Completed chat traces remain isolated and contain no request credentials."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from flask import Flask, Response

import sgkp_chat_log as logs


class ChatLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "chat.log"
        self.path_patch = patch.object(logs, "CHAT_LOG_PATH", self.path)
        self.path_patch.start()
        self.env = patch.dict(os.environ, {"CHAT_DEBUG": "true"})
        self.env.start()
        self.app = Flask(__name__)

        @self.app.post("/chat")
        @logs.traced_chat
        def chat():
            @logs.timed_stage("wyszukiwanie")
            def search():
                return []
            search()
            def chunks():
                logs.record("Qwen", 0.12, thinking=False)
                yield "first"
                logs.record("Qwen", 0.34, thinking=True)
                yield "second"
            return Response(chunks())

        @self.app.post("/error")
        @logs.traced_chat
        def error():
            raise ValueError("failed")
        self.app.testing = True

    def tearDown(self):
        self.env.stop()
        self.path_patch.stop()
        self.tmp.cleanup()

    def test_block_written_after_stream_and_contains_settings(self):
        response = self.app.test_client().post("/chat", json={
            "question": "Źródła?", "filters": {"tom": "01"}, "verify": True},
            headers={"Authorization": "Bearer secret-value"}, buffered=False)
        self.assertFalse(self.path.exists())
        self.assertEqual(response.get_data(as_text=True), "firstsecond")
        response.close()
        content = self.path.read_text()
        self.assertIn("Źródła?", content)
        self.assertIn('"tom": "01"', content)
        self.assertIn('"weryfikacja_zadana": true', content)
        self.assertIn('"thinking": false', content)
        self.assertIn('"thinking": true', content)
        self.assertIn("czas_calkowity_s=", content)
        self.assertNotIn("secret-value", content)
        self.assertEqual(content.count("=== CHAT"), 1)
        self.assertTrue(content.endswith("\n\n"))

    def test_disabled_creates_no_file(self):
        with patch.dict(os.environ, {"CHAT_DEBUG": "false"}):
            response = self.app.test_client().post("/chat", json={"question": "test"})
            response.get_data()
            response.close()
        self.assertFalse(self.path.exists())

    def test_interleaved_streams_stay_in_separate_blocks(self):
        client = self.app.test_client()
        first = client.post("/chat", json={"question": "first-question"}, buffered=False)
        second = client.post("/chat", json={"question": "second-question"}, buffered=False)
        second.get_data()
        first.get_data()
        blocks = self.path.read_text().strip().split("\n\n")
        self.assertEqual(len(blocks), 2)
        self.assertIn("second-question", blocks[0])
        self.assertNotIn("first-question", blocks[0])
        self.assertIn("first-question", blocks[1])
        self.assertEqual(blocks[0].count('"etap": "Qwen"'), 2)
        self.assertEqual(blocks[1].count('"etap": "Qwen"'), 2)
        self.assertIsNone(logs._current.get())

    def test_error_is_logged(self):
        with self.assertRaises(ValueError):
            self.app.test_client().post("/error", json={"question": "error-question"})
        self.assertIn("status=ValueError", self.path.read_text())
        self.assertIsNone(logs._current.get())

    def test_early_close_is_logged_as_interrupted(self):
        response = self.app.test_client().post("/chat", json={"question": "cancelled"}, buffered=False)
        response.close()
        self.assertIn("status=interrupted", self.path.read_text())
