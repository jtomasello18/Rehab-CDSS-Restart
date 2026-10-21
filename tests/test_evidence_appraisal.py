"""Deterministic regression cases for clinically meaningful appraisal mistakes."""

import unittest

from professor_aria.evidence_appraisal import (
    appraise_article,
    appraise_articles,
    extract_sample_size,
)


def paper(title="Rehabilitation after stroke", abstract="", types=(), **fields):
    return {"title": title, "abstract": abstract, "publication_types": list(types), **fields}


class SampleSizeTests(unittest.TestCase):
    def test_numeric_explicit_and_spelled_out_participant_counts(self):
        cases = {
            "Thirty patients were randomly assigned to two groups.": 30,
            "Sixty-four stroke survivors were randomized.": 64,
            "One hundred and twenty adults were recruited.": 120,
            "A total of 1,240 participants were included.": 1240,
            "We randomized 60 chronic stroke survivors to treatment or control.": 60,
            "The trial included participants with stroke (N = 51).": 51,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(extract_sample_size(abstract=text), expected)

    def test_scores_ages_doses_and_dates_are_not_participant_counts(self):
        for text in (
            "Berg scores were 30/56. Follow-up was 12 weeks; baclofen dose was 10 mg.",
            "Adults aged 50 years were evaluated in 2024.",
            "The review included 60 studies and 30 randomized trials.",
            "Included studies (n=70) were published between 2000 and 2024.",
            "We pooled n=30 studies of rehabilitation.",
        ):
            with self.subTest(text=text):
                self.assertIsNone(extract_sample_size(abstract=text))

    def test_total_randomized_is_not_followup_or_per_arm_count(self):
        self.assertEqual(extract_sample_size(abstract=(
            "A total of 60 patients were randomized; 30 patients per group received therapy. "
            "Forty patients completed follow-up."
        )), 60)
        self.assertEqual(extract_sample_size(abstract=(
            "Sixty patients were randomized. At follow-up, 42 patients were analyzed."
        )), 60)
        self.assertEqual(extract_sample_size(abstract=(
            "Participants were randomized to intervention (n=30) and control (n=32)."
        )), 62)
        self.assertEqual(extract_sample_size(abstract="Two equal groups of thirty participants received therapy."), 60)

    def test_lone_per_arm_count_is_unknown(self):
        for text in (
            "We included 30 patients per arm.",
            "Each group included 30 patients.",
            "Subjects received therapy (n=30 per arm).",
        ):
            with self.subTest(text=text):
                self.assertIsNone(extract_sample_size(abstract=text))

    def test_systematic_review_study_count_does_not_hide_participant_count(self):
        self.assertEqual(extract_sample_size(abstract=(
            "We included 30 studies (n=30) comprising a total of 1,200 patients."
        )), 1200)

    def test_group_counts_and_prior_or_planned_counts_do_not_replace_current_total(self):
        self.assertEqual(extract_sample_size(abstract=(
            "Two groups of 30 patients were randomized to treatment and control."
        )), 60)
        self.assertEqual(extract_sample_size(abstract=(
            "Previous trials enrolled 100 patients. In this study, 30 patients were randomized."
        )), 30)
        self.assertEqual(extract_sample_size(abstract=(
            "We planned to recruit 100 patients. We enrolled 30 patients."
        )), 30)
        self.assertEqual(extract_sample_size(abstract=(
            "Thirty patients with stroke were randomly divided into two groups. "
            "The RVF-STS group received treatment (n=15), and the C-STS group received control (n=15)."
        )), 30)

    def test_randomized_count_wins_over_screened_and_enrolled_counts(self):
        for text in (
            "A total of 100 patients were screened; 30 patients were randomized to treatment or control.",
            "We recruited 100 patients and randomized 30 patients to gait training or control.",
        ):
            with self.subTest(text=text):
                self.assertEqual(extract_sample_size(abstract=text), 30)
                assessed = appraise_article(paper("A randomized controlled trial", text))
                self.assertEqual(assessed["star_rating"], 3)


class EvidenceHierarchyTests(unittest.TestCase):
    def assert_appraisal(self, article, stars, design=None, n=None):
        assessed = appraise_article(article)
        self.assertEqual(assessed["star_rating"], stars)
        self.assertEqual(assessed["star_display"], "★" * stars + "☆" * (5 - stars))
        if design is not None:
            self.assertEqual(assessed["study_design"], design)
        self.assertEqual(assessed["sample_size"], n)
        self.assertTrue(assessed["appraisal_rationale"])
        self.assertIn(assessed["evidence_level"], assessed["appraisal_rationale"])
        self.assertTrue(assessed["appraisal_limitations"])
        return assessed

    def test_guideline_systematic_review_meta_analysis_and_cochrane(self):
        cases = (
            (paper(types=["Practice Guideline"]), "CPG"),
            (paper("Clinical practice guideline for stroke rehabilitation"), "CPG"),
            (paper(types=["Review", "Systematic Review"]), "Systematic Review"),
            (paper("Gait training: a systematic review and meta-analysis"), "Meta-Analysis"),
            (paper("Cochrane review: walking after stroke"), "Cochrane Review"),
            (paper(abstract="We conducted a systematic review of rehabilitation."), "Systematic Review"),
        )
        for article, design in cases:
            with self.subTest(article=article):
                self.assert_appraisal(article, 5, design)

    def test_rct_cutoff_and_multicenter_exception(self):
        for count, stars, design in ((30, 3, "Small RCT"), (49, 3, "Small RCT"), (50, 4, "Large RCT"), (200, 4, "Large RCT")):
            with self.subTest(count=count):
                assessed = self.assert_appraisal(paper(types=["Randomized Controlled Trial"], abstract=f"We enrolled {count} patients."), stars, design, count)
                self.assertIn(f"N={count}", assessed["appraisal_rationale"])
        self.assert_appraisal(paper(types=["Randomized Controlled Trial", "Multicenter Study"]), 4, "Multicenter RCT")
        self.assert_appraisal(paper("A multicentre randomized controlled trial", "Thirty participants were enrolled."), 4, "Multicenter RCT", 30)
        assessed = self.assert_appraisal(paper(types=["Randomized Controlled Trial"]), 3, "RCT")
        self.assertIn("unclear", assessed["appraisal_rationale"])

    def test_explicit_abstract_random_allocation_is_recognized(self):
        self.assert_appraisal(paper(abstract="Thirty patients were randomly assigned to treatment or control."), 3, "Small RCT", 30)
        self.assert_appraisal(paper(abstract="We conducted a randomized controlled trial. Sixty patients were recruited."), 4, "Large RCT", 60)

    def test_small_rct_rationale_explains_downgrade_without_power_claim(self):
        assessed = self.assert_appraisal(paper("A randomized controlled trial", "Thirty patients were randomly assigned."), 3, "Small RCT", 30)
        self.assertIn("downgraded for small sample size (N=30)", assessed["appraisal_rationale"])
        self.assertIn("N=30", assessed["evidence_tier"])
        self.assertTrue(any("statistical power" in text for text in assessed["appraisal_limitations"]))

    def test_nonrandomized_or_quasirandomized_large_trial_does_not_become_four_star(self):
        for title in ("Nonrandomized clinical trial", "A non-randomized controlled trial", "A quasi-randomized trial"):
            with self.subTest(title=title):
                self.assert_appraisal(paper(title, "A total of 100 patients were enrolled.", ["Clinical Trial"]), 3, "Nonrandomized Clinical Trial", 100)
        self.assert_appraisal(paper(
            abstract="This study was a non-randomized controlled trial. We enrolled 100 patients.",
            types=["Clinical Trial"],
        ), 3, "Nonrandomized Clinical Trial", 100)

    def test_prospective_and_nonrandomized_clinical_evidence(self):
        self.assert_appraisal(paper("A prospective cohort study", "We enrolled 80 patients."), 3, "Cohort", 80)
        self.assert_appraisal(paper(abstract="We prospectively enrolled 80 patients."), 3, "Cohort", 80)
        self.assert_appraisal(paper(types=["Controlled Clinical Trial"]), 3, "Nonrandomized Clinical Trial")
        self.assert_appraisal(paper(types=["Clinical Trial", "Multicenter Study"]), 3, "Nonrandomized Clinical Trial")

    def test_observational_designs_and_uncontrolled_trials(self):
        for title, design in (
            ("A retrospective cohort study", "Retrospective Study"),
            ("A case-control study", "Case-Control"),
            ("A cross-sectional survey", "Cross-Sectional"),
            ("A single-group pre-post clinical trial", "Single-Group / Pre-Post"),
            ("An uncontrolled before-and-after study", "Single-Group / Pre-Post"),
            ("A case series", "Case Series"),
        ):
            with self.subTest(title=title):
                self.assert_appraisal(paper(title, types=["Clinical Trial"] if "trial" in title else []), 2, design)
        self.assert_appraisal(paper(types=["Observational Study"]), 2, "Observational Study")

    def test_case_report_and_narrative_evidence(self):
        self.assert_appraisal(paper(types=["Case Reports"]), 1, "Case Report")
        self.assert_appraisal(paper("A narrative review of stroke trials", types=["Review"]), 1, "Narrative / Non-Systematic Review")
        self.assert_appraisal(paper(types=["Editorial"]), 1, "Commentary / Expert Opinion")
        self.assert_appraisal(paper(source_type="book_chapter"), 1, "Book Chapter / Expert Opinion")
        self.assert_appraisal(paper("A case series", types=["Case Reports"]), 2, "Case Series")

    def test_background_mentions_do_not_promote_an_observational_study(self):
        article = paper(
            "Walking outcomes after stroke: a retrospective study",
            "Previous randomized controlled trials and systematic reviews found benefit. "
            "We retrospectively reviewed the records of patients at our clinic.",
        )
        self.assert_appraisal(article, 2, "Retrospective Study")
        self.assert_appraisal(paper(
            "Adherence to clinical practice guidelines: a cross-sectional survey",
            "Clinical practice guidelines recommend screening.",
        ), 2, "Cross-Sectional")

    def test_indexed_case_report_is_not_promoted_by_prior_rct_description(self):
        self.assert_appraisal(paper(
            "Rehabilitation after stroke: a case report",
            "Previous research reports that 100 patients were randomized to treatment or control. "
            "We describe one patient with stroke.",
            ["Case Reports"],
        ), 1, "Case Report", 1)

    def test_studies_of_reviews_and_guidelines_keep_actual_design(self):
        self.assert_appraisal(paper(
            "Effect of clinical practice guidelines on falls: a randomized controlled trial",
            "Thirty patients were randomized to treatment or control.",
            ["Randomized Controlled Trial"],
        ), 3, "Small RCT", 30)
        self.assert_appraisal(paper(
            "Methodological quality of systematic reviews of stroke rehabilitation: a cross-sectional study",
            "We evaluated methodological quality.",
            ["Journal Article", "Observational Study"],
        ), 2, "Cross-Sectional")
        self.assert_appraisal(paper(
            "Best Practice Guidelines for Stroke Rehabilitation: A Modified Scoping Review.",
            types=["Scoping Review"],
        ), 1, "Scoping Review")

    def test_abstract_passive_design_statement_is_recognized(self):
        self.assert_appraisal(paper(
            abstract="A single-group, pre-post study was conducted in 30 patients.",
            types=["Clinical Trial"],
        ), 2, "Single-Group / Pre-Post", 30)
        self.assert_appraisal(paper(
            abstract="A prospective cohort study was conducted in 100 patients.",
            types=["Observational Study"],
        ), 3, "Cohort", 100)

    def test_protocol_and_pilot_require_completed_outcome_design(self):
        self.assert_appraisal(paper("Protocol for a systematic review and meta-analysis", types=["Systematic Review"]), 1, "Study Protocol")
        self.assert_appraisal(paper("A randomized controlled trial: study protocol", types=["Randomized Controlled Trial"]), 1, "Study Protocol")
        self.assert_appraisal(paper("A pilot study of gait rehabilitation"), 1, "Pilot / Feasibility Study")
        assessed = self.assert_appraisal(paper("A pilot randomized controlled trial", "Thirty patients were randomized."), 3, "Small RCT", 30)
        self.assertTrue(any("pilot" in text for text in assessed["appraisal_limitations"]))

    def test_preclinical_and_retracted_override_nominal_design(self):
        self.assert_appraisal(paper(types=["Systematic Review"], mesh_terms=["Animals"]), 1, "Preclinical Study")
        self.assert_appraisal(paper("A randomized controlled study in rats", types=["Randomized Controlled Trial"]), 1, "Preclinical Study")
        self.assert_appraisal(paper("An in vitro systematic review", types=["Systematic Review"]), 1, "Preclinical Study")
        self.assert_appraisal(paper(types=["Randomized Controlled Trial", "Retracted Publication"]), 1, "Retracted Study")
        self.assert_appraisal(paper(types=["Meta-Analysis"], retracted=True), 1, "Retracted Study")
        self.assert_appraisal(paper(types=["Systematic Review"], mesh_terms=["Humans", "Animals"]), 5, "Systematic Review")
        self.assert_appraisal(paper(
            "A randomized controlled trial",
            "We randomly assigned 100 rats to treadmill or control training.",
            ["Randomized Controlled Trial"],
        ), 1, "Preclinical Study")

    def test_sort_is_stable_and_input_is_not_modified(self):
        articles = [
            paper("Small trial A", types=["Randomized Controlled Trial"], pmid="1"),
            paper("A systematic review", pmid="2"),
            paper("Small trial B", types=["Randomized Controlled Trial"], pmid="3"),
            paper("A case report", pmid="4"),
        ]
        assessed = appraise_articles(articles)
        self.assertEqual([article["pmid"] for article in assessed], ["2", "1", "3", "4"])
        self.assertNotIn("star_rating", articles[0])
        self.assertEqual([article["pmid"] for article in articles], ["1", "2", "3", "4"])
        self.assertEqual(appraise_articles([]), [])


if __name__ == "__main__":
    unittest.main()
