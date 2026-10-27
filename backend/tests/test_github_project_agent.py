from agents.github_project_agent import collect_project_files


def test_collect_project_files_walks_tree(monkeypatch):
    tree = {
        "tree": [
            {"path": "app.py", "type": "blob", "size": 40},
            {"path": "pkg/util.py", "type": "blob", "size": 50},
            {"path": "tests/test_app.py", "type": "blob", "size": 20},
            {"path": "README.md", "type": "blob", "size": 30},
            {"path": "venv/lib/x.py", "type": "blob", "size": 10},
        ]
    }

    def fake_request(_token, path, params=None):
        if path == "/repos/octocat/demo":
            return {"default_branch": "main"}
        if path == "/repos/octocat/demo/git/trees/main":
            return tree
        raise AssertionError(path)

    files = {
        "app.py": "def add(a, b):\n    return a + b\n",
        "pkg/util.py": "def ident(x):\n    return x\n",
        "README.md": "Add numbers and echo values.\n",
    }

    def fake_download(_token, _owner, _repo, path):
        return files[path]

    monkeypatch.setattr("agents.github_project_agent.github_request", fake_request)
    collected = collect_project_files("token", "octocat", "demo", download=fake_download)
    assert collected["python_files_tested"] == ["app.py", "pkg/util.py"]
    assert "README.md" in collected["requirement_files"]
    assert "def add(" in collected["flatten"]["source_code"]
    assert "def ident(" in collected["flatten"]["source_code"]
    assert "Add numbers" in collected["requirements_text"]
    assert collected["python_file_count"] == 2
