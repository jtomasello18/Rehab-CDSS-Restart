"""Full-page retrieval and non-blocking response regressions for long PDFs."""

import base64
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('ANTHROPIC_API_KEY','test-key')
from streamlit.testing.v1 import AppTest
from professor_aria import branding, knowledge_base as kb, knowledge_chat
from professor_aria.knowledge_citations import knowledge_context
from test_knowledge_base import pdf_bytes


class LongDocumentRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.root_patch=patch.object(kb,'DEFAULT_ROOT',self.root)
        self.root_patch.start()
        pages=['Administrative content and cover information.']*119
        for index in range(98,118):
            pages[index]=f'Aerobic exercise and cardiorespiratory training protocol, section {index}. Heart rate reserve HRR, intensity, frequency, duration and screening are discussed.'
        pages[117]=('Aerobic exercise heart rate reserve HRR frequency duration and cardiorespiratory training.\n' +
                    'Detailed clinical protocol text with interval progression and exertion monitoring. '*45 +
                    '\nThe prescribed duration is individualized. END OF PAGE 118.')
        pages[118]='REFERENCES\n'+'\n'.join(f'{i}. Author. Aerobic exercise HRR cardiorespiratory intensity frequency. Journal. 2020;44:20. doi:10.1234/exercise{i}' for i in range(1,35))
        self.doc=kb.ingest_pdf('AHA ASA Acute Ischemic Stroke CPG .pdf',pdf_bytes(pages))

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def test_all_119_pages_scanned_and_twelve_full_pages_sections_returned(self):
        query='For AHA ASA Acute Ischemic Stroke CPG .pdf explain aerobic exercise heart rate reserve HRR frequency, duration, interval progression and exertion monitoring alongside the fixed references.'
        with patch.object(kb,'_passages',wraps=kb._passages) as scan:
            sources=kb.search_knowledge_base(query,max_documents=8,max_passages=12)
        self.assertEqual(self.doc['page_count'],119)
        self.assertEqual(scan.call_count,1)
        self.assertEqual(sum(len(s['passages']) for s in sources),12)
        self.assertTrue(all(s['source_type']=='uploaded_pdf' for s in sources))
        pdf_source=next(s for s in sources if s['source_type']=='uploaded_pdf')
        self.assertTrue(all(p['page_number']>=99 for p in pdf_source['passages']))
        self.assertNotIn(119,[p['page_number'] for p in pdf_source['passages']])
        for passage in pdf_source['passages']:
            self.assertEqual(passage['text'],self.doc['pages_text'][passage['page_number']])
        full=next(p for p in pdf_source['passages'] if p['page_number']==118)
        self.assertGreater(len(full['text']),1500)
        context=knowledge_context(sources)
        self.assertIn('END OF PAGE 118',context)
        self.assertIn('Page 118',context)
        self.assertIn('Document Name',context)

    def test_acute_keyword_expansion_finds_late_reperfusion_page(self):
        pages=['Administrative material.']*119
        pages[112]='Acute ischemic stroke: intravenous alteplase and endovascular reperfusion assessment for large vessel occlusion.'
        doc=kb.ingest_pdf('Acute Emergency.pdf',pdf_bytes(pages))
        sources=kb.search_knowledge_base('Thrombolysis and thrombectomy for ischaemic stroke',max_passages=10)
        match=next(s for s in sources if s['document_id']==doc['document_id'])
        self.assertEqual(match['passages'][0]['page_number'],113)

    def test_bibliography_detection_does_not_drop_prose_with_citations(self):
        self.assertTrue(kb._is_reference_page('References\n1. Exercise evidence. 2021;2:3.'))
        self.assertFalse(kb._is_reference_page('Aerobic exercise recommendations\nClinical recommendations cite several studies.\n1. Supporting study. doi:10.1234/test'))


