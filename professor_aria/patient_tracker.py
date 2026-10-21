"""Local, page-addressable Evidence Bridge context for the patient tracker."""

from .knowledge_base import KnowledgeBaseError, search_knowledge_base


SPECIALTY_QUERIES = {
    "pt": "stroke gait walking balance falls ankle foot orthosis rehabilitation fatigue",
    "physician": "stroke baclofen spasticity sedation weakness botulinum toxin orthosis falls",
    "ot": "stroke upper limb spasticity elbow shoulder subluxation self feeding occupational therapy",
    "slp": "stroke aphasia naming communication cognitive fatigue speech language swallowing",
}


def tracker_evidence() -> dict:
    """Refresh from real PDFs on every tracker render, including after removal.

    These are relevant passages for clinician review, not a claim that a matched
    document validates every case-specific action displayed by the frontend.
    """
    result = {"sources": {}}
    try:
        for specialty, query in SPECIALTY_QUERIES.items():
            matches = search_knowledge_base(query, max_documents=2, max_passages=2)
            result["sources"][specialty] = [
                {
                    "document_id": source["document_id"],
                    "filename": source["filename"],
                    "star_rating": max(1, min(5, int(source.get("star_rating") or 1))),
                    "page_number": passage["page_number"],
                    "text": passage["text"],
                }
                for source in matches if source.get("source_type") == "uploaded_pdf"
                for passage in source.get("passages", [])
                if passage.get("page_number") is not None
            ]
    except (KnowledgeBaseError, OSError):
        result["error"] = "Evidence Bridge could not read the local PDFs. Open the library to check the documents."
    return result
