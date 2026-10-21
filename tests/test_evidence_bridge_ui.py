"""Exercise native uploads, removal, disk detection, exact citations, and routing."""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from streamlit.testing.v1 import AppTest

import evidence_bridge
from professor_aria import branding, knowledge_base
from professor_aria.knowledge_citations import format_knowledge_citation


def text_pdf(text="Thirty patients were randomized to gait training or control."):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream.set_data(f"BT /F1 12 Tf 50 700 Td ({escaped}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class Upload:
    def __init__(self, name, data):
        self.name, self.data = name, data

    def getvalue(self):
        return self.data


class NativeBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        patcher = patch.object(knowledge_base, "DEFAULT_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def app(self):
        return AppTest.from_string("from evidence_bridge import render_evidence_bridge\nrender_evidence_bridge()")

    def test_native_view_is_empty_until_real_pdf_is_copied_on_disk(self):
        app = self.app().run()
        self.assertFalse(app.exception)
        markup = "\n".join(item.value for item in app.markdown)
        self.assertNotIn("AHA/ASA Stroke Guidelines", markup)
        self.assertIn("No Active Documents — Upload a clinical study or CPG PDF above to populate the knowledge base.", markup)
        self.assertNotIn("High-Intensity Gait Training 2026.pdf", markup)
        (self.root / "Real gait trial.pdf").write_bytes(text_pdf())
        app.run()
        self.assertFalse(app.exception)
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("Real gait trial.pdf", markup)
        self.assertIn("User Uploaded · 1 pages", markup)
        self.assertEqual(len(app.button), 1)
        self.assertEqual(app.chat_input[0].placeholder, "Ask ARIA about your uploaded studies and CPG PDFs...")

    def test_real_upload_persists_once_and_failed_file_does_not_block_valid_file(self):
        uploads = [Upload("Broken.pdf", b"not a pdf"), Upload("Gait RCT.pdf", text_pdf())]
        with patch.object(evidence_bridge.st, "file_uploader", return_value=uploads), \
             patch.object(evidence_bridge, "ingest_pdf", wraps=knowledge_base.ingest_pdf) as ingest, \
             patch.object(evidence_bridge.st, "toast") as toast:
            app = self.app().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 1)
            app.run()
            self.assertFalse(app.exception)
        self.assertEqual(ingest.call_count, 2)
        self.assertEqual(toast.call_count, 1)
        self.assertEqual([doc["filename"] for doc in knowledge_base.list_documents() if doc["source_type"] == "uploaded_pdf"], ["Gait RCT.pdf"])
        self.assertTrue((self.root / "Gait RCT.pdf").exists())

    def test_remove_resets_selected_uploads_and_clears_stale_answer_history(self):
        upload = Upload("Remove me.pdf", text_pdf())
        def selected_files(*args, **kwargs):
            return [upload] if kwargs["key"] == "bridge_upload_0" else []
        with patch.object(evidence_bridge.st, "file_uploader", side_effect=selected_files):
            app = self.app().run()
            self.assertFalse(app.exception)
            app.session_state["bridge_history"] = [{"role": "user", "content": "Old question"}]
            app.button[0].click().run()
            self.assertFalse(app.exception)
            app.run()
        self.assertFalse((self.root / "Remove me.pdf").exists())
        self.assertEqual(app.session_state["bridge_upload_generation"], 1)
        self.assertEqual(app.session_state["bridge_history"], [])

    def test_query_calls_real_interface_and_displays_exact_page_quote(self):
        knowledge_base.ingest_pdf("Gait RCT.pdf", text_pdf())
        source = knowledge_base.search_knowledge_base("gait training")[0]
        passage = source["passages"][0]
        # Prefer the uploaded source if a curated reference also matches gait.
        source = next(s for s in knowledge_base.search_knowledge_base("Gait RCT.pdf gait training") if s["source_type"] == "uploaded_pdf")
        passage = source["passages"][0]
        result = {"answer": "The trial randomized thirty patients. " + format_knowledge_citation(source, passage),
                  "sources": [source], "citations": [{"source": source, "passage": passage, "quote": passage["text"]}], "error": None}
        with patch("professor_aria.knowledge_chat.answer_evidence_question", return_value=result) as answer:
            app = self.app().run()
            app.chat_input[0].set_value("What does the gait RCT report?").run()
        self.assertFalse(app.exception)
        self.assertEqual(answer.call_args.args[0], "What does the gait RCT report?")
        self.assertEqual(answer.call_args.kwargs["history"], [])
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("Citation:</strong>", markup)
        self.assertIn("(Pg. 1)", markup)
        self.assertIn("<strong>Gait RCT.pdf</strong> (Page 1)", markup)
        self.assertIn(passage["text"], markup)
        self.assertIn('class="aria-bridge-answer"', markup)
        self.assertNotIn('class="aria-evidence-citation knowledge"', markup)

    def test_bridge_is_accessible_without_loading_claude_engine(self):
        app = AppTest.from_string("import streamlit as st\nfrom aria_dashboard import render_professor_dashboard\nrender_professor_dashboard(lambda **kwargs: st.error('Unexpected iframe'))")
        app.session_state["view"] = "Evidence Bridge"
        with patch("aria_dashboard._load_professor_engine", side_effect=AssertionError("No clinical engine required")):
            app.run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(any("ARIA - Evidence Bridge" in item.value for item in app.markdown))

    def test_guidance_drawer_counts_and_displays_pubmed_and_local_sources(self):
        knowledge_base.ingest_pdf("Gait RCT.pdf", text_pdf())
        local = knowledge_base.search_knowledge_base("Gait RCT.pdf gait training")
        app = AppTest.from_string("import streamlit as st\nfrom aria_chat import _render_sources\n_render_sources(st.session_state.catalog)")
        app.session_state["catalog"] = {
            "sources": [{"pmid": "123", "title": "Clinical practice guideline for stroke",
                         "abstract": "Rehabilitation recommendations.", "publication_types": ["Practice Guideline"]}],
            "knowledge_sources": local,
        }
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.expander[0].label, f"The evidence I used ({1 + len(local)} source(s))")
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("Source: Evidence Bridge Knowledge Base", markup)
        self.assertIn("https://pubmed.ncbi.nlm.nih.gov/123/", markup)
        self.assertIn("Read retrieved passages", markup)