class NonBlockingAnswerTests(unittest.TestCase):
    def setUp(self):
        self.source={'document_id':'pdf-test','source_type':'uploaded_pdf','filename':'Large Study.pdf','title':'Large study',
                     'star_rating':3,'star_display':'★★★☆☆','passages':[{'id':'pdf-test:p108:0','passage_id':'pdf-test:p108:0','page_number':108,
                     'text':'Aerobic\ntraining is delivered after screening. Exercise duration is individualized.'}]}

    def answer(self,text):
        client=SimpleNamespace(messages=SimpleNamespace(create=lambda **kw:SimpleNamespace(content=[SimpleNamespace(type='text',text=text)])))
        with patch.object(kb,'search_knowledge_base',return_value=[self.source]),patch.object(knowledge_chat,'_client',return_value=client):
            return knowledge_chat.answer_evidence_question('What is the aerobic protocol?')

    def test_markdown_without_json_quotes_or_tokens_is_shown_with_source_box(self):
        result=self.answer('Use the reported protocol after safety screening.')
        self.assertIsNone(result['error'])
        self.assertIn('Use the reported protocol',result['answer'])
        self.assertEqual(result['citations'][0]['passage']['page_number'],108)
        self.assertIn(result['citations'][0]['quote'],self.source['passages'][0]['text'])

    def test_malformed_trailing_json_does_not_hide_complete_answer(self):
        result=self.answer('{"answer":"Here is the clinical answer [KB:pdf-test:p108:0]","citations":[')
        self.assertIsNone(result['error'])
        self.assertIn('Here is the clinical answer',result['answer'])
        self.assertNotIn('{"answer"',result['answer'])
        self.assertTrue(result['citations'])

    def test_typographic_pdf_line_wrap_difference_returns_original_source_quote(self):
        result=self.answer(json.dumps({'answer':'Screen first [KB:pdf-test:p108:0]',
                                      'citations':[{'passage_id':'pdf-test:p108:0','quote':'Aerobic training is delivered after screening.'}]}))
        self.assertIsNone(result['error'])
        self.assertEqual(result['citations'][0]['quote'],'Aerobic\ntraining is delivered after screening.')

    def test_previous_page_number_does_not_constrain_followup_retrieval(self):
        client=SimpleNamespace(messages=SimpleNamespace(create=lambda **kw:SimpleNamespace(content=[SimpleNamespace(type='text',text='Answer with source context.')])) )
        with patch.object(kb,'search_knowledge_base',return_value=[self.source]) as search,patch.object(knowledge_chat,'_client',return_value=client):
            result=knowledge_chat.answer_evidence_question('What is the aerobic protocol in this PDF?',history=[{'role':'user','content':'Explain page 1 in Large Study.pdf'}])
        self.assertNotIn('page 1',search.call_args.args[0])
        self.assertIn('Large Study.pdf',search.call_args.args[0])
        self.assertIsNone(result['error'])


class BrandingAndReferenceTests(unittest.TestCase):
    def test_avatar_images_and_accessible_header_replace_robot_icons(self):
        self.assertEqual(branding.chat_avatar('assistant'),branding.PAGE_ICON)
        clinician=base64.b64decode(branding.chat_avatar('user').split(',',1)[1]).decode()
        self.assertIn('#145b6e',clinician)
        self.assertIn('>PT</text>',clinician)
        with tempfile.TemporaryDirectory() as folder,patch.object(kb,'DEFAULT_ROOT',Path(folder)):
            app=AppTest.from_string('from evidence_bridge import render_evidence_bridge\nrender_evidence_bridge()').run()
            app.session_state.bridge_history=[{'role':'user','content':'Question'}, {'role':'assistant','content':'Answer','sources':[],'citations':[]}]
            app.run()
        self.assertFalse(app.exception)
        markup='\n'.join(m.value for m in app.markdown)
        self.assertIn('alt="ARIA"',markup)
        self.assertNotIn('aria-hidden="true"><path',markup)
        chats=app.get('chat_message')
        self.assertEqual(chats[0].proto.avatar,branding.PT_AVATAR)
        self.assertEqual(chats[1].proto.avatar,branding.PAGE_ICON)

    def test_global_focus_and_bridge_font_sizes(self):
        from evidence_bridge import BRIDGE_STYLE
        for selector in ('div[data-baseweb="input"]:focus-within','div[data-baseweb="textarea"]:focus-within','div[data-baseweb="base-input"]:focus-within','input:focus, textarea:focus'):
            self.assertIn(selector,branding.INTERACTION_STYLE)
        self.assertIn('rgba(20, 91, 110, 0.25)',branding.INTERACTION_STYLE)
        self.assertIn('font-size:17px',BRIDGE_STYLE)
        self.assertIn('font-size:14px; font-weight:700',BRIDGE_STYLE)



if __name__=='__main__':
    unittest.main()
