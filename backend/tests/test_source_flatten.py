from agents.source_flatten import (
    combine_requirement_docs,
    flatten_python_modules,
    is_python_source,
    should_skip_path,
)


def test_skips_venv_and_tests():
    assert should_skip_path("venv/lib/mod.py")
    assert should_skip_path("src/tests/test_foo.py")
    assert should_skip_path("app/test_helpers.py")
    assert is_python_source("pkg/checkout.py")
    assert not is_python_source("pkg/tests/test_checkout.py")


def test_flatten_combines_top_level_functions_and_renames_collisions():
    files = [
        ("shop/cart.py", "def add(a, b):\n    return a + b\n"),
        ("shop/math.py", "def add(a, b):\n    return a + b + 1\n"),
        ("shop/tests/test_cart.py", "def test_add():\n    assert True\n"),
    ]
    result = flatten_python_modules(files)
    assert "def add(" in result["source_code"]
    assert "def shop_math_add(" in result["source_code"] or "math_add" in result["source_code"]
    paths = {item["path"] for item in result["included"]}
    assert "shop/cart.py" in paths
    assert "shop/math.py" in paths
    assert result["function_count"] == 2


def test_combine_requirement_docs_skips_pip_lockfiles():
    docs = [
        ("requirements.txt", "fastapi==0.115.0\npytest>=8.3.0\n"),
        ("README.md", "Members receive a 10% discount.\n"),
    ]
    text = combine_requirement_docs(docs)
    assert "Members receive" in text
    assert "fastapi" not in text
