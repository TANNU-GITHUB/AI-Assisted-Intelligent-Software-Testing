"""Streamlit UI for Tasks 1–4: upload code + requirements, run analysis, show results."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code_analysis.analyzer import CodeAnalysisError, analyze_session  # noqa: E402
from config import GEMINI_API_KEY  # noqa: E402
from input_handler.handler import (  # noqa: E402
    InputValidationError,
    create_session,
    load_session,
)
from requirement_analysis.analyzer import (  # noqa: E402
    RequirementAnalysisError,
    analyze_session_requirements,
)

st.set_page_config(
    page_title="AI-Assisted Software Testing",
    page_icon="🧪",
    layout="wide",
)

st.title("AI-Assisted Intelligent Software Testing")
st.caption("Phase 1 — Input handling, source-code analysis, and requirement analysis")

if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    st.warning(
        "Paste your Gemini API key in the project-root `.env` file as "
        "`GEMINI_API_KEY=...` then restart this app. "
        "Get a key at https://aistudio.google.com/apikey"
    )

uploaded = st.file_uploader("Upload a Python source file", type=["py"])
requirements_text = st.text_area(
    "Functional requirements (plain English)",
    height=180,
    placeholder="Example: Members receive a 10% discount. Non-members pay full price. "
    "Negative amounts must be rejected.",
)

run = st.button("Analyze", type="primary", use_container_width=True)

if run:
    try:
        if uploaded is None:
            raise InputValidationError("Please upload a .py source file.")
        source_code = uploaded.getvalue().decode("utf-8")
        session = create_session(
            source_code=source_code,
            requirements_text=requirements_text,
            original_filename=uploaded.name,
        )
        session_id = session["session_id"]
        analyze_session(session_id)
        analyze_session_requirements(session_id)
        result = load_session(session_id)
        st.session_state["last_result"] = result
        st.success(f"Session created: `{session_id}`")
    except UnicodeDecodeError:
        st.error("The uploaded file must be UTF-8 text.")
    except (InputValidationError, CodeAnalysisError, RequirementAnalysisError) as exc:
        st.error(str(exc))

result = st.session_state.get("last_result")
if result:
    st.subheader("Session")
    st.code(result["session_id"])

    code_col, req_col = st.columns(2)
    with code_col:
        st.subheader("Source code analysis")
        functions = (result.get("code_analysis") or {}).get("functions") or []
        if functions:
            st.dataframe(
                [
                    {
                        "function": fn["qualified_name"],
                        "params": ", ".join(p["name"] for p in fn["params"]),
                        "return": fn.get("return_type") or "—",
                        "lines": f"{fn['lineno']}–{fn['end_lineno']}",
                        "branches": fn["branch_count"],
                        "complexity": fn["cyclomatic_complexity"],
                    }
                    for fn in functions
                ],
                use_container_width=True,
            )
        else:
            st.info("No functions found.")

    with req_col:
        st.subheader("Requirement analysis")
        reqs = (result.get("requirement_analysis") or {}).get("requirements") or []
        if reqs:
            st.dataframe(reqs, use_container_width=True)
        else:
            st.info("No structured requirements.")

    with st.expander("Full session JSON"):
        st.json(result)

    st.download_button(
        "Download session.json",
        data=json.dumps(result, indent=2),
        file_name=f"{result['session_id']}_session.json",
        mime="application/json",
    )
