# Figma Streamlit Component

Production-oriented Streamlit custom component scaffold for rendering exported React/Figma components.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
streamlit run app.py
```

Evidence retrieval in `professor_aria/rag.py` searches rehabilitation,
medication/safety, and biomechanical dimensions independently when present. Each
search uses MeSH/keyword concept groups and broadens empty queries before asking
for clarification. Results are merged by PMID in alternating facet order, up to
eight articles total; search attempts and coverage limitations accompany the sources.
The same pipeline powers the integrated dashboard, standalone professor app, and
`aria_chat.py`.

Model JSON extraction tolerates code fences, commentary, and trailing objects.
If optimization fails, standard clinical keyword plans replace narrative searches.
PubMed calls are paced to [NCBI's E-utilities limits](https://eutilities.github.io/site/API_Key/usageandkey/).
Genuine empty results and service failures remain explicit; articles are never invented.

The shared evidence appraisal engine (`professor_aria/evidence_appraisal.py`) grades
every retrieved article using PubMed publication types, title, reported study
methods, and participant sample size. It prioritizes higher grades within each
clinical facet before selecting up to eight sources, then sorts the final sources
from five to one star. The dashboard, standalone app, and Ask ARIA use the same
cards, legend, methodological rationale, and graded inline PMID citations.

| ARIA stars | Design and sample-size tier |
| --- | --- |
| 5 | CPG, Cochrane/systematic review, meta-analysis |
| 4 | RCT with N ≥ 50 or multicenter randomization |
| 3 | Small/unknown-size RCT, prospective cohort, clinical trial |
| 2 | Retrospective, case-control, cross-sectional, single-group pre/post |
| 1 | Case report, narrative review, opinion, animal/bench research, unclassified evidence |

These are **ARIA's automated design/sample-size grades**, not validated PEDro
scores or formal GRADE certainty assessments. The requested Level I-A/I-B/II/III-IV/V
labels describe this local hierarchy. Trial registration/protocols and retracted or
nonhuman studies do not become high-grade human treatment evidence. Unreported
sample size and methodological limitations remain visible. The N ≥ 50 rule is a
ranking threshold, not proof of statistical power. Claude receives the grades and
must anchor recommendations in relevant 4–5-star sources, qualify lower-grade
evidence, and disclose when stronger evidence is missing. Follow-ups receive the
same graded source catalog; citation grades are normalized against it.

## Evidence Bridge

The Evidence Bridge tab is a native Streamlit workspace. Drop one or more PDFs
into its upload area to extract and persist each page in `knowledge_base/`, together
with the original document, upload time, content hash, and automated study appraisal.
The active library scans this directory on reruns, including PDFs copied there
outside the app. Identical uploads deduplicate; different documents sharing a
filename receive distinct filenames. Download and Remove act on the stored originals.

The Evidence Query chat ranks complete pages across uploaded PDFs and the fixed
reference sections using clinical keyword weights and medical synonym expansion.
Bibliographies are excluded. Up to twelve full pages/sections enter Claude's context
with document names and physical page locators. Answers are displayed independently
of optional quote/JSON formatting: citation mismatches never suppress the response.
Light-blue citation boxes quote actual extracted source text; unsupported locators
are marked inline. Image-only PDFs need OCR before upload. Limits are 25 MB, 400 pages, and
two million extracted characters per document. `pypdf>=6.21.1` is required.

Three fixed source-linked references cover AHA/ASA stroke rehabilitation, APTA/ANPT
physical therapy, and ASHA/ROMA communication/swallowing outcomes. These are curated
summaries, not full guideline copies. They retain a conservative 1-star summary
appraisal and section citations. Upload the original guideline PDF for exact original
text and page citations. The three reference records cannot be deleted through the UI.

Initial Evidence & Guidance searches and context-backed follow-ups search PubMed
and the current knowledge base. Up to eight PubMed papers and eight local documents
(twelve full retrieved pages/sections) enter the evidence context. Follow-ups re-read the library,
so newly uploaded PDFs become searchable and removed PDFs stop entering new answers.
Matched local sources appear beside PubMed in the shared evidence drawer, with
their own source badge, grades, page/section excerpts, and primary-reference links.

Uploading and browsing remain available without an Anthropic key. Evidence Query
and clinical synthesis use `ANTHROPIC_API_KEY` from `.env` or Streamlit secrets;
the query sends only retrieved excerpts rather than the complete document.

Evidence Bridge and guidance use the official ARIA emblem for assistant messages
and a teal PT clinician badge. Shared input-focus styling uses `#145b6e`;
the Bridge workspace uses 16–17 px response text and larger document titles.

Methodological references: [Oxford OCEBM Levels of Evidence](https://www.cebm.ox.ac.uk/resources/levels-of-evidence/ocebm-levels-of-evidence),
[GRADE Working Group](https://www.gradeworkinggroup.org/), and
[PEDro scale](https://pedro.org.au/english/resources/pedro-scale/).

Run the regression suite without making Claude or PubMed requests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

