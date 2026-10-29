"""Session persistence for the synthetic education curriculum; no credit certification."""

from functools import lru_cache
import json
from pathlib import Path

import streamlit as st


@lru_cache(maxsize=1)
def curriculum():
    # One question bank is shared with React so allowed IDs/options cannot drift.
    path = Path(__file__).resolve().parent.parent / "frontend" / "src" / "data" / "education.json"
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_progress(value):
    result = {"version": 1, "answers": {}}
    if (not isinstance(value, dict) or type(value.get("version")) is not int
            or value["version"] != 1 or not isinstance(value.get("answers"), dict)):
        return result
    for patient in curriculum()["patients"]:
        entries = value["answers"].get(patient["id"])
        if not isinstance(entries, dict):
            continue
        for question in patient["questions"]:
            answer = entries.get(question["id"])
            if not isinstance(answer, dict):
                continue
            option = answer.get("option")
            if type(option) is not int or not 0 <= option < len(question["options"]):
                continue
            confidence = answer.get("confidence")
            result["answers"].setdefault(patient["id"], {})[question["id"]] = {
                "option": option,
                "confidence": confidence if confidence in ("high", "review") else None,
            }
    return result


def render_education(figma_component, role="Viewer"):
    progress = normalize_progress(st.session_state.get("education_progress"))
    patients = {patient["id"]: patient for patient in curriculum()["patients"]}
    valid_specialties = {item["id"] for item in curriculum()["specialties"]}
    specialty = st.session_state.get("education_specialty", "md")
    if not isinstance(specialty, str) or specialty not in valid_specialties:
        specialty = "md"
    valid_patients = {pid for pid, patient in patients.items() if patient["specialty"] == specialty}
    selected = st.session_state.get("education_patient")
    if not isinstance(selected, str) or selected not in valid_patients:
        selected = next(patient["id"] for patient in patients.values() if patient["specialty"] == specialty)
    event = figma_component(
        view="education", role=role, education_progress=progress,
        education_patient=selected, education_specialty=specialty, key="aria_education",
    )
    if not isinstance(event, dict) or event.get("type") != "education_progress":
        return
    request_id = event.get("requestId")
    if (not isinstance(request_id, str) or not 0 < len(request_id) <= 100
            or request_id == st.session_state.get("education_last_request")):
        return
    # Invalid envelopes must not clear existing answers. Valid resets use an empty map.
    candidate = event.get("progress")
    if (not isinstance(candidate, dict) or type(candidate.get("version")) is not int
            or candidate["version"] != 1 or not isinstance(candidate.get("answers"), dict)):
        return
    st.session_state.education_progress = normalize_progress(candidate)
    patient_id = event.get("patientId")
    next_specialty = event.get("specialty")
    # Older clients send patientId alone; infer its bank without dropping answers.
    if next_specialty is None and isinstance(patient_id, str) and patient_id in patients:
        next_specialty = patients[patient_id]["specialty"]
    if isinstance(next_specialty, str) and next_specialty in valid_specialties:
        st.session_state.education_specialty = next_specialty
        if (isinstance(patient_id, str) and patient_id in patients
                and patients[patient_id]["specialty"] == next_specialty):
            st.session_state.education_patient = patient_id
        else:
            st.session_state.education_patient = next(p["id"] for p in patients.values() if p["specialty"] == next_specialty)
    st.session_state.education_last_request = request_id
    st.rerun()
