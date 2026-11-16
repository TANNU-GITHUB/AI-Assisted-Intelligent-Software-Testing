import json
import threading
import time

import pytest

from input_handler.handler import (
    InputValidationError,
    create_session,
    load_session,
    save_session,
    session_locked,
)


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


def test_save_session_remains_valid_under_parallel_writes(tmp_path):
    payload = create_session(
        source_code="def add(a, b):\n    return a + b\n",
        requirements_text="The function should add two numbers.",
        original_filename="math_utils.py",
    )
    session_id = payload["session_id"]
    start = threading.Barrier(2)

    def writer(tag: str) -> None:
        start.wait()
        for i in range(200):
            save_session({**payload, "status": "running", "writer": tag, "counter": i})
            time.sleep(0.0005)

    first = threading.Thread(target=writer, args=("left",))
    second = threading.Thread(target=writer, args=("right",))
    first.start()
    second.start()
    first.join()
    second.join()

    loaded = load_session(session_id)
    assert loaded["session_id"] == session_id
    manifest = tmp_path / session_id / "session.json"
    assert json.loads(manifest.read_text(encoding="utf-8"))["session_id"] == session_id


def test_session_operations_preserve_concurrent_read_modify_write_updates():
    payload = create_session(
        source_code="def add(a, b):\n    return a + b\n",
        requirements_text="The function should add two numbers.",
        original_filename="math_utils.py",
    )
    session_id = payload["session_id"]
    first_loaded = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    second_loaded = threading.Event()
    errors = []

    @session_locked
    def update_field(session_id: str, field: str, pause_after_read: bool = False) -> None:
        current = load_session(session_id)
        if pause_after_read:
            first_loaded.set()
            if not release_first.wait(timeout=5):
                raise TimeoutError("Timed out waiting to finish the first session update.")
        if field == "second_update":
            second_loaded.set()
        current[field] = True
        save_session(current)

    def update_first() -> None:
        try:
            update_field(session_id, "first_update", pause_after_read=True)
        except Exception as exc:
            errors.append(exc)

    def update_second() -> None:
        second_started.set()
        try:
            update_field(session_id, "second_update")
        except Exception as exc:
            errors.append(exc)

    first = threading.Thread(target=update_first)
    second = threading.Thread(target=update_second)
    first.start()
    assert first_loaded.wait(timeout=5)
    second.start()
    assert second_started.wait(timeout=5)
    assert not second_loaded.wait(timeout=0.1)
    release_first.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    loaded = load_session(session_id)
    assert loaded["first_update"] is True
    assert loaded["second_update"] is True


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
