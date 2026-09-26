import pytest

from input_handler.handler import InputValidationError, create_session, load_session


@pytest.fixture(autouse=True)
def isolated_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    return tmp_path


def test_create_session_saves_files(tmp_path):
    payload = create_session(
        source_code="def add(a, b):\n    return a + b\n",
        requirements_text="Adding two numbers should return their sum.",
        original_filename="math_utils.py",
    )
    session_id = payload["session_id"]
    folder = tmp_path / session_id
    assert (folder / "source.py").is_file()
    assert (folder / "requirements.txt").is_file()
    assert payload["status"] == "created"
    loaded = load_session(session_id)
    assert loaded["inputs"]["original_filename"] == "math_utils.py"


def test_rejects_non_python_file():
    with pytest.raises(InputValidationError, match="Only Python"):
        create_session(
            source_code="print('hi')",
            requirements_text="Print hello",
            original_filename="notes.txt",
        )


def test_rejects_empty_source():
    with pytest.raises(InputValidationError, match="empty"):
        create_session(
            source_code="   \n",
            requirements_text="Some requirement",
            original_filename="app.py",
        )


def test_rejects_empty_requirements():
    with pytest.raises(InputValidationError, match="Requirements"):
        create_session(
            source_code="def f():\n    pass\n",
            requirements_text="  ",
            original_filename="app.py",
        )
