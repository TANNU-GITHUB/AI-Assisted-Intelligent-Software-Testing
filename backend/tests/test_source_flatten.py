import ast

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


def test_flatten_preserves_imports_constants_classes_and_async_functions():
    result = flatten_python_modules(
        [
            (
                "shop/service.py",
                "import json\n"
                "from pathlib import Path\n"
                "DEFAULT_NAME = 'shop'\n"
                "class Service:\n"
                "    def name(self):\n"
                "        return DEFAULT_NAME\n"
                "async def load_name(path: Path):\n"
                "    return json.loads(path.read_text())\n"
                "def service_name():\n"
                "    return Service().name()\n",
            )
        ]
    )

    tree = ast.parse(result["source_code"])
    assert any(isinstance(node, ast.Import) and node.names[0].name == "json" for node in tree.body)
    assert any(
        isinstance(node, ast.ImportFrom) and node.module == "pathlib"
        for node in tree.body
    )
    assert any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "DEFAULT_NAME" for target in node.targets)
        for node in tree.body
    )
    assert any(isinstance(node, ast.ClassDef) and node.name == "Service" for node in tree.body)
    assert any(
        isinstance(node, ast.AsyncFunctionDef) and node.name == "load_name"
        for node in tree.body
    )
    assert result["function_count"] == 2
    assert result["included"][0]["functions"] == ["load_name", "service_name"]


def test_flatten_keeps_dependency_only_modules_with_generated_placeholder():
    result = flatten_python_modules(
        [
            ("shop/constants.py", "DEFAULT_LIMIT: int = 12\n"),
            ("shop/models.py", "class Order:\n    pass\n"),
        ]
    )

    tree = ast.parse(result["source_code"])
    assert any(
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "DEFAULT_LIMIT"
        for node in tree.body
    )
    assert any(isinstance(node, ast.ClassDef) and node.name == "Order" for node in tree.body)
    assert any(
        isinstance(node, ast.FunctionDef) and node.name == "project_placeholder"
        for node in tree.body
    )
    assert {item["path"] for item in result["included"]} == {
        "shop/constants.py",
        "shop/models.py",
        "(generated)",
    }


def test_combine_requirement_docs_skips_pip_lockfiles():
    docs = [
        ("requirements.txt", "fastapi==0.115.0\npytest>=8.3.0\n"),
        ("README.md", "Members receive a 10% discount.\n"),
    ]
    text = combine_requirement_docs(docs)
    assert "Members receive" in text
    assert "fastapi" not in text
