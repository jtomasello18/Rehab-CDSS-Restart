"""Metadata, source ordering, and graded synthesis stay consistent end to end."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')

from professor_aria import rag, literacy_engine
from professor_aria.evidence_citations import canonicalize_citations, format_citation


SOURCES = [
    {'pmid': '30', 'title': 'Gait training: a randomized controlled trial',
     'abstract': 'Thirty patients were randomly assigned to treatment or control.',
     'publication_types': ['Randomized Controlled Trial']},
    {'pmid': '50', 'title': 'Clinical practice guideline for stroke rehabilitation',
     'abstract': 'Recommendations for rehabilitation.', 'publication_types': ['Practice Guideline']},
    {'pmid': '80', 'title': 'Multicenter randomized controlled trial of walking',
     'abstract': 'A total of 100 patients were randomized to treatment or control.',
     'publication_types': ['Randomized Controlled Trial', 'Multicenter Study']},
]


def response(text):
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)])


class MetadataAndOrderingTests(unittest.TestCase):
    def test_pubmed_design_metadata_preserved_and_appraised(self):
        xml = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>30</PMID><Article>
        <Journal><Title>Rehabilitation Journal</Title></Journal>
        <ArticleTitle>Gait training: randomized controlled trial</ArticleTitle>
        <Abstract><AbstractText>Thirty patients were randomized to treatment or control.</AbstractText></Abstract>
        <PublicationTypeList><PublicationType UI="D016449">Randomized Controlled Trial</PublicationType>
        <PublicationType>Clinical Trial</PublicationType></PublicationTypeList></Article>
        <MeshHeadingList><MeshHeading><DescriptorName>Humans</DescriptorName></MeshHeading></MeshHeadingList>
        </MedlineCitation></PubmedArticle></PubmedArticleSet>'''
        with patch.object(rag, '_pubmed_get', return_value=SimpleNamespace(content=xml)):
            paper = rag.fetch_article_details(['30'])[0]
        self.assertIn('Randomized Controlled Trial', paper['publication_types'])
        self.assertIn('Humans', paper['mesh_terms'])
        self.assertEqual(paper['journal'], 'Rehabilitation Journal')
        self.assertEqual(paper['star_rating'], 3)
        self.assertEqual(paper['sample_size'], 30)

    def test_quality_sort_before_cap_and_final_display_preserves_facets(self):
        plans = [
            {'facet': 'rehabilitation', 'query': 'rehab', 'fallback_queries': []},
            {'facet': 'medication_safety', 'query': 'safety', 'fallback_queries': []},
        ]
        by_query = {'rehab': ['30', '50'], 'safety': ['80']}
        with patch.object(rag, 'build_smart_query', return_value={'queries': plans, 'rationale': 'test'}), patch.object(rag, 'search_pubmed', side_effect=lambda q, n: by_query[q]), patch.object(rag, 'fetch_article_details', return_value=SOURCES):
            result = rag.retrieve_literature_smart('stroke', {'diagnosis': 'stroke'}, max_results=2)
        self.assertEqual([s['pmid'] for s in result['sources']], ['50', '80'])
        self.assertEqual([s['star_rating'] for s in result['sources']], [5, 4])
        self.assertEqual([s['retrieved_count'] for s in result['searches']], [1, 1])

    def test_higher_quality_guideline_not_discarded_just_because_it_is_a_book_record(self):
        articles = [dict(SOURCES[0], source_type='journal_article'), dict(SOURCES[1], source_type='book_chapter')]
        plans = [{'facet': 'rehabilitation', 'query': 'rehab', 'fallback_queries': []}]
        with patch.object(rag, 'build_smart_query', return_value={'queries': plans, 'rationale': 'test'}), patch.object(rag, 'search_pubmed', return_value=['30', '50']), patch.object(rag, 'fetch_article_details', return_value=articles):
            result = rag.retrieve_literature_smart('stroke', {'diagnosis': 'stroke'}, max_results=1)
        self.assertEqual(result['sources'][0]['pmid'], '50')


class CitationTests(unittest.TestCase):
    def test_exact_small_rct_citation(self):
        self.assertEqual(format_citation(SOURCES[0]), '(PMID: 30 · ★★★☆☆ 3/5 · Small RCT, N=30)')

    def test_wrong_model_grade_corrected_and_grouped_pmids_supported(self):
        text = 'Try walking (PMID: 30 · ★★★★★ 5/5 · CPG). Compare [PMIDs: 50, 80].'
        result = canonicalize_citations(text, SOURCES)
        self.assertIn('(PMID: 30 · ★★★☆☆ 3/5 · Small RCT, N=30)', result)
        self.assertIn('(PMID: 50 · ★★★★★ 5/5 · CPG)', result)
        self.assertIn('PMID: 80 · ★★★★☆ 4/5', result)
        self.assertNotIn('PMID: 30 · ★★★★★', result)

    def test_unknown_pmid_never_given_a_fabricated_grade(self):
        result = canonicalize_citations('PMID: 99999999', SOURCES)
        self.assertEqual(result, '(PMID: 99999999 · not in retrieved evidence)')

    def test_unparenthesized_model_grade_is_corrected_without_duplicate_stars(self):
        result = canonicalize_citations('PMID: 30 · ★★★★★ 5/5 · CPG.', SOURCES)
        self.assertEqual(result, format_citation(SOURCES[0]) + '.')

    def test_multiple_decorated_citations_and_and_lists_preserve_every_pmid(self):
        for text in ('(PMID: 30 · ★★★★★ 5/5 · CPG; PMID: 50 · ★☆☆☆☆ 1/5 · Case Report)', '(PMIDs: 30 and 50)'):
            with self.subTest(text=text):
                result = canonicalize_citations(text, SOURCES)
                self.assertIn(format_citation(SOURCES[0]), result)
                self.assertIn(format_citation(SOURCES[1]), result)

    def test_markdown_pmid_link_does_not_leave_an_orphaned_model_url(self):
        result = canonicalize_citations('[PMID: 30](https://example.com/unverified)', SOURCES)
        self.assertEqual(result, format_citation(SOURCES[0]))

    def test_title_links_and_bare_pubmed_urls_get_source_grades(self):
        result = canonicalize_citations('See [Small trial](https://pubmed.ncbi.nlm.nih.gov/30/) and https://pubmed.ncbi.nlm.nih.gov/50/.', SOURCES)
        self.assertIn('Small trial ' + format_citation(SOURCES[0]), result)
        self.assertIn(format_citation(SOURCES[1]), result)

    def test_code_examples_untouched_and_canonicalization_idempotent(self):
        text = 'Evidence (PMID: 30). `PMID: 123`\n```\nPMID: 456\n```'
        result = canonicalize_citations(text, SOURCES)
        self.assertIn('`PMID: 123`', result)
        self.assertIn('```\nPMID: 456\n```', result)
        self.assertEqual(canonicalize_citations(result, SOURCES), result)


class SynthesisTests(unittest.TestCase):
    def test_initial_synthesis_receives_appraisals_instructions_and_canonical_citations(self):
        with patch.object(literacy_engine.client.messages, 'create', return_value=response('Walking (PMID: 30).')) as create:
            result = literacy_engine.generate_response({'diagnosis': 'stroke'}, {'sources': SOURCES}, 'stroke note', tier=2)
        kwargs = create.call_args.kwargs
        prompt = kwargs['messages'][0]['content']
        self.assertIn('NEVER treat all retrieved PubMed papers as equal weight', kwargs['system'])
        self.assertIn('N>=50 does not establish statistical power', kwargs['system'])
        self.assertIn('Methodological appraisal:', prompt)
        self.assertIn('Level I-A', prompt)
        self.assertIn('N=30', prompt)
        self.assertLess(prompt.index('PMID: 50'), prompt.index('PMID: 30'))
        self.assertIn('★★★☆☆ 3/5', result['response_text'])

    def test_followup_preserves_catalog_and_corrects_model_grade(self):
        history = [{'role': 'user', 'content': 'What about the small trial?'}]
        with patch.object(literacy_engine.client.messages, 'create', return_value=response('Supplementary (PMID: 30 · ★★★★★ 5/5 · CPG).')) as create:
            result = literacy_engine.continue_conversation(history, 2, literature={'sources': SOURCES, 'note': 'Some evidence gaps.'})
        system = create.call_args.kwargs['system']
        self.assertIn('Retrieved evidence catalog:', system)
        self.assertIn('Small RCT', system)
        self.assertIn('Some evidence gaps.', system)
        self.assertIn('★★★☆☆ 3/5', result)
        self.assertNotIn('★★★★★ 5/5', result)
        self.assertEqual(history, [{'role': 'user', 'content': 'What about the small trial?'}])


if __name__ == '__main__':
    unittest.main()