class KnowledgeEvidencePresentationTests(unittest.TestCase):
    def source(self):
        return {
            "id": "pdf-123", "document_id": "pdf-123", "source_type": "uploaded_pdf",
            "filename": "Trial.pdf", "title": "Gait training: randomized controlled trial",
            "abstract": "Thirty patients were randomized to intervention or control.",
            "publication_types": [], "page_count": 2,
            "passages": [{"id": "pdf-123:p2:0", "passage_id": "pdf-123:p2:0", "page_number": 2,
                          "text": 'Thirty patients were randomized. <script>alert("x")</script>'}],
        }

    def test_local_card_has_provenance_page_and_appraisal_with_no_fake_pmid(self):
        markup = branding._evidence_card_html(self.source())
        self.assertIn("Source: Evidence Bridge Knowledge Base", markup)
        self.assertIn("Methodological Appraisal:", markup)
        self.assertIn("N=30", markup)
        self.assertIn("Page 2", markup)
        self.assertIn("&lt;script&gt;", markup)
        self.assertNotIn("<script>", markup)
        self.assertNotIn("PMID:", markup)
        self.assertNotIn("pubmed.ncbi", markup)

    def test_local_citation_uses_stored_grade_and_rejects_an_invented_page(self):
        source = self.source()
        markup = branding._guidance_markup("Try gait training [KB:pdf-123:p2:0]", [source])
        self.assertIn('class="aria-evidence-citation knowledge"', markup)
        self.assertIn("Trial.pdf, p. 2", markup)
        self.assertIn('class="aria-evidence-score">3/5</span>', markup)
        wrong = branding._guidance_markup("(Uploaded PDF: Trial.pdf, p. 88 · ★★★★★ 5/5)", [source])
        self.assertIn("not in retrieved passages", wrong)
        self.assertNotIn("★★★★★", wrong)

    def test_exact_quote_box_escapes_pdf_metadata_and_text(self):
        markup = evidence_bridge._citation_box_html({"source": dict(self.source(), filename="<img src=x>.pdf"),
                                                    "passage": {"page_number": 2}, "quote": "<script>danger</script>"})
        self.assertIn("(Pg. 2)", markup)
        self.assertIn("&lt;script&gt;", markup)
        self.assertNotIn("<img", markup)
        self.assertNotIn("<script>", markup)

    def test_lookup_bubble_has_one_compact_citation_and_safe_bold_metadata(self):
        source = self.source()
        source['filename'] = '<unsafe>.pdf'
        card = {'source': source, 'passage': source['passages'][0],
                'quote': 'First sentence. Second sentence. Third sentence.'}
        markup = evidence_bridge._answer_bubble_html('A direct answer. [KB:pdf-123:p2:0]', [card, card])
        self.assertEqual(markup.count('class="aria-bridge-answer"'), 1)
        self.assertEqual(markup.count('class="aria-bridge-citation"'), 1)
        self.assertIn('<strong>&lt;unsafe&gt;.pdf</strong> (Page 2)', markup)
        self.assertIn('Citation:</strong> &quot;First sentence. Second sentence.&quot; (Pg. 2)', markup)
        self.assertNotIn('Third sentence', markup)
        self.assertNotIn('<unsafe>', markup)
        self.assertNotIn('aria-evidence-citation', markup)
        self.assertIn('#eef6ff', evidence_bridge.BRIDGE_STYLE)

    def test_primary_source_links_reject_unsafe_schemes_hosts_credentials_and_markup(self):
        unsafe = ["javascript:alert(1)", "data:text/html,<script>bad</script>",
                  "http://www.asha.org/practice-portal/", "https://www.asha.org.evil.example/path",
                  "https://evil.example/", "https://user@www.asha.org/", "https://www.asha.org:444/",
                  'https://www.asha.org/\" onclick=\"alert(1)', "https://www.asha.org/\n"]
        for url in unsafe:
            with self.subTest(url=url):
                self.assertEqual(branding._safe_primary_reference_url(url), "")
        source = dict(self.source(), source_type="builtin_reference", title="Reference summary",
                      url=unsafe[0], references=[{"title": "<script>bad</script>", "url": url} for url in unsafe])
        passage = {"section": "Summary", "text": "A relevant reference summary.", "url": unsafe[0]}
        source["passages"] = [passage]
        self.assertNotIn("href=", branding._evidence_card_html(source))
        self.assertNotIn("href=", evidence_bridge._citation_box_html({"source": source, "passage": passage, "quote": passage["text"]}))
        self.assertEqual(branding._primary_reference_links_html(dict(self.source(), url="https://www.asha.org/")), "")


if __name__ == "__main__":
    unittest.main()
