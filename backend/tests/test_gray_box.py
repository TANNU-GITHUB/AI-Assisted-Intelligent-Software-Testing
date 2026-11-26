from test_generation.gray_box import GrayBoxError, analyze_session_gray_box


def test_gray_box_fallback_writes_pytest_file(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)

    payload = __import__("input_handler.handler", fromlist=["create_session"]).create_session(
        source_code=(
            "def discount(price, is_member):\n"
            "    if price < 0:\n"
            "        raise ValueError('negative')\n"
            "    if is_member:\n"
            "        return price * 0.9\n"
            "    return price\n"
        ),
        requirements_text="Members get a discount and negative prices are rejected.",
        original_filename="gray_demo.py",
    )
    session_id = payload["session_id"]

    from code_analysis.analyzer import analyze_session
    from requirement_analysis.analyzer import analyze_session_requirements

    analyze_session(session_id)
    analyze_session_requirements(session_id)

    monkeypatch.setattr("test_generation.gray_box.llm_is_configured", lambda: False)
    result = analyze_session_gray_box(session_id)
    gray = result["gray_box_tests"]
    assert gray["test_count"] >= 1
    assert gray["generation_source"] in {"fallback", "heuristic-fallback"}
    assert (tmp_path / session_id / "tests" / "gray_box" / "test_gray_box.py").is_file()
    assert all(case["test_type"] == "gray_box" for case in gray["test_cases"])


def test_gray_box_requires_code_and_requirement_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    from input_handler.handler import create_session

    payload = create_session(
        source_code="def add(a, b):\n    return a + b\n",
        requirements_text="The sum is returned.",
        original_filename="demo.py",
    )
    try:
        analyze_session_gray_box(payload["session_id"])
    except GrayBoxError as exc:
        assert "requirement analysis" in str(exc) or "code analysis" in str(exc)
    else:
        raise AssertionError("gray-box generation should require prior analysis")


def test_gray_box_semantically_links_requirements_and_trims_llm_context():
    from test_generation.gray_box import _fallback_cases, _generate_cases_with_llm

    reqs = [
        {"requirement_id": "REQ-01", "condition": "calc_fee must raise ValueError when amount < 0.", "expected_result": "Raises ValueError"},
        {"requirement_id": "REQ-02", "condition": "calc_fee returns 10.0 when amount >= 100.", "expected_result": "Returns 10.0"},
    ]
    api = [{"name": "calc_fee", "return_type": "float", "params": [{"name": "amount", "annotation": "float"}]}]
    fns = [{"name": "calc_fee", "qualified_name": "calc_fee", "params": api[0]["params"], "branches": [{"type": "if", "lineno": 2, "condition": "amount < 0", "has_else": False}]}]
    src = "def calc_fee(amount: float) -> float:\n    if amount < 0:\n        raise ValueError('neg')\n    return 10.0 if amount >= 100 else 0.0\n"

    cases = _fallback_cases(reqs, api, fns, src)
    valid_non_error = [c for c in cases if c["expected_exception"] is None]
    assert valid_non_error
    assert all(c["requirement_id"] == "REQ-02" for c in valid_non_error)

    captured_prompts = []
    _generate_cases_with_llm(
        structured_requirements=reqs,
        public_api=api,
        functions=fns,
        source_code="x = 1\n" * 5000,
        api_key="k",
        model_name="m",
        llm_call=lambda prompt, *_args: captured_prompts.append(prompt) or '[{"case_id":"g1","description":"No error on valid input","requirement_id":"BAD","function_name":"calc_fee","input":{"amount":120.0}}]',
    )
    assert len(captured_prompts[0]) < 12000
