"""Input length caps preserve accepted evidence and valid citation numbering."""
import os
import unittest
from unittest.mock import patch

import app as web


def source(i, texts):
    ids = [f"entry{i}_p{j:04d}" for j in range(len(texts))]
    return {"entry_id": f"entry{i}", "nazwa": f"Name {i}", "tom": "01", "strona": 1,
            "jest_miejscowoscia": True, "powiat_ujednolicony": None,
            "królestwo_polskie": True, "passage_id": ids[0], "passage_ids": ids,
            "text": "\n\n".join(texts), "_evidence_passages": list(zip(ids, texts))}


class ChatContextTests(unittest.TestCase):
    def test_all_verified_sources_and_full_passages_are_included(self):
        sources = [source(i, ["x" * 1800 + f"END{i}"]) for i in range(30)]
        with patch.dict(os.environ, {"CHAT_MAX_INPUT_CHARS": "300000"}):
            messages, retained, truncated = web.prepare_chat_context("Instructions", "Question", "", sources, True)
        self.assertEqual(len(retained), 30)
        self.assertIn("END29", messages[1]["content"])
        self.assertFalse(truncated)
        self.assertNotIn("_evidence_passages", retained[0])

    def test_actual_message_contents_never_exceed_cap(self):
        sources = [source(i, ["x" * 300, "y" * 300]) for i in range(10)]
        with patch.dict(os.environ, {"CHAT_MAX_INPUT_CHARS": "1000"}):
            messages, retained, truncated = web.prepare_chat_context("Instructions", "Question", "history", sources, True)
        self.assertTrue(truncated)
        self.assertLessEqual(sum(len(m["content"]) for m in messages), 1000)
        self.assertIn("[1]", messages[1]["content"])
        self.assertNotIn(f"[{len(retained) + 1}]", messages[1]["content"])

    def test_clipped_passages_are_not_reported_as_sent(self):
        item = source(0, ["a" * 500, "b" * 500, "c" * 500])
        with patch.dict(os.environ, {"CHAT_MAX_INPUT_CHARS": "1000"}):
            messages, retained, truncated = web.prepare_chat_context("Instructions", "Question", "", [item], True)
        self.assertTrue(truncated)
        self.assertEqual(len(retained[0]["passage_ids"]), 2)
        self.assertNotIn("entry0_p0002", messages[1]["content"])
        self.assertNotIn("c", retained[0]["text"])
        self.assertEqual(sum(len(m["content"]) for m in messages), 1000)

    def test_long_history_and_metadata_are_included_in_budget(self):
        item = source(0, ["text"])
        item["archeo"] = ["huge metadata" * 100]
        with patch.dict(os.environ, {"CHAT_MAX_INPUT_CHARS": "800"}):
            with self.assertRaises(web.ServiceError):
                web.prepare_chat_context("Instructions", "Question", "history" * 1000, [item], True)

    def test_unverified_evidence_keeps_existing_excerpt_length(self):
        with patch.dict(os.environ, {"CHAT_MAX_INPUT_CHARS": "300000"}):
            _, retained, truncated = web.prepare_chat_context(
                "Instructions", "Question", "", [source(0, ["x" * 3000])], False)
        self.assertEqual(retained[0]["text"], web.source_excerpt("x" * 3000, "Question", web.CHAT_EVIDENCE_CHARS))
        self.assertFalse(truncated)

    def test_invalid_limit_is_rejected(self):
        for value in ("0", "-1", "invalid"):
            with patch.dict(os.environ, {"CHAT_MAX_INPUT_CHARS": value}):
                with self.assertRaises(ValueError):
                    web.chat_context_limit()
