"""Regression tests for concept-based PubMed coverage; no external services used."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from professor_aria import intake, literacy_engine, rag
from professor_aria.json_utils import extract_json_object


NOTE = (
    "Left MCA ischemic stroke, 12 weeks post-stroke. Prior Berg 42/56 now 38/56, "
    "walking slowed to 0.35 m/s, 2 near-falls at home this week. "
    "Baclofen increased to 10mg TID for worsening spasticity with drowsiness. "
    "Right foot drop and foot catching on carpet. Goal: walk to the mailbox."
)
ENTITIES = {
    "diagnosis": "Left MCA ischemic stroke, 12 weeks post-stroke",
    "symptoms": ["2 near-falls at home this week", "foot drop", "worsening spasticity"],
}


def response(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def plan(facet, query, fallbacks=()):
    return {"facet": facet, "query": query, "fallback_queries": list(fallbacks)}


def details(pmids):
    return [{"pmid": pmid, "title": f"Paper {pmid}", "abstract": "Abstract"} for pmid in pmids]


class JsonTests(unittest.TestCase):
    def test_extra_data_fences_escaped_braces_and_multiple_objects(self):
        first = {"rationale": 'quoted } and { and "quotes"', "queries": []}
        text = "Some preamble\n```json\n" + json.dumps(first) + "\n```\n" + '{"extra": true}'
        self.assertEqual(extract_json_object(text), first)

    def test_invalid_prefix_is_skipped(self):
        self.assertEqual(extract_json_object('bad {text}\n{"ok":true} trailing'), {"ok": True})

    def test_missing_or_truncated_json(self):
        for text in ("", "no JSON", '{"query": "stroke"'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                extract_json_object(text)

    def test_intake_and_tier_share_robust_extraction(self):
        with patch.object(intake.client.messages, "create", return_value=response('{"diagnosis":"stroke"}\nExtra text')):
            self.assertEqual(intake.parse_clinician_note(NOTE)["diagnosis"], "stroke")
        with patch.object(literacy_engine.client.messages, "create", return_value=response('{"tier":3,"rationale":"detail"}\n{}')):
            self.assertEqual(literacy_engine.infer_tier_from_note(NOTE), (3, "detail"))


class QueryPlanTests(unittest.TestCase):
    def test_malformed_optimizer_uses_three_clinical_facets_not_chart_sentences(self):
        with patch.object(rag.client.messages, "create", return_value=response("not JSON")):
            result = rag.build_smart_query(NOTE, ENTITIES)
        self.assertEqual([p["facet"] for p in result["queries"]], list(rag.FACETS))
        text = json.dumps(result["queries"])
        for bad in ("12 weeks", "2 near-falls", "38/56", "10mg", "mailbox", "carpet"):
            self.assertNotIn(bad, text)
        primary, safety, biomech = result["queries"]
        self.assertIn('"gait"', primary["query"])
        self.assertIn('"balance"', primary["query"])
        self.assertNotIn("baclofen", primary["query"])
        self.assertIn('"baclofen"', safety["query"])
        self.assertIn('"spasticity"', safety["query"])
        self.assertIn('"foot drop"', biomech["query"])
        self.assertTrue(primary["fallback_queries"])
        self.assertTrue(safety["fallback_queries"])
        self.assertTrue(biomech["fallback_queries"])

    def test_model_json_extra_data_and_omitted_facets(self):
        optimized = {
            "rationale": "Prioritize gait speed", "queries": [{
                "facet": "rehabilitation", "condition": ["stroke"],
                "focus": ["gait speed", "walking"], "refinements": ["balance", "falls"],
                "broad_focus": ["gait"],
            }],
        }
        with patch.object(rag.client.messages, "create", return_value=response(json.dumps(optimized) + '\n{"extra":1}')):
            result = rag.build_smart_query(NOTE, ENTITIES)
        self.assertEqual(result["rationale"], "Prioritize gait speed")
        self.assertEqual(len(result["queries"]), 3)
        self.assertIn('"gait speed"', result["queries"][0]["query"])
        self.assertLessEqual(result["queries"][0]["query"].count(" AND "), 2)

    def test_clarification_adds_coverage_without_narrowing_all_facets(self):
        with patch.object(rag.client.messages, "create", return_value=response("")):
            initial = rag.build_smart_query("stroke; goal walking", {"diagnosis": "stroke"})
            richer = rag.build_smart_query("stroke; goal walking", {"diagnosis": "stroke"}, [
                {"question": "Other concerns?", "answer": "baclofen spasticity and foot drop"},
            ])
        self.assertEqual(len(initial["queries"]), 1)
        self.assertEqual(len(richer["queries"]), 3)
        self.assertEqual(initial["queries"][0]["query"], richer["queries"][0]["query"])

    def test_unexpected_schema_and_invalid_terms_fall_back(self):
        for bad in ("[]", '{"queries":null}', '{"queries":[null]}', '{"queries":[{"facet":"rehabilitation","condition":["stroke AND baclofen"],"focus":["near falls at home this week yesterday"]}]}'):
            with self.subTest(bad=bad), patch.object(rag.client.messages, "create", return_value=response(bad)):
                result = rag.build_smart_query(NOTE, ENTITIES)
                self.assertEqual(len(result["queries"]), 3)
                self.assertNotIn("yesterday", str(result))

    def test_simple_nonstroke_case_and_compatibility_builder(self):
        with patch.object(rag.client.messages, "create", return_value=response("invalid")):
            result = rag.build_smart_query("knee OA with pain", {"diagnosis": "knee osteoarthritis"})
        self.assertEqual(len(result["queries"]), 1)
        self.assertIn("osteoarthritis", result["query"])
        self.assertIn("pain management", result["query"])
        self.assertNotIn(" AND 2 near-falls", rag.build_search_query(ENTITIES))

    def test_optimizer_connection_error_retains_clinical_facets(self):
        error = rag.APIConnectionError(request=SimpleNamespace())
        with patch.object(rag.client.messages, "create", side_effect=error):
            result = rag.build_smart_query(NOTE, ENTITIES)
        self.assertEqual(len(result["queries"]), 3)
        self.assertIn("optimizer was unavailable", result["rationale"])

    def test_standard_numbered_conditions_allowed_but_patient_numbers_rejected(self):
        self.assertEqual(rag._terms(["type 2 diabetes mellitus", "COVID-19"]), ["type 2 diabetes mellitus", "COVID-19"])
        self.assertEqual(rag._terms(["baclofen 10mg", "12 weeks post-stroke", "38/56", "2 near-falls at home"]), [])


class RetrievalTests(unittest.TestCase):
    def retrieve(self, plans, search, max_results=8, fetch=details):
        with patch.object(rag, "build_smart_query", return_value={"queries": plans, "rationale": "independent facets"}), patch.object(rag, "search_pubmed", side_effect=search), patch.object(rag, "fetch_article_details", side_effect=fetch):
            return rag.retrieve_literature_smart(NOTE, ENTITIES, max_results=max_results)

    def test_progressive_fallback_per_facet(self):
        calls = []
        def search(query, limit):
            calls.append(query)
            return {"rehab-core": ["1", "2"], "med-target": ["3"], "orthotics-broad": ["4"]}.get(query, [])
        result = self.retrieve([
            plan("rehabilitation", "rehab-target", ["rehab-core", "rehab-broad"]),
            plan("medication_safety", "med-target", ["med-core"]),
            plan("biomechanics", "orthotics-target", ["orthotics-core", "orthotics-broad"]),
        ], search)
        self.assertEqual(calls, ["rehab-target", "rehab-core", "med-target", "orthotics-target", "orthotics-core", "orthotics-broad"])
        self.assertEqual([s["pmid"] for s in result["sources"]], ["1", "3", "4", "2"])
        self.assertTrue(result["searches"][0]["broadened"])
        self.assertIn("Broader", result["note"])
        self.assertNotIn("No matching literature", str(result))

    def test_round_robin_deduplication_and_cap(self):
        hits = {"rehab": [str(i) for i in range(1, 9)], "med": ["1", "9", "10"], "bio": ["11", "12", "1"]}
        result = self.retrieve([
            plan("rehabilitation", "rehab"), plan("medication_safety", "med"), plan("biomechanics", "bio"),
        ], lambda query, limit: hits[query])
        ids = [s["pmid"] for s in result["sources"]]
        self.assertEqual(len(ids), 8)
        self.assertEqual(len(set(ids)), 8)
        self.assertIn("9", ids)
        self.assertIn("11", ids)
        self.assertEqual(result["sources"][0]["facets"], ["rehabilitation", "medication_safety", "biomechanics"])
        limited = self.retrieve([plan("rehabilitation", "rehab")], lambda q, n: hits[q], max_results=5)
        self.assertEqual(len(limited["sources"]), 5)

    def test_failed_facet_does_not_discard_successes_or_broaden_outage(self):
        calls = []
        def search(query, limit):
            calls.append(query)
            if query == "med":
                raise rag.PubMedError("Service unavailable")
            return ["1"]
        result = self.retrieve([plan("rehabilitation", "rehab"), plan("medication_safety", "med", ["med-broad"])], search)
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(calls, ["rehab", "med"])
        self.assertIn("partial coverage", result["note"])

    def test_zero_hits_remain_honest_and_distinct_from_network_error(self):
        result = self.retrieve([plan("rehabilitation", "target", ["core", "broad"])], lambda q, n: [])
        self.assertEqual(len(result["searches"][0]["attempts"]), 3)
        self.assertFalse(result["sources"])
        self.assertIn("coverage is incomplete", result["note"])
        self.assertNotIn("unavailable", result["note"])
        def unavailable(q, n):
            raise rag.PubMedError("Outage")
        result = self.retrieve([plan("rehabilitation", "target", ["broad"])], unavailable)
        self.assertIn("temporarily unavailable", result["note"])
        self.assertEqual(len(result["searches"][0]["attempts"]), 1)
        self.assertTrue(result["retrieval_error"])

    def test_repeated_queries_cached_and_missing_details_do_not_consume_cap(self):
        calls = []
        def search(query, limit):
            calls.append(query)
            return ["1", "2", "3"]
        result = self.retrieve([plan("rehabilitation", "shared"), plan("biomechanics", "shared")], search,
                               max_results=2, fetch=lambda ids: details(["2", "3"]))
        self.assertEqual(calls, ["shared"])
        # Search normally honors retmax, but tolerate missing records in the response.
        self.assertEqual(result["sources"][0]["pmid"], "2")

    def test_fetch_failure_is_reported(self):
        def broken(ids):
            raise rag.PubMedError("Bad XML")
        result = self.retrieve([plan("rehabilitation", "q")], lambda q, n: ["1"], fetch=broken)
        self.assertFalse(result["sources"])
        self.assertIn("article details", result["note"])

    def test_successful_search_with_missing_article_records_is_not_a_zero_hit(self):
        result = self.retrieve([plan("rehabilitation", "q")], lambda q, n: ["1"], fetch=lambda ids: [])
        self.assertIn("no usable article records", result["note"])
        self.assertTrue(result["retrieval_error"])

    def test_journal_articles_preferred_over_broad_book_chapters(self):
        def fetch(ids):
            articles = details(ids)
            articles[0]["source_type"] = "book_chapter"
            articles[1]["source_type"] = "journal_article"
            return articles
        result = self.retrieve([plan("medication_safety", "q")], lambda q, n: ["1", "2"], fetch=fetch)
        self.assertEqual([s["pmid"] for s in result["sources"]], ["2"])

    def test_parsed_error_skips_external_calls(self):
        with patch.object(rag, "build_smart_query") as build:
            result = rag.retrieve_literature_smart(NOTE, {"error": "invalid"})
        build.assert_not_called()
        self.assertFalse(result["sources"])


class PubMedTransportTests(unittest.TestCase):
    def test_successful_empty_search_and_service_error_are_distinct(self):
        with patch.object(rag, "_pubmed_get", return_value=SimpleNamespace(json=lambda: {"esearchresult": {"idlist": []}})):
            self.assertEqual(rag.search_pubmed("stroke"), [])
        for payload in ({"error": "rate limit"}, {"esearchresult": []}, {"esearchresult": {"ERROR": "failed"}}, {"esearchresult": {"idlist": "oops"}}):
            with self.subTest(payload=payload), patch.object(rag, "_pubmed_get", return_value=SimpleNamespace(json=lambda: payload)):
                with self.assertRaises(rag.PubMedError):
                    rag.search_pubmed("stroke")

    def test_complete_structured_abstract_and_inline_title_markup(self):
        xml = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>
          <ArticleTitle>Walking <i>after</i> stroke</ArticleTitle><Abstract>
          <AbstractText Label="METHODS">Measured <b>gait</b>.</AbstractText>
          <AbstractText Label="RESULTS">Improved speed.</AbstractText>
          </Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>'''
        with patch.object(rag, "_pubmed_get", return_value=SimpleNamespace(content=xml)):
            article = rag.fetch_article_details(["123"])[0]
        self.assertEqual(article["title"], "Walking after stroke")
        self.assertEqual(article["abstract"], "METHODS: Measured gait.\nRESULTS: Improved speed.")

    def test_pubmed_book_records_are_preserved(self):
        xml = b'''<PubmedArticleSet><PubmedBookArticle><BookDocument><PMID>456</PMID>
        <ArticleTitle>Post-Stroke Spasticity</ArticleTitle>
        <Abstract><AbstractText>Spasticity management.</AbstractText></Abstract>
        </BookDocument></PubmedBookArticle></PubmedArticleSet>'''
        with patch.object(rag, "_pubmed_get", return_value=SimpleNamespace(content=xml)):
            article = rag.fetch_article_details(["456"])[0]
        self.assertEqual(article["pmid"], "456")
        self.assertEqual(article["title"], "Post-Stroke Spasticity")

    def test_rate_limit_retried_once_and_paced(self):
        limited = SimpleNamespace(status_code=429)
        ok = SimpleNamespace(status_code=200, raise_for_status=lambda: None)
        with patch.object(rag.requests, "get", side_effect=[limited, ok]) as get, patch.object(rag.time, "sleep") as sleep:
            self.assertIs(rag._pubmed_get(rag.ESEARCH_URL, {}), ok)
        self.assertEqual(get.call_count, 2)
        self.assertIn(unittest.mock.call(1), sleep.call_args_list)


class GuidanceIntegrationTests(unittest.TestCase):
    def test_guidance_keeps_raw_note_clarifications_and_evidence_gaps(self):
        literature = {
            "sources": [{"pmid": "1", "title": "Gait paper", "abstract": "Walking", "facets": ["rehabilitation"]}],
            "note": "Medication evidence unavailable.",
            "clarifications": [{"question": "Safety?", "answer": "Drowsiness after baclofen increase"}],
            "searches": [{"facet": "rehabilitation", "retrieved_count": 1}],
        }
        with patch.object(literacy_engine.client.messages, "create", return_value=response("Guidance")) as create:
            literacy_engine.generate_response(ENTITIES, literature, NOTE, tier=2)
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn(NOTE, prompt)
        self.assertIn("Drowsiness after baclofen increase", prompt)
        self.assertIn("Medication evidence unavailable.", prompt)
        self.assertIn("do not substitute gait evidence", prompt)

    def test_dashboard_does_not_ask_narrowing_questions_for_an_outage(self):
        import aria_dashboard
        literature = {"sources": [], "retrieval_error": True, "note": "PubMed unavailable"}
        case = {"note": NOTE, "parsed": ENTITIES, "clarifications": []}
        with patch.object(aria_dashboard, "retrieve_literature_smart", return_value=literature), patch.object(aria_dashboard, "generate_clarifying_question") as question:
            aria_dashboard.advance_search(case)
        self.assertIs(case["literature"], literature)
        question.assert_not_called()


if __name__ == "__main__":
    unittest.main()
