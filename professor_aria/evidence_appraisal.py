"""Transparent, conservative screening of PubMed evidence for ARIA.

This is ARIA's requested design-and-sample-size hierarchy, informed by evidence
hierarchies. It is *not* a formal OCEBM, GRADE certainty, PEDro, or risk-of-bias
assessment. Publication types and reported design identify the kind of evidence;
they do not establish its validity, applicability, or the power of a trial.
"""

import re
from typing import Iterable


_ONES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_WORD_NUMBER = (
    r"(?:" + "|".join(_ONES) + r")(?:[-\s]+(?:"
    + "|".join(_ONES) + r"|hundred|thousand|and)){0,8}"
)
_NUMBER = rf"(?:\d{{1,3}}(?:,\d{{3}})+|\d+|{_WORD_NUMBER})"
_PERSON = r"(?:participants?|patients?|subjects?|individuals?|adults?|children|survivors|volunteers|people|men|women|residents|athletes)"
_MODIFIERS = (
    r"(?:(?:eligible|consecutive|ambulatory|adult|older|elderly|young|healthy|"
    r"male|female|chronic|acute|subacute|stroke|post[- ]stroke|community[- ]dwelling|"
    r"human|total|randomi[sz]ed)\s+){0,5}"
)
_COUNT_PEOPLE = re.compile(rf"\b(?P<number>{_NUMBER})\s+{_MODIFIERS}{_PERSON}\b", re.I)
_N_EQUALS = re.compile(r"\bn\s*=\s*(\d{1,3}(?:,\d{3})+|\d+)\b", re.I)
_ARM_END = re.compile(
    r"(?:intervention|experimental|treatment|control|placebo|usual care|comparison|"
    r"(?:group|arm)\s*[a-c1-9]?)(?:\s+(?:group|arm))?\s*[:=(\[]*\s*$", re.I
)
_BASE_LIMITATION = (
    "ARIA's design-and-sample-size screen is not a formal GRADE certainty, "
    "PEDro or risk-of-bias assessment."
)


def _integer(text: str) -> int | None:
    """Read a numeric or spelled-out positive count without external models."""
    if re.fullmatch(r"[\d,]+", text):
        value = int(text.replace(",", ""))
        return value if value > 0 else None
    current = total = 0
    for word in re.split(r"[-\s]+", text.lower()):
        if word == "and":
            continue
        if word in _ONES:
            current += _ONES[word]
        elif word == "hundred":
            current = max(current, 1) * 100
        elif word == "thousand":
            total += max(current, 1) * 1000
            current = 0
        else:
            return None
    return total + current or None


def _prior_or_planned(text: str, position: int) -> bool:
    """Separate the current reported sample from background and target Ns."""
    start = max(text.rfind(".", 0, position), text.rfind(";", 0, position), text.rfind("\n", 0, position)) + 1
    prefix = text[start:position]
    other = list(re.finditer(r"\b(?:previous|prior|earlier|published|existing|historical|planned|plan to|target|aimed to|aim to|will enroll|will recruit|will randomi[sz]e)\b", prefix, re.I))
    if not other:
        return False
    own = list(re.finditer(r"\b(?:this|the present|the current|our)\s+(?:study|trial|sample)\b", prefix, re.I))
    return not own or other[-1].start() > own[-1].start()


