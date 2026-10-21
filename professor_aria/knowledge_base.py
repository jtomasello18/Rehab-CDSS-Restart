"""Persistent, local PDF knowledge with exact, page-addressable retrieval.

The index is deliberately inspectable: original PDFs and JSON sidecars live in
``knowledge_base/``. Retrieval runs locally and sends only selected passages to
the synthesis layer. No model, network service, or fabricated OCR is used here.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading

try:
    from .evidence_appraisal import appraise_article
except ImportError:  # Streamlit can execute professor_aria as a script directory.
    from evidence_appraisal import appraise_article


DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "knowledge_base"
MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 400
MAX_TEXT_CHARACTERS = 2_000_000
MAX_PAGE_STREAM_BYTES = 10 * 1024 * 1024
_INDEX_VERSION = 2
_LOCK = threading.RLock()
_STOP_WORDS = frozenset("""
a an and are as at be been being but by can could did do does doing each for from
had has have how i if in into is it its may me more most my of on or our please
say says should show so some than that the their them there these they this those
to use used using was we were what when where which who why will with would you
your ask aria evidence article articles pdf pdfs document documents paper papers study
studies page pages p pp uploaded upload exact exactly contents content according
patient patients clinical recent question answer reference references guideline
guidelines finding findings discussion conclusion conclusions abstract methods
results background introduction text reported report information describe tell
""".split())
_SYNONYM_GROUPS = (
    {"stroke", "cva", "cerebrovascular", "hemiplegia", "hemiparesis"},
    {"gait", "walk", "walking", "ambulation", "locomotor", "locomotion"},
    {"fall", "falls", "balance", "postural", "stability"},
    {"spasticity", "spastic", "hypertonia", "baclofen", "antispasmodic"},
    {"afo", "orthosis", "orthotic", "orthoses", "dorsiflexion", "footdrop"},
    {"dysphagia", "swallow", "swallowing", "aspiration"},
    {"aphasia", "communication", "language"},
    {"fatigue", "sedation", "sedating", "drowsiness", "somnolence"},
    {"intensity", "intensive", "aerobic", "endurance", "cardiorespiratory", "cardiovascular", "fitness"},
    {"hrr", "reserve", "karvonen"},
    {"hrmax", "maximum", "maximal"},
    {"thrombolysis", "thrombolytic", "alteplase", "tenecteplase", "tpa", "ivt"},
    {"thrombectomy", "endovascular", "reperfusion", "evt"},
    {"ischemic", "ischaemic", "ischemia", "ischaemia", "infarction"},
    {"frequency", "weekly", "week", "days", "sessions"},
    {"duration", "minutes", "mins"},
)


class KnowledgeBaseError(ValueError):
    """An actionable ingestion or local-storage error suitable for the UI."""


def _root(root: Path | str | None) -> Path:
    path = Path(root) if root is not None else DEFAULT_ROOT
    if path.is_symlink():
        raise KnowledgeBaseError("The knowledge-base directory must not be a symbolic link.")
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve(strict=True)
    except OSError as exc:
        raise KnowledgeBaseError("The local knowledge-base directory is not available or writable.") from exc


def _safe_filename(filename: str) -> str:
    if (not isinstance(filename, str) or not filename.strip()
            or filename != Path(filename).name or "/" in filename or "\\" in filename
            or any(ord(char) < 32 for char in filename)
            or filename in {".", ".."}):
        raise KnowledgeBaseError("Choose a PDF with a plain filename, without folders or path separators.")
    if Path(filename).suffix.lower() != ".pdf":
        raise KnowledgeBaseError("Only PDF files can be added to the Evidence Bridge knowledge base.")
    if len(filename.encode("utf-8")) > 220:
        raise KnowledgeBaseError("The PDF filename is too long; shorten it and upload again.")
    return filename


def _safe_path(base: Path, name: str) -> Path:
    if not name or name != Path(name).name or "/" in name or "\\" in name:
        raise KnowledgeBaseError("Invalid knowledge-base file path.")
    target = base / name
    if target.is_symlink() or target.parent.resolve() != base:
        raise KnowledgeBaseError("Symbolic links are not accepted as knowledge-base documents.")
    return target


def _read_bytes(path: Path, limit: int) -> bytes:
    try:
        if path.is_symlink():
            raise KnowledgeBaseError("Symbolic links are not accepted as knowledge-base documents.")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            data = stream.read(limit + 1)
    except OSError as exc:
        raise KnowledgeBaseError(f"Unable to read {path.name}; check file permissions and try again.") from exc
    if len(data) > limit:
        raise KnowledgeBaseError(f"{path.name} exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB upload limit.")
    return data


def _atomic_write(path: Path, data: bytes) -> None:
    temporary = None
    try:
        if path.is_symlink():
            raise KnowledgeBaseError("Refusing to replace a symbolic link in the knowledge base.")
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".aria-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise KnowledgeBaseError("Unable to persist the PDF index; check available disk space and permissions.") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _sidecar(pdf: Path) -> Path:
    return _safe_path(pdf.parent, pdf.name + ".aria.json")


def _pdf_title(filename: str, metadata, pages: dict[int, str]) -> str:
    title = str(getattr(metadata, "title", "") or "").strip()
    if title and title.lower() not in {"untitled", "document", "microsoft word", "pdf"}:
        return title[:250]
    first_lines = [line.strip() for line in pages.get(1, "").splitlines() if line.strip()]
    for line in first_lines[:5]:
        if 12 <= len(line) <= 250 and len(line.split()) >= 3:
            return line
    return Path(filename).stem.replace("_", " ")


def _extract_pdf(filename: str, data: bytes, stored_name: str | None = None) -> dict:
    if not data:
        raise KnowledgeBaseError("The PDF is empty. Select a complete, searchable PDF and upload again.")
    if len(data) > MAX_PDF_BYTES:
        raise KnowledgeBaseError(f"The PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB upload limit.")
    if b"%PDF-" not in data[:1024]:
        raise KnowledgeBaseError("This file is not a valid PDF. Export it as a PDF and upload again.")
    try:
        from pypdf import PdfReader, apply_configuration
    except ImportError as exc:
        raise KnowledgeBaseError("PDF extraction requires pypdf. Install the project's Python requirements and restart ARIA.") from exc
    try:
        # pypdf's context-local limits also bound compressed streams and parser
        # work, before a small compressed upload can expand without a bound.
        with apply_configuration(
            maximum_declared_stream_length=MAX_PAGE_STREAM_BYTES,
            array_based_stream_maximum_output_length=MAX_PAGE_STREAM_BYTES,
            zlib_maximum_output_length=MAX_PAGE_STREAM_BYTES,
            lzw_maximum_output_length=MAX_PAGE_STREAM_BYTES,
            run_length_maximum_output_length=MAX_PAGE_STREAM_BYTES,
            brotli_maximum_output_length=MAX_PAGE_STREAM_BYTES,
            stream_decoding_work_maximum_length=MAX_PAGE_STREAM_BYTES * 3,
            stream_parsing_work_maximum_count=300_000,
            page_tree_maximum_entries=MAX_PDF_PAGES * 4,
        ):
            reader = PdfReader(io.BytesIO(data), strict=False)
            if reader.is_encrypted and not reader.decrypt(""):
                raise KnowledgeBaseError("The PDF is password-protected. Upload an unlocked, searchable copy.")
            count = len(reader.pages)
            if not count:
                raise KnowledgeBaseError("The PDF has no pages. Upload a complete, searchable PDF.")
            if count > MAX_PDF_PAGES:
                raise KnowledgeBaseError(f"This PDF has {count} pages; the limit is {MAX_PDF_PAGES}. Upload the relevant chapters separately.")
            pages, empty, total = {}, [], 0
            for number, page in enumerate(reader.pages, 1):
                contents = page.get_contents()
                if contents is not None and len(contents.get_data()) > MAX_PAGE_STREAM_BYTES:
                    raise KnowledgeBaseError(f"Page {number} is too complex to extract safely. Re-export this PDF or upload a smaller section.")
                text = page.extract_text() or ""
                total += len(text)
                if total > MAX_TEXT_CHARACTERS:
                    raise KnowledgeBaseError("The extracted PDF text is too large. Upload the relevant chapters separately.")
                pages[number] = text
                if not text.strip():
                    empty.append(number)
            if len(empty) == count:
                raise KnowledgeBaseError("No searchable text was found. This may be a scanned/image-only PDF; run OCR and upload the searchable copy.")
            title = _pdf_title(filename, reader.metadata, pages)
    except KnowledgeBaseError:
        raise
    except Exception as exc:
        raise KnowledgeBaseError("The PDF could not be read reliably. Re-export it as an unlocked, searchable PDF and upload again.") from exc
    digest = hashlib.sha256(data).hexdigest()
    full_text = "\n\n".join(pages.values())
    # Bibliographies should not upgrade the source based on cited study titles.
    references = re.search(r"\n\s*(?:references|bibliography|works cited)\s*\n", full_text, re.I)
    appraisal_text = full_text[:references.start()] if references else full_text
    document = appraise_article({
        "id": "pdf-" + digest[:24], "document_id": "pdf-" + digest[:24],
        "source_type": "uploaded_pdf", "filename": filename, "original_filename": filename,
        "stored_filename": stored_name or filename, "title": title,
        "page_count": count, "pages_text": pages,
        "upload_time": datetime.now(timezone.utc).isoformat(),
        "content_hash": digest, "abstract": appraisal_text[:50_000], "appraisal_text": appraisal_text[:50_000],
        "publication_types": [], "index_version": _INDEX_VERSION,
        "extraction_warnings": ([
            "No extractable text on page(s): " + ", ".join(map(str, empty))
            + ". These pages are not indexed; apply OCR to search or cite their contents."
        ] if empty else []),
    })
    document["appraisal_limitations"].append(
        "Design and sample size were inferred automatically from extracted PDF text; verify the original methods before applying the grade."
    )
    return document


def _write_metadata(pdf: Path, document: dict) -> None:
    stat = pdf.stat()
    document["file_size"] = stat.st_size
    document["file_mtime_ns"] = stat.st_mtime_ns
    _atomic_write(_sidecar(pdf), json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8"))


def _cached_document(pdf: Path) -> dict | None:
    sidecar = _sidecar(pdf)
    if not sidecar.exists():
        return None
    try:
        document = json.loads(_read_bytes(sidecar, MAX_TEXT_CHARACTERS * 8))
        stat = pdf.stat()
        digest = str(document.get("content_hash", ""))
        if (document.get("index_version") != _INDEX_VERSION
                or document.get("source_type") != "uploaded_pdf"
                or document.get("stored_filename") != pdf.name
                or document.get("file_size") != stat.st_size
                or document.get("file_mtime_ns") != stat.st_mtime_ns
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
                or document.get("document_id") != "pdf-" + digest[:24]
                or not isinstance(document.get("pages_text"), dict)):
            return None
        _safe_filename(document.get("filename", ""))
        document["pages_text"] = {int(page): text for page, text in document["pages_text"].items()}
        return document
    except (KnowledgeBaseError, ValueError, TypeError, OSError):
        return None


def _uploaded_documents(base: Path, deduplicate: bool = True) -> list[dict]:
    documents, hashes = [], set()
    for path in sorted(base.iterdir(), key=lambda item: item.name.casefold()):
        if path.suffix.lower() != ".pdf" or path.is_symlink() or not path.is_file():
            continue
        try:
            document = _cached_document(path)
            if document is None:
                data = _read_bytes(path, MAX_PDF_BYTES)
                document = _extract_pdf(_safe_filename(path.name), data, path.name)
                _write_metadata(path, document)
            if not deduplicate or document["content_hash"] not in hashes:
                documents.append(document)
                hashes.add(document["content_hash"])
        except KnowledgeBaseError as exc:
            # Keep external files visible with an actionable status; they never
            # enter retrieval unless extraction completed successfully.
            documents.append({
                "id": "error-" + hashlib.sha256(path.name.encode()).hexdigest()[:24],
                "document_id": "error-" + hashlib.sha256(path.name.encode()).hexdigest()[:24],
                "source_type": "uploaded_pdf", "filename": path.name,
                "stored_filename": path.name, "title": path.stem,
                "page_count": 0, "pages_text": {}, "upload_time": None,
                "content_hash": None, "extraction_error": str(exc),
                "extraction_warnings": [],
            })
    return documents


def list_documents(root: Path | str | None = None) -> list[dict]:
    """List only PDFs on disk, indexing files copied in from outside ARIA."""
    with _LOCK:
        return _uploaded_documents(_root(root))


def ingest_pdf(filename: str, data: bytes, root: Path | str | None = None) -> dict:
    """Extract and durably store a PDF; identical content is ingested only once."""
    filename = _safe_filename(filename)
    if not isinstance(data, bytes):
        raise KnowledgeBaseError("The PDF upload must contain bytes.")
    # Validate and extract before committing anything to the active directory.
    document = _extract_pdf(filename, data)
    with _LOCK:
        base = _root(root)
        for existing in _uploaded_documents(base):
            if existing.get("content_hash") == document["content_hash"]:
                return existing
        stored = filename
        target = _safe_path(base, stored)
        if target.exists():
            stored = f"{Path(filename).stem[:100]}-{document['content_hash'][:12]}.pdf"
            target = _safe_path(base, stored)
            if target.exists():
                raise KnowledgeBaseError("A conflicting document already exists. Rename the new PDF and upload again.")
        document["stored_filename"] = stored
        document["filename"] = stored
        _atomic_write(target, data)
        _write_metadata(target, document)
        return document


def remove_document(document_id: str, root: Path | str | None = None) -> None:
    """Remove an uploaded PDF and sidecar. Fixed references cannot be removed."""
    with _LOCK:
        base = _root(root)
        matches = [doc for doc in _uploaded_documents(base, deduplicate=False) if doc.get("document_id") == document_id]
        if not matches:
            raise KnowledgeBaseError("That uploaded PDF is no longer in the knowledge base; refresh the workspace.")
        try:
            # Remove content first: an orphaned sidecar is deliberately never
            # enough to reactivate a document during a future directory scan.
            # Exact duplicate copies represent one active logical document.
            for document in matches:
                pdf = _safe_path(base, document["stored_filename"])
                pdf.unlink()
                _sidecar(pdf).unlink(missing_ok=True)
        except OSError as exc:
            raise KnowledgeBaseError("Unable to remove this PDF; check local file permissions.") from exc


def get_document_bytes(document_id: str, root: Path | str | None = None) -> bytes:
    """Read an original uploaded PDF using only a known, scoped document ID."""
    with _LOCK:
        base = _root(root)
        for document in _uploaded_documents(base):
            if document.get("document_id") == document_id:
                return _read_bytes(_safe_path(base, document["stored_filename"]), MAX_PDF_BYTES)
    raise KnowledgeBaseError("The original PDF is unavailable or has been removed.")


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z][a-z0-9-]*", text.casefold()) if token not in _STOP_WORDS and len(token) > 1]


def _query_terms(query: str) -> tuple[set[str], set[str]]:
    original = set(_tokens(query))
    expanded = set(original)
    for group in _SYNONYM_GROUPS:
        if original & group:
            expanded.update(group)
    if "foot" in original and "drop" in original:
        expanded.update({"afo", "dorsiflexion", "orthosis", "footdrop"})
    return original, expanded


def _is_reference_page(text: str) -> bool:
    """Exclude bibliography pages without excluding prose with a few citations."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    heading = any(re.fullmatch(r"(?:references|bibliography|works cited|literature cited)(?:\s+\d+)?", line, re.I) for line in lines[:6])
    numbered = sum(bool(re.match(r"^(?:\[\d+\]|\d+[.)])\s+", line)) for line in lines)
    doi_count = len(re.findall(r"(?:doi\s*:|10\.\d{4,9}/)", text, re.I))
    citation_years = len(re.findall(r"\b(?:19|20)\d{2}\s*;\s*\d+", text))
    return heading or (numbered >= 5 and doi_count + citation_years >= 5) or (doi_count >= 8 and citation_years >= 5)


