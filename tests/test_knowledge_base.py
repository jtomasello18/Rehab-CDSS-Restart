"""Local PDF ingestion and retrieval, including exact-page and storage safety."""

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from professor_aria.knowledge_base import (
    KnowledgeBaseError,
    format_kb_citation,
    get_document_bytes,
    ingest_pdf,
    list_documents,
    remove_document,
    search_knowledge_base,
)


def pdf_bytes(pages, title="", password=None):
    writer = PdfWriter()
    if title:
        writer.add_metadata({"/Title": title})
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
        })
        if text:
            stream = DecodedStreamObject()
            lines = []
            for line in text.splitlines():
                escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                lines.append(f"({escaped}) Tj 0 -14 Td")
            stream.set_data(("BT /F1 12 Tf 50 750 Td " + " ".join(lines) + " ET").encode("latin-1"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    if password:
        writer.encrypt(password)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_persists_original_pdf_page_text_and_methodological_appraisal(self):
        data = pdf_bytes([
            "A randomized controlled trial of gait training\nThirty patients were randomly assigned to treatment or control.",
            "Walking speed improved after six weeks. Falls and sedation were monitored.",
        ])
        document = ingest_pdf("Gait Trial.pdf", data, self.root)
        self.assertEqual(document["page_count"], 2)
        self.assertEqual(document["sample_size"], 30)
        self.assertEqual(document["star_rating"], 3)
        self.assertIn("small sample size", document["appraisal_rationale"])
        self.assertIn("Walking speed", document["pages_text"][2])
        self.assertTrue(document["upload_time"])
        self.assertEqual(get_document_bytes(document["document_id"], self.root), data)
        rescanned = list_documents(self.root)
        self.assertEqual(len(rescanned), 1)
        self.assertEqual(rescanned[0]["pages_text"], document["pages_text"])
        self.assertEqual(rescanned[0]["upload_time"], document["upload_time"])
        metadata = json.loads(next(self.root.glob("*.aria.json")).read_text())
        self.assertEqual(metadata["document_id"], document["document_id"])

    def test_identical_contents_deduplicate_and_conflicting_filenames_are_preserved(self):
        first_data = pdf_bytes(["Stroke walking and balance rehabilitation."])
        first = ingest_pdf("Study.pdf", first_data, self.root)
        duplicate = ingest_pdf("Renamed Study.pdf", first_data, self.root)
        self.assertEqual(first["document_id"], duplicate["document_id"])
        self.assertEqual(len(list(self.root.glob("*.pdf"))), 1)
        second_data = pdf_bytes(["Spasticity management and baclofen-associated sedation."])
        second = ingest_pdf("Study.pdf", second_data, self.root)
        self.assertNotEqual(first["stored_filename"], second["stored_filename"])
        self.assertEqual(second["filename"], second["stored_filename"])
        self.assertEqual(second["original_filename"], "Study.pdf")
        self.assertEqual(get_document_bytes(first["document_id"], self.root), first_data)
        self.assertEqual(get_document_bytes(second["document_id"], self.root), second_data)
        self.assertEqual(len(list_documents(self.root)), 2)

    def test_external_pdf_is_discovered_and_deleted_original_does_not_reappear_from_sidecar(self):
        (self.root / "External.pdf").write_bytes(pdf_bytes(["Stroke spasticity rehabilitation."]))
        documents = list_documents(self.root)
        self.assertEqual(len(documents), 1)
        self.assertTrue((self.root / "External.pdf.aria.json").exists())
        (self.root / "External.pdf").unlink()
        self.assertEqual(list_documents(self.root), [])

    def test_external_modification_and_corrupt_sidecar_are_reindexed(self):
        doc = ingest_pdf("Study.pdf", pdf_bytes(["Stroke walking rehabilitation."]), self.root)
        (self.root / "Study.pdf.aria.json").write_text("not valid JSON")
        self.assertEqual(list_documents(self.root)[0]["document_id"], doc["document_id"])
        (self.root / "Study.pdf").write_bytes(pdf_bytes(["Stroke baclofen medication safety and sedation."]))
        replacement = list_documents(self.root)[0]
        self.assertNotEqual(replacement["content_hash"], doc["content_hash"])
        self.assertIn("baclofen", replacement["pages_text"][1])

    def test_remove_uploaded_document_removes_pdf_sidecar_and_retrieval(self):
        doc = ingest_pdf("Gait.pdf", pdf_bytes(["Gait training after stroke."]), self.root)
        self.assertTrue(search_knowledge_base("stroke gait", root=self.root))
        remove_document(doc["document_id"], self.root)
        self.assertEqual(list_documents(self.root), [])
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(search_knowledge_base("stroke gait", root=self.root), [])
        with self.assertRaises(KnowledgeBaseError):
            get_document_bytes(doc["document_id"], self.root)
        with self.assertRaises(KnowledgeBaseError):
            remove_document("builtin-aha-asa", self.root)

    def test_invalid_encrypted_and_image_only_uploads_fail_before_storage(self):
        cases = (
            (b"", "empty"),
            (b"not a pdf", "not a valid PDF"),
            (b"%PDF-1.7\nbroken", "could not be read"),
            (pdf_bytes([""]), "OCR"),
            (pdf_bytes(["Stroke rehabilitation"], password="secret"), "password-protected"),
        )
        for data, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(KnowledgeBaseError, message):
                    ingest_pdf("Bad.pdf", data, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_external_pdf_has_visible_error_but_is_never_retrieved(self):
        (self.root / "Corrupted.pdf").write_bytes(b"invalid")
        docs = list_documents(self.root)
        self.assertEqual(len(docs), 1)
        self.assertIn("not a valid PDF", docs[0]["extraction_error"])
        self.assertEqual(search_knowledge_base("Corrupted.pdf", root=self.root), [])
        remove_document(docs[0]["document_id"], self.root)
        self.assertEqual(list_documents(self.root), [])

    def test_empty_pages_are_reported_without_fabricating_text_or_losing_page_numbers(self):
        doc = ingest_pdf("Mixed.pdf", pdf_bytes(["Gait rehabilitation", "", "Stroke falls safety"]), self.root)
        self.assertEqual(doc["page_count"], 3)
        self.assertEqual(doc["pages_text"][2], "")
        self.assertIn("2", doc["extraction_warnings"][0])
        self.assertEqual(search_knowledge_base("Mixed.pdf page 2", root=self.root), [])
        source = search_knowledge_base("Mixed.pdf page 3", root=self.root)[0]
        self.assertEqual(source["passages"][0]["page_number"], 3)

    def test_limits_are_actionable_and_prevent_oversized_storage(self):
        with patch("professor_aria.knowledge_base.MAX_PDF_BYTES", 5):
            with self.assertRaisesRegex(KnowledgeBaseError, "upload limit"):
                ingest_pdf("Large.pdf", b"%PDF-1.7 large", self.root)
        with patch("professor_aria.knowledge_base.MAX_PDF_PAGES", 1):
            with self.assertRaisesRegex(KnowledgeBaseError, "limit is 1"):
                ingest_pdf("Long.pdf", pdf_bytes(["Stroke", "Gait"]), self.root)
        with patch("professor_aria.knowledge_base.MAX_TEXT_CHARACTERS", 3):
            with self.assertRaisesRegex(KnowledgeBaseError, "too large"):
                ingest_pdf("Huge.pdf", pdf_bytes(["Stroke"]), self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_path_traversal_and_symbolic_links_are_rejected(self):
        data = pdf_bytes(["Stroke gait rehabilitation."])
        for filename in ("../Escape.pdf", "/tmp/Escape.pdf", "folder/Escape.pdf", "folder\\Escape.pdf", "bad\x00.pdf", "File.txt"):
            with self.subTest(filename=filename):
                with self.assertRaises(KnowledgeBaseError):
                    ingest_pdf(filename, data, self.root)
        outside = self.root / "outside.data"
        outside.write_bytes(data)
        (self.root / "Linked.pdf").symlink_to(outside)
        self.assertEqual(list_documents(self.root), [])
        with self.assertRaisesRegex(KnowledgeBaseError, "Symbolic links"):
            ingest_pdf("Linked.pdf", data, self.root)
        target = self.root / "actual"
        target.mkdir()
        linked_root = self.root / "linked-root"
        linked_root.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(KnowledgeBaseError, "symbolic link"):
            list_documents(linked_root)

    def test_retrieval_returns_exact_passages_and_matches_synonyms(self):
        doc = ingest_pdf("Trial.pdf", pdf_bytes([
            "Locomotor rehabilitation improves ambulation after stroke. " * 60,
            "Baclofen may produce sedation. Medication review informs safety during therapy.",
        ]), self.root)
        sources = search_knowledge_base("walking treatment", root=self.root)
        self.assertEqual(len(sources), 1)
        for passage in sources[0]["passages"]:
            self.assertIn(passage["text"], doc["pages_text"][passage["page_number"]])
            self.assertEqual(passage["text"], doc["pages_text"][passage["page_number"]])
        self.assertNotIn("pages_text", sources[0])
        self.assertNotIn("abstract", sources[0])
        self.assertIn("appraisal_text", sources[0])
        safety = search_knowledge_base("baclofen sedation", root=self.root)[0]
        self.assertEqual(safety["passages"][0]["page_number"], 2)

    def test_named_document_and_explicit_page_queries_scope_retrieval(self):
        doc = ingest_pdf("High Intensity Gait.pdf", pdf_bytes([
            "Stroke gait training trial overview.", "Balance and falls outcomes.",
            "Baclofen medication review.", "The exact fourth-page dose was 20 minutes of walking.",
        ]), self.root)
        ingest_pdf("Different.pdf", pdf_bytes(["Stroke gait walking on page four."] * 4), self.root)
        sources = search_knowledge_base("What does High Intensity Gait.pdf say on page 4?", root=self.root)
        self.assertEqual([source["document_id"] for source in sources], [doc["document_id"]])
        self.assertEqual([p["page_number"] for p in sources[0]["passages"]], [4])
        self.assertIn("20 minutes", sources[0]["passages"][0]["text"])
        self.assertEqual(search_knowledge_base("High Intensity Gait.pdf page 99", root=self.root), [])
        self.assertIn("p. 4", format_kb_citation(sources[0]))
        self.assertIn("1/5", format_kb_citation(sources[0]))

    def test_retrieval_limits_passages_and_preserves_document_coverage(self):
        for number in range(5):
            ingest_pdf(f"Trial {number}.pdf", pdf_bytes([
                f"Stroke gait balance report {number}, page {page}. " * 90 for page in range(3)
            ]), self.root)
        sources = search_knowledge_base("stroke gait balance", max_documents=5, max_passages=8, root=self.root)
        self.assertLessEqual(len(sources), 5)
        self.assertGreaterEqual(len(sources), 1)
        self.assertEqual(sum(len(source["passages"]) for source in sources), 8)
        self.assertTrue(all(1 <= len(source["passages"]) <= 8 for source in sources))
        self.assertEqual(search_knowledge_base("stroke", max_documents=0, root=self.root), [])
        self.assertEqual(search_knowledge_base("completelyunrelatedxyz", root=self.root), [])
        self.assertEqual(search_knowledge_base("", root=self.root), [])

    def test_empty_directory_has_no_bundled_guidelines_or_orphan_cache_sources(self):
        (self.root / "Retired.pdf.aria.json").write_text('{"title":"AHA/ASA Stroke Guidelines"}')
        self.assertEqual(list_documents(self.root), [])
        self.assertEqual(search_knowledge_base("stroke walking balance", root=self.root), [])

    def test_overview_questions_retrieve_document_contents_without_narrative_fallback(self):
        doc = ingest_pdf("Trial.pdf", pdf_bytes(["Walking recovery after stroke.", "Detailed methodology."]), self.root)
        sources = search_knowledge_base("Summarize the uploaded PDFs", root=self.root)
        self.assertEqual([source["document_id"] for source in sources], [doc["document_id"]])
        self.assertEqual(sources[0]["passages"][0]["page_number"], 1)
        self.assertIn("Walking recovery", sources[0]["passages"][0]["text"])

    def test_external_identical_copies_do_not_reappear_after_removing_the_document(self):
        data = pdf_bytes(["Stroke gait rehabilitation."])
        (self.root / "Copy A.pdf").write_bytes(data)
        (self.root / "Copy B.pdf").write_bytes(data)
        documents = list_documents(self.root)
        self.assertEqual(len(documents), 1)
        remove_document(documents[0]["document_id"], self.root)
        self.assertEqual(list_documents(self.root), [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_named_pdf_retrieval_has_only_real_pdf_pages(self):
        doc = ingest_pdf("Gait Trial.pdf", pdf_bytes(["Study overview.", "Stroke walking training and balance."]), self.root)
        sources = search_knowledge_base("Cross-reference Gait Trial.pdf page 2 with stroke walking CPGs", root=self.root)
        self.assertEqual({source["document_id"] for source in sources}, {doc["document_id"]})
        self.assertEqual(sources[0]["passages"][0]["page_number"], 2)
        self.assertTrue(all(source["source_type"] == "uploaded_pdf" for source in sources))


if __name__ == "__main__":
    unittest.main()