def extract_sample_size(title: str = "", abstract: str = "") -> int | None:
    """Extract a reported participant total, avoiding study counts and arm Ns.

    Explicit total and enrollment/randomization counts take precedence over
    follow-up counts. Clearly labelled arm Ns can be summed within one sentence;
    a lone per-arm count is left unknown rather than presented as a total.
    """
    text = f"{title or ''}. {abstract or ''}"
    people = []
    for match in _COUNT_PEOPLE.finditer(text):
        if _prior_or_planned(text, match.start()):
            continue
        value = _integer(match.group("number"))
        if value is None:
            continue
        before = text[max(0, match.start() - 65):match.start()]
        after = text[match.end():match.end() + 95]
        # Do not turn an age, a follow-up interval, or an explicit per-arm count
        # into the total sample. A count of studies never matches _PERSON.
        if re.search(r"(?:aged?|age[sd]?\s+(?:of|was|were))\s*$", before, re.I):
            continue
        if re.search(r"\b(?:screened|assessed for eligibility|evaluated for eligibility)\s*$", before, re.I) or re.match(r"\s*(?:(?:were|was)\s+)?(?:screened|assessed for eligibility|evaluated for eligibility)\b", after, re.I):
            continue
        per_arm = bool(re.match(r"\s*(?:in\s+)?(?:each|per)\s+(?:group|arm)\b", after, re.I))
        per_arm |= bool(re.search(r"\b(?:each|per)\s+(?:group|arm)\s+(?:of\s+|included\s+|contained\s+)?$", before, re.I))
        arm = bool(_ARM_END.search(before)) or per_arm
        total = bool(re.search(r"\b(?:a\s+)?total(?:\s+of)?\s*$", before, re.I))
        enrollment = bool(re.match(
            r"\s*(?:(?:with|who had|diagnosed with)\s+[^.;]{0,40}\s+)?"
            r"(?:(?:were|was)\s+)?(?:enrolled|recruited|randomi[sz]ed|randomly\s+(?:assigned|allocated|divided)|included)\b", after, re.I
        )) or bool(re.search(
            r"\b(?:enrolled|recruited|randomi[sz]ed|included)\s+(?:(?:a\s+)?total\s+of\s+)?$", before, re.I
        ))
        randomized = bool(re.match(
            r"\s*(?:(?:with|who had|diagnosed with)\s+[^.;]{0,40}\s+)?"
            r"(?:(?:were|was)\s+)?(?:randomi[sz]ed|randomly\s+(?:assigned|allocated|divided))\b", after, re.I
        )) or bool(re.search(r"\b(?:randomi[sz]ed|randomly\s+(?:assigned|allocated|divided))\s+(?:(?:a\s+)?total\s+of\s+)?$", before, re.I))
        # Approximate examples or recommendations are not the current sample.
        if re.search(r"\b(?:at least|more than|fewer than|less than|approximately|about|up to|e\.g\.,?)\s*$", before, re.I):
            continue
        people.append((value, match.start(), total, enrollment, arm, randomized))
    # Two groups of 30 participants explicitly establishes a total of 60.
    grouped = re.search(
        rf"\b(?P<groups>two|three|four|\d+)\s+(?:equal\s+)?(?:groups|arms)\s+of\s+"
        rf"(?P<count>{_NUMBER})\s+{_MODIFIERS}{_PERSON}\b", text, re.I
    )
    if grouped and not _prior_or_planned(text, grouped.start()):
        groups, count = _integer(grouped.group("groups")), _integer(grouped.group("count"))
        if groups and count:
            return groups * count

    randomized = [item[0] for item in people if item[5] and not item[4]]
    if randomized:
        return max(randomized)
    totals = [item[0] for item in people if item[2] and not item[4]]
    if totals:
        return max(totals)
    enrollment = [item[0] for item in people if item[3] and not item[4]]
    if enrollment:
        return max(enrollment)

    generic_n, arms = [], []
    for match in _N_EQUALS.finditer(text):
        if _prior_or_planned(text, match.start()):
            continue
        value = _integer(match.group(1))
        before = text[max(0, match.start() - 75):match.start()]
        after = text[match.end():match.end() + 35]
        # N can count included studies, records, or other non-participant units.
        if re.search(r"\b(?:studies|trials|articles|publications|records|databases|reviews|outcomes)\s*[(:=\[]*\s*$", before, re.I):
            continue
        if re.match(r"\s*(?:studies|trials|articles|publications|records|reviews|outcomes)\b", after, re.I):
            continue
        per_arm = bool(re.match(r"\s*(?:[)\]]\s*)?(?:per|in each)\s+(?:group|arm)\b", after, re.I))
        if _ARM_END.search(before):
            arms.append((value, match.start()))
        elif not per_arm:
            generic_n.append(value)

    unlabelled = [item[0] for item in people if not item[4]]
    if unlabelled:
        return max(unlabelled)
    if generic_n:
        return max(generic_n)
    # Arm labels must occur in the same sentence to avoid summing baseline and
    # follow-up Ns or samples from unrelated studies cited in the abstract.
    if len(arms) >= 2:
        between = text[arms[0][1]:arms[-1][1]]
        if not re.search(r"[.!?]\s+[A-Z]", between):
            return sum(value for value, _ in arms)

    return None


