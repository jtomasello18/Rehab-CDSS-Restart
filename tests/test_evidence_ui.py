"""Evidence presentation preserves provenance and safely renders external text."""

import unittest
from html.parser import HTMLParser
from unittest.mock import patch

from professor_aria import branding


CPG = {
    "pmid": "11111111", "title": "Clinical practice guideline for stroke rehabilitation",
    "abstract": "Evidence-based recommendations for rehabilitation.",
    "publication_types": ["Practice Guideline"],
}
SMALL_RCT = {
    "pmid": "22222222", "title": "A randomized controlled trial of gait training",
    "abstract": "Thirty patients were randomized to gait training or a control group.",
    "publication_types": ["Randomized Controlled Trial"],
}


class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class EvidenceCardTests(unittest.TestCase):
    def test_card_displays_appraisal_sample_size_and_pubmed_link(self):
        markup = branding._evidence_card_html(SMALL_RCT)
        self.assertIn("Methodological Appraisal:", markup)
        self.assertIn("N=30", markup)
        self.assertIn("3/5", markup)
        self.assertIn("Level II", markup)
        self.assertIn("https://pubmed.ncbi.nlm.nih.gov/22222222/", markup)
        self.assertIn('class="aria-evidence-filled">★★★</span>', markup)
        self.assertIn('class="aria-evidence-empty">☆☆</span>', markup)
        self.assertIn("Read abstract", markup)

    def test_source_markup_cannot_create_html_or_unsafe_urls(self):
        source = dict(CPG, title='<img src=x onerror="alert(1)"> Clinical practice guideline',
                      abstract="<script>alert('x')</script>", pmid='javascript:alert(1)')
        markup = branding._evidence_card_html(source)
        tags = TagCollector()
        tags.feed(markup)
        self.assertNotIn("img", [tag for tag, _ in tags.tags])
        self.assertNotIn("script", [tag for tag, _ in tags.tags])
        self.assertFalse(any("href" in attrs for _, attrs in tags.tags))
        self.assertIn("&lt;img", markup)
        self.assertIn("&lt;script&gt;", markup)

    def test_legend_precedes_quality_sorted_cards_and_works_without_global_theme(self):
        with patch.object(branding.st, "markdown") as markdown:
            branding.render_evidence_sources([SMALL_RCT, CPG])
        calls = [call.args[0] for call in markdown.call_args_list]
        legend_index = next(i for i, text in enumerate(calls) if '<details class="aria-evidence-legend">' in text)
        cards = [(i, text) for i, text in enumerate(calls) if '<article class="aria-evidence-card">' in text]
        self.assertLess(legend_index, cards[0][0])
        self.assertIn(CPG["title"], cards[0][1])
        self.assertIn(SMALL_RCT["title"], cards[1][1])
        self.assertIn("#f59e0b", calls[0])
        self.assertIn("#cbd5e1", calls[0])
        self.assertIn("not a full GRADE certainty or PEDro assessment", calls[legend_index])


class GuidanceBadgeTests(unittest.TestCase):
    def test_guidance_includes_its_own_scoped_styles(self):
        with patch.object(branding.st, "markdown") as markdown:
            branding.render_guidance_markdown("Plan (PMID: 11111111)", [CPG])
        self.assertEqual(markdown.call_args_list[0].args[0], branding.EVIDENCE_STYLE)
        self.assertIn('class="aria-evidence-citation"', markdown.call_args_list[1].args[0])

    def test_known_source_gets_its_real_grade_and_markdown_is_preserved(self):
        markup = branding._guidance_markup(
            "### Plan\n\n- **Train gait** (PMID: 22222222 · ★★★★★ 5/5 · CPG)", [SMALL_RCT],
        )
        self.assertIn("### Plan\n\n- **Train gait**", markup)
        self.assertIn('class="aria-evidence-citation"', markup)
        self.assertIn('class="aria-evidence-score">3/5</span>', markup)
        self.assertIn("N=30", markup)
        self.assertNotIn("5/5", markup)

    def test_unknown_pmid_does_not_inherit_a_model_supplied_grade(self):
        markup = branding._guidance_markup("(PMID: 99999999 · ★★★★★ 5/5 · CPG)", [CPG])
        self.assertIn("not in retrieved evidence", markup)
        self.assertNotIn("aria-evidence-citation", markup)
        self.assertNotIn("★★★★★", markup)

    def test_model_html_is_escaped_while_blockquotes_and_lists_remain_markdown(self):
        markup = branding._guidance_markup(
            '> **Safety**\n\n- Review <img src=x onerror="alert(1)"> (PMID: 11111111)', [CPG],
        )
        self.assertIn("> **Safety**", markup)
        self.assertIn("- Review &lt;img", markup)
        tags = TagCollector()
        tags.feed(markup)
        self.assertNotIn("img", [tag for tag, _ in tags.tags])
        self.assertTrue(any(tag == "a" for tag, _ in tags.tags))

    def test_code_spans_and_fences_do_not_become_evidence_badges(self):
        citation = "(PMID: 11111111 · ★★★★★ 5/5 · CPG)"
        text = f"`{citation}`\n\n```text\n{citation}\n```"
        self.assertEqual(branding._guidance_markup(text, [CPG]), text)


if __name__ == "__main__":
    unittest.main()
