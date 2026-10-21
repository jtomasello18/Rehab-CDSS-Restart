"""Retired curated references must never enter active retrieval."""
import tempfile
import unittest
from professor_aria.builtin_knowledge import BUILTIN_DOCUMENTS
from professor_aria.knowledge_base import list_documents, search_knowledge_base

class UploadedOnlyKnowledgeTests(unittest.TestCase):
    def test_no_bundled_documents_remain(self):
        self.assertEqual(BUILTIN_DOCUMENTS, [])
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(list_documents(root), [])
            self.assertEqual(search_knowledge_base("AHA/ASA Stroke Guidelines aerobic exercise", root=root), [])
