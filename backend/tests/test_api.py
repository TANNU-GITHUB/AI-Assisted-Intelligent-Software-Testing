from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_report_download(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    created = client.post(
        "/api/sessions",
        files={"source_file": ("demo.py", b"def add(a, b):\n    return a + b\n", "text/x-python")},
        data={"requirements_text": "Adding returns the sum.", "run_analysis": "false"},
    )
    session_id = created.json()["session_id"]

    report = client.get(f"/api/sessions/{session_id}/report")
    assert report.status_code == 200
    assert "text/html" in report.headers["content-type"]
    assert "Software Test Report" in report.text


def test_source_update_runs_existing_tests(tmp_path, monkeypatch):
    import execution.analyzer

    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    created = client.post(
        "/api/sessions",
        files={"source_file": ("demo.py", b"def value():\n    return 1\n", "text/x-python")},
        data={"requirements_text": "value returns one.", "run_analysis": "false"},
    )
    session_id = created.json()["session_id"]
    tests_dir = tmp_path / session_id / "tests" / "custom"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_value.py").write_text("def test_value(): pass\n", encoding="utf-8")
    calls = []

    def fake_execution(ran_session_id):
        calls.append(ran_session_id)
        return {"session_id": ran_session_id, "test_execution": {"total": 1, "passed": 1, "tests": []}}

    monkeypatch.setattr(execution.analyzer, "analyze_session_execution", fake_execution)
    updated = client.put(
        f"/api/sessions/{session_id}/source",
        json={"source_code": "def value():\n    return 2\n"},
    )

    assert updated.status_code == 200
    assert calls == [session_id]
    assert updated.json()["regression_awareness"]["execution"]["passed"] == 1


def test_examples():
    res = client.get("/api/examples")
    assert res.status_code == 200
    body = res.json()
    assert "def calculate_discount" in body["source_code"]
    assert "Members receive" in body["requirements_text"]


def test_session_and_code_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    source = tmp_path / "demo.py"
    source.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    res = client.post(
        "/api/sessions",
        files={"source_file": ("demo.py", source.read_bytes(), "text/x-python")},
        data={"requirements_text": "Adding two numbers returns their sum.", "run_analysis": "false"},
    )
    assert res.status_code == 200
    session_id = res.json()["session_id"]
    analyzed = client.post(f"/api/sessions/{session_id}/code-analysis")
    assert analyzed.status_code == 200
    functions = analyzed.json()["code_analysis"]["functions"]
    assert functions[0]["name"] == "add"
    fetched = client.get(f"/api/sessions/{session_id}")
    assert fetched.status_code == 200
    assert "def add" in fetched.json()["source_code"]


def test_rejects_non_python_upload():
    res = client.post(
        "/api/sessions",
        files={"source_file": ("notes.txt", b"print('hi')", "text/plain")},
        data={"requirements_text": "Some requirement", "run_analysis": "false"},
    )
    assert res.status_code == 400
    assert "Python" in res.json()["detail"]


def test_requirement_analysis_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    fake = {
        "model": "test",
        "requirement_count": 1,
        "requirements": [
            {
                "requirement_id": "REQ-01",
                "condition": "is_member is True",
                "expected_result": "discount applies",
                "source_excerpt": "Members receive a discount",
            }
        ],
    }
    monkeypatch.setattr(
        "requirement_analysis.analyzer.analyze_requirements",
        lambda text, **kwargs: fake,
    )
    res = client.post(
        "/api/sessions",
        files={"source_file": ("demo.py", b"def f():\n    return 1\n", "text/x-python")},
        data={"requirements_text": "Members receive a discount.", "run_analysis": "false"},
    )
    session_id = res.json()["session_id"]
    analyzed = client.post(f"/api/sessions/{session_id}/requirement-analysis")
    assert analyzed.status_code == 200
    assert analyzed.json()["requirement_analysis"]["requirements"][0]["requirement_id"] == "REQ-01"
