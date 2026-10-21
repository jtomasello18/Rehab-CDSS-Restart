"""Grounded document answers, source refresh, and combined synthesis integration."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('ANTHROPIC_API_KEY','test-key')
from professor_aria import knowledge_base as kb, knowledge_chat, literacy_engine, rag
from professor_aria.evidence_appraisal import appraise_article
from professor_aria.knowledge_citations import (
    canonicalize_knowledge_citations, format_knowledge_citation, knowledge_context,
)
from test_knowledge_base import pdf_bytes


class KnowledgeAnswerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.root_patch=patch.object(kb,'DEFAULT_ROOT',self.root)
        self.root_patch.start()
        self.quote='Participants practiced walking three sessions per week for six weeks.'
        self.document=kb.ingest_pdf('Trial.pdf',pdf_bytes([
            'Gait rehabilitation: randomized controlled trial\nSixty patients were randomly assigned to exercise or control.',
            'Balance measurements were collected at baseline.',
            'Adverse events were recorded during supervised rehabilitation.',
            self.quote+' The protocol did not specify a Berg Balance Scale eligibility cutoff.',
        ]))

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def sources(self):
        return kb.search_knowledge_base('Trial.pdf page 4 walking frequency')

    def model(self,payload):
        client=SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(content=[SimpleNamespace(type='text',text=json.dumps(payload))])))
        return patch.object(knowledge_chat,'_client',return_value=client)

    def test_exact_quote_and_physical_page_are_verified_from_real_pdf(self):
        source=self.sources()[0]
        passage=source['passages'][0]
        token=passage['passage_id']
        payload={'answer':f'The trial reports three sessions weekly [KB:{token}]','citations':[{'passage_id':token,'quote':self.quote}]}
        with self.model(payload):
            result=knowledge_chat.answer_evidence_question('What frequency does Trial.pdf page 4 report?')
        self.assertIsNone(result['error'])
        self.assertEqual(result['citations'][0]['quote'],self.quote)
        self.assertIn(self.quote,result['citations'][0]['passage']['text'])
        self.assertEqual(result['citations'][0]['passage']['page_number'],4)
        self.assertIn('**Trial.pdf** (Page 4)',result['answer'])
        self.assertNotIn('★',result['answer'])

    def test_fabricated_quotes_do_not_hide_answer_or_become_verified_quote_cards(self):
        token=self.sources()[0]['passages'][0]['passage_id']
        for quote,identifier in [('Five sessions per week is proven for BBS > 35.',token),(self.quote,'invented:p99:0')]:
            payload={'answer':f'Unsupported claim [KB:{identifier}]','citations':[{'passage_id':identifier,'quote':quote}]}
            with self.subTest(quote=quote),self.model(payload):
                result=knowledge_chat.answer_evidence_question('Trial.pdf page 4 walking frequency')
            self.assertIsNone(result['error'])
            self.assertIn('Unsupported claim',result['answer'])
            self.assertTrue(result['citations'])
            self.assertTrue(all(card['quote'] in card['passage']['text'] for card in result['citations']))
            self.assertFalse(any(card.get('quote_kind') == 'verified_quote' for card in result['citations']))

    def test_answer_with_unverified_extra_token_remains_visible_with_locator_note(self):
        token=self.sources()[0]['passages'][0]['passage_id']
        payload={'answer':f'Valid [KB:{token}] and invented [KB:other:p90:0]','citations':[{'passage_id':token,'quote':self.quote}]}
        with self.model(payload):
            result=knowledge_chat.answer_evidence_question('Trial.pdf page 4 walking frequency')
        self.assertIsNone(result['error'])
        self.assertTrue(result['answer'])
        self.assertNotIn('[KB:',result['answer'])
        self.assertEqual(len(result['citations']), 1)

    def test_query_prompt_is_brief_and_does_not_request_guidance_badges(self):
        calls = []
        token = self.sources()[0]['passages'][0]['passage_id']
        payload = {'answer': 'The protocol reports three sessions weekly. See **Trial.pdf** (Page 4).',
                   'citations': [{'passage_id': token, 'quote': self.quote}]}
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(payload))])
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        with patch.object(knowledge_chat, '_client', return_value=client):
            result = knowledge_chat.answer_evidence_question('Trial.pdf page 4 walking frequency')
        self.assertIn('40–60 words', calls[0]['system'])
        self.assertIn('exactly ONE citation', calls[0]['system'])
        self.assertNotIn('fixed references', calls[0]['messages'][0]['content'])
        self.assertLessEqual(len(result['answer'].split()), 60)
        self.assertEqual(len(result['citations']), 1)

    def test_essay_response_is_compacted_to_one_quote_without_changing_source_text(self):
        token = self.sources()[0]['passages'][0]['passage_id']
        payload = {'answer': '# Answer\nThe study reports three weekly sessions.\n'
                   '## Detail\n- This is a supervised protocol.\n'
                   '| Dose | Frequency |\n| --- | --- |\n| Exercise | 3/week |\n'
                   'Further discussion follows. Even more discussion follows. [KB:' + token + ']',
                   'citations': [{'passage_id': token, 'quote': self.quote}] * 2}
        with self.model(payload):
            result = knowledge_chat.answer_evidence_question('Trial.pdf page 4 walking frequency')
        self.assertIn('**Trial.pdf** (Page 4)', result['answer'])
        self.assertLessEqual(len(result['answer'].split()), 60)
        for unwanted in ('#', '|', '[KB:', '★', 'Further discussion', 'Even more discussion'):
            self.assertNotIn(unwanted, result['answer'])
        self.assertEqual(len(result['citations']), 1)
        self.assertEqual(result['citations'][0]['quote'], self.quote)

    def test_missing_key_error_is_actionable_and_documents_remain_available(self):
        with patch.object(knowledge_chat,'_client',side_effect=ValueError('Add ANTHROPIC_API_KEY to .env')):
            result=knowledge_chat.answer_evidence_question('Trial.pdf page 4 walking frequency')
        self.assertIn('ANTHROPIC_API_KEY',result['error'])
        self.assertEqual(len(kb.list_documents()),1)

    def test_no_match_does_not_call_claude(self):
        with patch.object(knowledge_chat,'_client') as client:
            result=knowledge_chat.answer_evidence_question('quantum entanglement of quasars')
        client.assert_not_called()
        self.assertIn('could not find',result['answer'])

    def test_retrieval_appraisal_roundtrip_and_bounded_context(self):
        source=self.sources()[0]
        assessed=appraise_article(source)
        self.assertEqual(assessed['star_rating'],4)
        self.assertEqual(assessed['sample_size'],60)
        context=knowledge_context([assessed])
        self.assertIn(self.quote,context)
        self.assertNotIn('appraisal_text',context)
        self.assertNotIn('pages_text',context)
        self.assertIn('page_number',context)

    def test_known_page_grade_corrected_unknown_page_flagged_and_deleted_doc_not_citable(self):
        sources=self.sources()
        source=sources[0]
        passage=source['passages'][0]
        canonical=format_knowledge_citation(source,passage)
        wrong=canonical.replace('★★★★☆ 4/5','★★★★★ 5/5')
        self.assertEqual(canonicalize_knowledge_citations(wrong,sources),canonical)
        self.assertIn('not in retrieved passages',canonicalize_knowledge_citations(wrong.replace('p. 4','p. 99'),sources))
        kb.remove_document(source['document_id'])
        fresh=kb.search_knowledge_base('Trial.pdf page 4 walking frequency')
        self.assertIn('not in retrieved passages',canonicalize_knowledge_citations(canonical,fresh))

    def test_pubmed_outage_keeps_local_sources(self):
        plans=[{'facet':'rehabilitation','query':'stroke AND gait','fallback_queries':[]}]
        with patch.object(rag,'build_smart_query',return_value={'queries':plans,'rationale':'test'}),patch.object(rag,'search_pubmed',side_effect=rag.PubMedError('offline')):
            result=rag.retrieve_literature_smart('Trial.pdf walking protocol',{'diagnosis':'stroke'})
        self.assertFalse(result['sources'])
        self.assertTrue(result['knowledge_sources'])
        self.assertEqual(result['knowledge_sources'][0]['filename'],'Trial.pdf')

    def test_initial_guidance_includes_pdf_context_and_canonical_local_citation(self):
        source=self.sources()[0]
        token=source['passages'][0]['passage_id']
        fake=SimpleNamespace(content=[SimpleNamespace(type='text',text=f'The protocol reports three sessions [KB:{token}]')])
        literature={'sources':[]}
        with patch.object(literacy_engine.client.messages,'create',return_value=fake) as create:
            result=literacy_engine.generate_response({'diagnosis':'stroke'},literature,'Trial.pdf page 4 walking protocol',tier=2)
        kwargs=create.call_args.kwargs
        self.assertIn(self.quote,kwargs['messages'][0]['content'])
        self.assertIn('EVIDENCE BRIDGE',kwargs['system'])
        self.assertIn('Uploaded PDF: Trial.pdf, p. 4',result['response_text'])
        self.assertTrue(literature['knowledge_sources'])

    def test_followup_researches_pubmed_and_reads_newly_ingested_pdf(self):
        previous={'pmid':'1','title':'A systematic review','abstract':'Walking evidence','publication_types':['Systematic Review']}
        fresh={'pmid':'2','title':'A clinical practice guideline','abstract':'Guidance','publication_types':['Practice Guideline']}
        literature={'sources':[previous], 'knowledge_sources':[], 'clinical_context':{'raw_note':'stroke gait rehabilitation','parsed_entities':{'diagnosis':'stroke'},'clarifications':[]}}
        source=self.sources()[0]
        token=source['passages'][0]['passage_id']
        fake=SimpleNamespace(content=[SimpleNamespace(type='text',text=f'Compare the protocol [KB:{token}] with guidance (PMID: 2).')])
        with patch.object(rag,'retrieve_literature_smart',return_value={'sources':[fresh],'searches':[],'knowledge_sources':[],'query_used':'new question','rationale':'new'} ) as retrieve,patch.object(literacy_engine.client.messages,'create',return_value=fake):
            result=literacy_engine.continue_conversation([{'role':'user','content':'stroke gait rehabilitation'},{'role':'assistant','content':'Initial guidance'},{'role':'user','content':'Compare Trial.pdf page 4 walking protocol with PubMed'}],2,literature=literature)
        retrieve.assert_called_once()
        self.assertIn('Compare Trial.pdf',retrieve.call_args.args[0])
        self.assertEqual({s['pmid'] for s in literature['sources']},{'1','2'})
        self.assertIn('Uploaded PDF: Trial.pdf, p. 4',result)
        self.assertIn('PMID: 2 · ★★★★★ 5/5',result)
        kb.remove_document(self.document['document_id'])
        with patch.object(rag,'retrieve_literature_smart',return_value={'sources':[fresh],'searches':[]}),patch.object(literacy_engine.client.messages,'create',return_value=SimpleNamespace(content=[SimpleNamespace(type='text',text='No local source remains.')])):
            literacy_engine.continue_conversation([{'role':'user','content':'Trial.pdf page 4 walking protocol'}],2,literature=literature)
        self.assertEqual(literature['knowledge_sources'],[])

    def test_builtin_guideline_title_does_not_make_a_summary_five_star(self):
        source=appraise_article({'source_type':'builtin_reference','title':'Clinical Practice Guidelines','publication_types':['Practice Guideline'],'abstract':'A summary of guidelines'})
        self.assertEqual(source['star_rating'],1)
        self.assertEqual(source['sample_size'],None)
        self.assertIn('Summary',source['study_design'])

    def test_manual_citations_without_grades_cannot_invent_pages(self):
        sources=self.sources()
        self.assertIn('not in retrieved passages',canonicalize_knowledge_citations('(Uploaded PDF: Trial.pdf, p. 99)',sources))
        canonical=format_knowledge_citation(sources[0],sources[0]['passages'][0])
        undecorated=canonical.rsplit(' · ',1)[0]+')'
        self.assertEqual(canonicalize_knowledge_citations(undecorated,sources),canonical)
        token=sources[0]['passages'][0]['passage_id']
        payload={'answer':f'Real quote [KB:{token}], but more data (Uploaded PDF: Trial.pdf, p. 99)', 'citations':[{'passage_id':token,'quote':self.quote}]}
        with self.model(payload):
            result=knowledge_chat.answer_evidence_question('Trial.pdf page 4 walking frequency')
        self.assertIsNone(result['error'])
        self.assertTrue(result['answer'])
        self.assertNotIn('[KB:',result['answer'])
        self.assertEqual(len(result['citations']), 1)


if __name__=='__main__':
    unittest.main()
