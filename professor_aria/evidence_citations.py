"""Keep inline PMID grades consistent with the deterministic article appraisal."""

import re

if __package__:
    from .evidence_appraisal import appraise_article, appraise_articles
else:
    from evidence_appraisal import appraise_article, appraise_articles


def format_citation(article: dict) -> str:
    source = appraise_article(article)
    label = source["study_design"]
    if source.get("sample_size") is not None:
        label += f", N={source['sample_size']:,}"
    return f"(PMID: {source['pmid']} · {source['star_display']} {source['star_rating']}/5 · {label})"


def canonicalize_citations(text: str, sources: list[dict]) -> str:
    """Correct grades for retrieved PMIDs; flag unsupported PMIDs without a grade.

    Accept common parenthetical, bracketed, grouped and bare PMID formats. Code
    spans/fences are preserved. We never infer an article identity from a bare number.
    """
    catalog = {str(s["pmid"]): s for s in appraise_articles(sources) if str(s.get("pmid", "")).isdigit()}
    labels = {s["study_design"] for s in catalog.values()} | {
        "CPG", "Large RCT", "Small RCT", "Multicenter RCT", "RCT", "Cohort",
        "Systematic Review", "Meta-Analysis", "Cochrane Review", "Case Report",
    }
    label_pattern = "(?:" + "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True)) + ")"

    def citation(pmid):
        if pmid in catalog:
            return format_citation(catalog[pmid])
        return f"(PMID: {pmid} · not in retrieved evidence)"

    def prose(part):
        replacements = []
        # PMID links supplied by the model are replaced with source-backed
        # citations; avoid leaving the model's URL as a stray parenthetical.
        part = re.sub(r"\[(PMIDs?\s*:?\s*[^\]\n]+)\]\([^\)\n]*\)", r"(\1)", part, flags=re.I)

        def placeholder(value):
            token = f"\x00ARIA_EVIDENCE_{len(replacements)}\x00"
            replacements.append(value)
            return token

        part = re.sub(
            r"\[([^\]\n]+)\]\(https?://(?:www\.)?pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?(?:\?[^\)\n]*)?\)",
            lambda m: placeholder(f"{m[1]} {citation(m[2])}"), part, flags=re.I,
        )
        part = re.sub(
            r"https?://(?:www\.)?pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?(?:\?[^\s\)\]]*)?",
            lambda m: placeholder(citation(m[1])), part, flags=re.I,
        )

        def grouped(match):
            # Ignore any model-supplied rating, label, or N after the PMID list.
            ids = []
            for segment in re.split(r"\bPMIDs?\s*:?\s*", match[1], flags=re.I):
                numeric_list = re.match(r"\s*\d+(?:\s*(?:[,;]|\band\b)\s*\d+)*", segment, re.I)
                if numeric_list:
                    ids.extend(re.findall(r"\d+", numeric_list[0]))
            if not ids:
                return match[0]
            return placeholder(" ".join(citation(pmid) for pmid in dict.fromkeys(ids)))

        part = re.sub(r"[\(\[]\s*PMIDs?\s*:?\s*([^\)\]\n]+)[\)\]]", grouped, part, flags=re.I)
        bare_pattern = (
            r"\bPMID\s*:?\s*(\d+)\b"
            r"(?:\s*·\s*[★☆]{1,5}(?:\s*\d\s*/\s*5)?"
            rf"(?:\s*·\s*{label_pattern}(?:,\s*N\s*=\s*[\d,]+)?)?)?"
        )
        part = re.sub(bare_pattern, lambda m: placeholder(citation(m[1])), part, flags=re.I)
        for index, value in enumerate(replacements):
            part = part.replace(f"\x00ARIA_EVIDENCE_{index}\x00", value)
        return part

    parts = re.split(r"(```[\s\S]*?```|`[^`\n]*`)", text)
    return "".join(part if index % 2 else prose(part) for index, part in enumerate(parts))
