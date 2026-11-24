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