def _passages(document: dict) -> list[dict]:
    """Each retrieval unit is a complete extracted PDF page."""
    passages = []
    for page, text in (document.get("pages_text") or {}).items():
        if not str(text).strip() or _is_reference_page(str(text)):
            continue
        identifier = f"{document['document_id']}:p{int(page)}:0"
        passages.append({"id": identifier, "passage_id": identifier, "page_number": int(page),
                         "document_name": document.get("filename") or document.get("title"),
                         "retrieval_unit": "page", "text": str(text)})
    return passages


_CLINICAL_WEIGHTS = {
    "stroke": .65, "rehabilitation": .65, "therapy": .6,
    "aerobic": 2.5, "cardiorespiratory": 2.8, "hrr": 3, "hrmax": 3,
    "intensity": 2.2, "frequency": 2, "duration": 1.8, "screening": 1.8,
    "spasticity": 2.4, "baclofen": 2.5, "sedation": 2.3, "dysphagia": 2.5,
    "aphasia": 2.3, "thrombolysis": 3, "thrombectomy": 3, "reperfusion": 3,
    "alteplase": 3, "tenecteplase": 3, "ischemic": 1.8, "acute": 1.8,
}
_CLINICAL_PHRASES = (
    "heart rate reserve", "acute ischemic stroke", "aerobic exercise", "high intensity",
    "gait training", "blood pressure", "swallow screening", "large vessel occlusion",
)