def _values(values: Iterable | str | None) -> list[str]:
    if isinstance(values, str):
        return [values.lower()]
    result = []
    for value in values or []:
        if isinstance(value, str):
            result.append(value.lower())
        elif isinstance(value, dict):
            label = value.get("descriptor_name") or value.get("descriptor") or value.get("name") or value.get("term")
            if isinstance(label, str):
                result.append(label.lower())
    return result


def _reported_design(abstract: str, pattern: str) -> bool:
    """Require the abstract to describe its own methods, not prior literature."""
    for match in re.finditer(pattern, abstract, re.I):
        sentence_start = max(abstract.rfind(".", 0, match.start()), abstract.rfind("\n", 0, match.start())) + 1
        prefix = abstract[sentence_start:match.start()]
        suffix = abstract[match.end():match.end() + 90]
        if _prior_or_planned(abstract, match.start()) or re.search(r"\b(?:other|literature|according to)\b", prefix, re.I):
            continue
        own = re.search(
            r"\b(?:(?:we|investigators|authors)\s+(?:conducted|performed|undertook|used|carried out|designed|randomly assigned|randomly allocated|randomi[sz]ed|studied|enrolled|recruited|evaluated)|"
            r"(?:this|our|the present)\s+(?:study|trial|review)|this\s+|methods\s*[:.]|study design\s*[:.])", prefix, re.I
        )
        passive = re.match(r"[^.;:]{0,65}\b(?:was|is|were)\s+(?:conducted|performed|undertaken|designed|randomi[sz]ed|assigned|allocated|studied|tested)\b", suffix, re.I)
        if own or passive:
            return True
    return False


def _is_preclinical(title: str, abstract: str, types: set[str], mesh: set[str]) -> bool:
    if "animals" in mesh and "humans" not in mesh:
        return True
    if any("veterinary" in kind for kind in types):
        return True
    animal_title = (
        r"\bin\s+(?:(?:adult|male|female|aged|young|laboratory|experimental)\s+){0,3}"
        r"(?:rats|mice|rabbits|dogs|sheep|pigs|monkeys|zebrafish)\b|"
        r"\b(?:rat|mouse|murine|rabbit|rodent|porcine|canine|animal)\s+(?:model|models|study|studies|experiment)\b"
    )
    bench = r"\b(?:in[- ]vitro|ex[- ]vivo|benchtop|bench[- ](?:study|test|testing)|cadaveric|cell[- ]culture|cell lines?)\b"
    animal_subject = r"\b(?:rats|mice|rabbits|monkeys|zebrafish|laboratory animals)\b"
    return bool(re.search(animal_title + "|" + bench, title, re.I) or _reported_design(abstract, animal_title + "|" + bench + "|" + animal_subject))