def search_knowledge_base(query: str, max_documents: int = 5, max_passages: int = 12,
                          root: Path | str | None = None) -> list[dict]:
    """Score every page of real PDFs on disk and return up to 12 full pages.

    Naming a PDF boosts that document; an explicit page request scopes its page
    locators. Bibliographies do not enter context.
    """
    if not query or not query.strip() or max_documents <= 0 or max_passages <= 0:
        return []
    max_documents, max_passages = min(max_documents, 12), min(max_passages, 12)
    documents = [doc for doc in list_documents(root) if not doc.get("extraction_error")]
    named = []
    clinical_query = query
    for doc in documents:
        names = [doc.get("filename", ""), doc.get("title", "")]
        if doc.get("filename"):
            names.append(Path(doc["filename"]).stem)
        matched = [name for name in names if len(name) >= 8 and name.casefold() in query.casefold()]
        if matched:
            named.append(doc["document_id"])
            for name in sorted(matched, key=len, reverse=True):
                clinical_query = re.sub(re.escape(name), " ", clinical_query, flags=re.I)
    page_match = re.search(r"\b(?:pages?|pp?\.?)\s*(\d+)\b", query, re.I)
    requested_page = int(page_match.group(1)) if page_match else None
    clinical_query = re.sub(r"\b(?:pages?|pp?\.?)\s*\d+\b", " ", clinical_query, flags=re.I)
    original, terms = _query_terms(clinical_query)
    overview_words = {"summarize", "summary", "overview", "brief", "give", "provide", "explain", "compare", "all", "list", "available", "active", "knowledge", "base", "sources", "pdfs", "say", "says"}
    overview = not (original - overview_words)
    named_pdf_ids = {doc["document_id"] for doc in documents if doc["document_id"] in named and doc.get("source_type") == "uploaded_pdf"}
    candidates = []
    for doc in documents:
        # A document/page lookup should not silently substitute another PDF.
        if requested_page is not None and named_pdf_ids and doc.get("source_type") == "uploaded_pdf" and doc["document_id"] not in named_pdf_ids:
            continue
        title_terms = set(_tokens(f"{doc.get('title', '')} {doc.get('filename', '')}"))
        for passage in _passages(doc):
            if requested_page is not None and passage["page_number"] is not None and passage["page_number"] != requested_page:
                continue
            counter = Counter(_tokens(passage["text"] + " " + str(passage.get("section") or "")))
            candidates.append((doc, passage, counter, title_terms))
    if not candidates:
        return []
    frequencies = Counter(term for _, _, counter, _ in candidates for term in counter)
    mean_length = sum(sum(counter.values()) for _, _, counter, _ in candidates) / len(candidates) or 1
    ranked = []
    normalized_query = re.sub(r"[-–—]", " ", clinical_query.casefold())
    for doc, passage, counter, title_terms in candidates:
        overlap = terms.intersection(counter)
        title_overlap = original & title_terms
        is_named = doc["document_id"] in named
        if not overlap and not (is_named and overview) and not (overview and not named):
            continue
        length = sum(counter.values())
        score = 0.0
        for term in overlap:
            weight = (1 if term in original else .45) * _CLINICAL_WEIGHTS.get(term, 1)
            idf = math.log(1 + (len(candidates) - frequencies[term] + .5) / (frequencies[term] + .5))
            count = counter[term]
            score += weight * idf * count * 2.2 / (count + 1.2 * (.25 + .75 * length / mean_length))
        normalized_page = re.sub(r"[-–—]", " ", passage["text"].casefold())
        score += 3 * sum(phrase in normalized_query and phrase in normalized_page for phrase in _CLINICAL_PHRASES)
        score += min(2, len(title_overlap) * .35)
        if is_named:
            score += 2
        if overview:
            score += 1 + 1 / max(1, passage.get("page_number") or 1)
        if score > 0:
            ranked.append((score, doc, {**passage, "relevance_score": round(score, 6)}))
    ranked.sort(key=lambda item: (-item[0], item[1]["document_id"], item[2]["page_number"] or 0, item[2]["passage_id"]))
    # Fill the context in global clinical-relevance order.
    selected, seen, doc_ids = [], set(), set()
    def add(item):
        key = item[2]["passage_id"]
        if key in seen or len(selected) >= max_passages:
            return
        if item[1]["document_id"] not in doc_ids and len(doc_ids) >= max_documents:
            return
        selected.append(item)
        seen.add(key)
        doc_ids.add(item[1]["document_id"])
    for item in ranked:
        add(item)
    selected.sort(key=lambda item: -item[0])
    sources = {}
    for score, document, passage in selected:
        document_id = document["document_id"]
        if document_id not in sources:
            source = {key: value for key, value in document.items() if key not in {"pages_text", "abstract", "sections"}}
            source["passages"] = []
            source["relevance_score"] = round(score, 6)
            source["source_badge"] = "Evidence Bridge Knowledge Base"
            sources[document_id] = source
        sources[document_id]["passages"].append(passage)
    return list(sources.values())


def format_kb_citation(source: dict, passage: dict | None = None) -> str:
    """Create a citation using only source metadata and a verified passage locator."""
    passage = passage or next(iter(source.get("passages") or []), {})
    stars = max(1, min(5, int(source.get("star_rating") or 1)))
    display = "★" * stars + "☆" * (5 - stars)
    if source.get("source_type") == "uploaded_pdf":
        location = f", p. {passage['page_number']}" if passage.get("page_number") is not None else ""
        return f"(Uploaded PDF: {source.get('filename') or source.get('title')}{location} · {display} {stars}/5)"
    section = f", section: {passage['section']}" if passage.get("section") else ""
    return f"(Fixed CPG Reference: {source.get('title')}{section} · {display} {stars}/5)"