def appraise_article(article: dict) -> dict:
    """Return an enriched copy of one PubMed article, never mutating its input."""
    result = dict(article)
    if article.get("source_type") == "builtin_reference":
        result.update({
            "star_rating": 1, "star_display": "★☆☆☆☆", "evidence_level": "Level V",
            "study_design": "Curated Reference Summary", "evidence_tier": "Level V Curated Reference Summary",
            "sample_size": None,
            "appraisal_rationale": "Level V Curated Reference Summary — Orientation to linked clinical guidance; the original guideline text has not been ingested.",
            "appraisal_limitations": [
                _BASE_LIMITATION,
                "This is an authored reference summary, not the original CPG, a verbatim quotation, or a formal recommendation grade. Consult its linked sources or upload the original PDF.",
            ],
        })
        return result
    title = str(article.get("title") or "")
    abstract = str(article.get("abstract") or article.get("appraisal_text") or "")
    types = {re.sub(r"[-_\s]+", " ", value).strip() for value in _values(article.get("publication_types"))}
    mesh = set(_values(article.get("mesh_terms")))
    n = extract_sample_size(title, abstract)
    n_text = f" (N={n:,})" if n is not None else ""
    limitations = [_BASE_LIMITATION]
    score, level, design = 1, "Level V", "Unclassified Evidence"
    reason = "Study design is not established by the available title, abstract and publication types."

    rct_pattern = r"\brandomi[sz]ed(?:[ -]+controlled|[ -]+(?:parallel|crossover|cross-over|pilot|feasibility|multicent(?:er|re)))?\s+(?:clinical\s+)?(?:trial|study)\b|\bRCT\b"
    nonrandom_pattern = r"\b(?:non[- ]?randomi[sz]ed|quasi[- ]?randomi[sz]ed)\b"
    nonrandom = bool(re.search(nonrandom_pattern, title, re.I)) or _reported_design(abstract, nonrandom_pattern)
    allocation_pattern = (
        rf"\b{_PERSON}\b[^.;]{{0,55}}\b(?:were\s+)?(?:randomi[sz]ed|randomly\s+(?:assigned|allocated))\b|"
        r"\bwe\s+(?:randomi[sz]ed|randomly\s+(?:assigned|allocated|divided))\b"
    )
    random_allocation = any(
        not _prior_or_planned(abstract, match.start())
        and not re.search(r"\b(?:not|non[- ]?randomi[sz]ed)\b", match.group(), re.I)
        for match in re.finditer(allocation_pattern, abstract, re.I)
    )
    rct = "randomized controlled trial" in types or (
        not nonrandom and (bool(re.search(rct_pattern, title, re.I)) or _reported_design(abstract, rct_pattern) or random_allocation)
    )
    multicenter = "multicenter study" in types or bool(re.search(r"\bmulti[- ]?cent(?:er|re)(?:ed)?\b", title, re.I)) or _reported_design(abstract, r"\bmulti[- ]?cent(?:er|re)(?:ed)?\b")
    protocol = "clinical trial protocol" in types or bool(re.search(r"\b(?:study |trial |review )?protocol\b", title, re.I))
    protocol |= _reported_design(abstract, r"\b(?:study|trial|review) protocol\b")
    retracted = article.get("retracted") is True or bool(types & {"retracted publication", "retraction of publication"}) or bool(re.search(r"^\s*(?:retracted|retraction)\b|\[retracted\]", title, re.I))
    review_pattern = r"\bsystematic(?:\s+literature)?\s+reviews?\b"
    meta_pattern = r"\bmeta[- ]analys(?:is|es)\b"
    meta_analysis = "meta analysis" in types or bool(re.search(meta_pattern, title, re.I)) or _reported_design(abstract, meta_pattern)
    systematic = "systematic review" in types or bool(re.search(review_pattern, title, re.I)) or _reported_design(abstract, review_pattern)
    cochrane = bool(re.search(r"\bcochrane\b", title, re.I)) or any("cochrane" in kind for kind in types)
    # A paper studying guideline adherence is not itself a practice guideline.
    guideline = bool(types & {"practice guideline", "guideline", "clinical practice guideline"})
    guideline_title = bool(re.search(r"\b(?:clinical\s+practice\s+)?guidelines?\b", title, re.I))
    guideline_title &= not bool(re.search(r"\b(?:adherence|compliance|uptake|survey|barriers|awareness|knowledge|cross[- ]sectional|effect of|impact of)\b", title, re.I))
    guideline |= guideline_title
    commentary = bool(types & {"editorial", "comment", "personal narrative", "interview"}) or bool(re.search(r"^\s*(?:commentary|editorial|expert opinion|perspective)\b", title, re.I))
    retrospective = bool(re.search(r"\bretrospective\b", title, re.I)) or _reported_design(abstract, r"\bretrospective\b")
    case_control = bool(re.search(r"\bcase[- ]control\b", title, re.I)) or _reported_design(abstract, r"\bcase[- ]control\b")
    cross_sectional = bool(re.search(r"\bcross[- ]sectional\b", title, re.I)) or _reported_design(abstract, r"\bcross[- ]sectional\b")
    single_group = bool(re.search(r"\b(?:single[- ](?:group|arm)|uncontrolled|pre[- ]?post|before[- ]and[- ]after)\b", title, re.I)) or _reported_design(abstract, r"\b(?:single[- ](?:group|arm)|uncontrolled|pre[- ]?post|before[- ]and[- ]after)\b")
    case_series = bool(re.search(r"\bcase series\b", title, re.I)) or _reported_design(abstract, r"\bcase series\b")
    cohort = bool(re.search(r"\b(?:prospective|cohort|longitudinal)\b", title, re.I)) or _reported_design(abstract, r"\b(?:prospective|cohort|longitudinal)\b")
    cohort |= bool(re.search(r"\bwe\s+prospectively\s+(?:enrolled|recruited|followed|studied)\b", abstract, re.I))
    clinical_trial = any(kind in {"clinical trial", "controlled clinical trial"} or kind.startswith("clinical trial phase ") for kind in types)
    scoping = "scoping review" in types or bool(re.search(r"\bscoping review\b", title, re.I))
    # Review/guideline words can be the object of an original research study.
    # Explicit original-study design in the title or indexed RCT metadata wins
    # over such incidental words unless a synthesis/guideline is itself indexed.
    high_types = types & {"practice guideline", "guideline", "clinical practice guideline", "systematic review", "meta analysis"}
    original_title = bool(re.search(
        r"(?:^|:)\s*(?:an?\s+)?(?:randomi[sz]ed|non[- ]?randomi[sz]ed|retrospective|prospective|cross[- ]sectional|case[- ]control|single[- ]group|pre[- ]?post)[^:;.]{0,65}\b(?:trial|study|survey|analysis)\b", title, re.I
    ))
    if not high_types and (original_title or "randomized controlled trial" in types):
        guideline = cochrane = systematic = meta_analysis = False
    if scoping and not high_types:
        guideline = cochrane = systematic = meta_analysis = False

    if retracted:
        design = "Retracted Study"
        reason = "Retracted publication; exclude from support for clinical recommendations."
        limitations.append("Retraction supersedes the original study design; this source must not support clinical care.")
    elif _is_preclinical(title, abstract, types, mesh):
        design = "Preclinical Study"
        reason = "Animal or laboratory evidence; clinical effectiveness in humans is not established."
    elif protocol:
        design = "Study Protocol"
        reason = "Planned methods without completed outcome evidence; preliminary support only."
        limitations.append("A protocol does not establish treatment effects, even when it describes a randomized trial or systematic review.")
    elif commentary and not (types & {"randomized controlled trial", "systematic review", "meta analysis", "practice guideline"}):
        design = "Commentary / Expert Opinion"
        reason = "Opinion or commentary without primary comparative outcome evidence."
    elif guideline or cochrane or meta_analysis or systematic:
        score, level = 5, "Level I-A"
        if guideline and not (meta_analysis or systematic):
            design = "CPG"
            reason = "Clinical practice guideline; recommendation strength and underlying evidence certainty require review."
            limitations.append("Guideline currency, recommendation strength and underlying evidence certainty have not been independently assessed.")
        else:
            design = "Cochrane Review" if cochrane else "Meta-Analysis" if meta_analysis else "Systematic Review"
            reason = "Systematic evidence synthesis; review quality and underlying study certainty require review."
            limitations.append("Search quality, risk of bias, heterogeneity and the certainty of included studies have not been independently assessed.")
    elif "case reports" in types and not case_series:
        design = "Case Report"
        reason = "Individual case evidence" + n_text + "; findings are preliminary and cannot establish treatment effects."
    elif rct:
        if multicenter or (n is not None and n >= 50):
            score, level = 4, "Level I-B"
            design = "Multicenter RCT" if multicenter else "Large RCT"
            reason = "Randomized design" + (f", N={n:,}" if n is not None else ", multicenter design") + "; meets ARIA's higher-tier design/sample rule."
        else:
            score, level = 3, "Level II"
            design = "Small RCT" if n is not None else "RCT"
            reason = (f"Randomized design, downgraded for small sample size (N={n:,})." if n is not None else "Randomized design; total sample size is unclear, so conservatively rated 3/5.")
        limitations.append("N alone does not establish statistical power, trial quality or applicability to this patient.")
        limitations.append("Allocation concealment, blinding, follow-up and intention-to-treat require full-text assessment.")
        if n is None:
            limitations.append("Total randomized sample size is not reported unambiguously.")
        if re.search(r"\b(?:pilot|feasibility)\b", title, re.I):
            limitations.append("A pilot or feasibility purpose limits confirmatory efficacy claims.")
    elif retrospective or case_control or cross_sectional or single_group or case_series:
        score, level = 2, "Level III-IV"
        design = "Retrospective Study" if retrospective else "Case-Control" if case_control else "Cross-Sectional" if cross_sectional else "Case Series" if case_series else "Single-Group / Pre-Post"
        reason = "Observational or uncontrolled evidence" + n_text + "; confounding and causal inference remain concerns."
    elif cohort or clinical_trial or nonrandom:
        score, level = 3, "Level II"
        design = "Cohort" if cohort else "Nonrandomized Clinical Trial"
        reason = "Prospective/cohort or nonrandomized clinical evidence" + n_text + "; randomization and causal certainty are not established."
    elif "observational study" in types:
        score, level, design = 2, "Level III-IV", "Observational Study"
        reason = "Observational design; study direction and control for confounding are not established."
    elif "case reports" in types or re.search(r"\bcase reports?\b", title, re.I):
        design = "Case Report"
        reason = "Individual case evidence" + n_text + "; findings are preliminary and cannot establish treatment effects."
    elif scoping or "review" in types or re.search(r"\b(?:narrative|scoping|literature)?\s*review\b", title, re.I):
        design = "Scoping Review" if scoping else "Narrative / Non-Systematic Review"
        reason = "No systematic synthesis or comparative outcome design is established; background context only."
    elif article.get("source_type") == "book_chapter":
        design = "Book Chapter / Expert Opinion"
        reason = "Background or expert synthesis without a verified comparative study design."
    elif re.search(r"\b(?:pilot|feasibility)\b", title, re.I):
        design = "Pilot / Feasibility Study"
        reason = "Preliminary study; randomization, controls and completed clinical effectiveness are not established."

    result.update({
        "star_rating": score,
        "star_display": "★" * score + "☆" * (5 - score),
        "evidence_level": level,
        "study_design": design,
        "evidence_tier": f"{level} {design}{n_text}",
        "sample_size": n,
        "appraisal_rationale": f"{level} {design} — {reason}",
        "appraisal_limitations": limitations,
    })
    return result


def appraise_articles(articles: list[dict]) -> list[dict]:
    """Enrich and stably sort highest-rated evidence first."""
    return sorted((appraise_article(article) for article in articles), key=lambda article: -article["star_rating"])
