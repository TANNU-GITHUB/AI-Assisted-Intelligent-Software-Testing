"""Task 3 — Source code analysis via Python's ast module (no execution)."""

from __future__ import annotations

import ast
from typing import Any

from input_handler.handler import load_session, save_session, session_dir


class CodeAnalysisError(ValueError):
    """Raised when source code cannot be parsed."""


def _annotation_to_str(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _expr_to_str(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _collect_params(args: ast.arguments) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []

    def add(arg: ast.arg, default: ast.AST | None = None, kind: str = "positional") -> None:
        params.append(
            {
                "name": arg.arg,
                "annotation": _annotation_to_str(arg.annotation),
                "default": _expr_to_str(default),
                "kind": kind,
            }
        )

    posonly = list(args.posonlyargs)
    regular = list(args.args)
    defaults = list(args.defaults)
    positional = posonly + regular
    default_offset = len(positional) - len(defaults)
    for index, arg in enumerate(positional):
        default = defaults[index - default_offset] if index >= default_offset else None
        kind = "positional_only" if index < len(posonly) else "positional"
        add(arg, default, kind)

    if args.vararg:
        add(args.vararg, None, "vararg")

    kw_defaults = list(args.kw_defaults)
    for arg, default in zip(args.kwonlyargs, kw_defaults):
        add(arg, default, "keyword_only")

    if args.kwarg:
        add(args.kwarg, None, "kwarg")

    return params


def _branch_from_node(node: ast.AST) -> dict[str, Any] | None:
    if isinstance(node, ast.If):
        return {
            "type": "if",
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "condition": _expr_to_str(node.test),
            "has_else": bool(node.orelse),
        }
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return {
            "type": "for",
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "condition": f"{_expr_to_str(node.target)} in {_expr_to_str(node.iter)}",
            "has_else": bool(node.orelse),
        }
    if isinstance(node, ast.While):
        return {
            "type": "while",
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "condition": _expr_to_str(node.test),
            "has_else": bool(node.orelse),
        }
    if isinstance(node, ast.ExceptHandler):
        name = _expr_to_str(node.type) if node.type else "Exception"
        return {
            "type": "except",
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "condition": name,
            "has_else": False,
        }
    if isinstance(node, ast.Assert):
        return {
            "type": "assert",
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "condition": _expr_to_str(node.test),
            "has_else": False,
        }
    if isinstance(node, ast.match_case):
        return {
            "type": "match_case",
            "lineno": getattr(node.pattern, "lineno", 0),
            "end_lineno": getattr(node, "end_lineno", getattr(node.pattern, "lineno", 0)),
            "condition": _expr_to_str(node.pattern),
            "has_else": False,
        }
    return None


_NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _iter_own_nodes(fn_node: ast.AST):
    """Yield AST nodes in a function body, skipping nested functions/classes."""

    def walk(node: ast.AST):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _NESTED_SCOPES):
                continue
            yield child
            yield from walk(child)

    yield from walk(fn_node)


def _decision_points(fn_node: ast.AST) -> tuple[list[dict[str, Any]], int]:
    """Count McCabe-style decision points inside one function (not nested defs)."""
    branches: list[dict[str, Any]] = []
    extra_boolean = 0

    for child in _iter_own_nodes(fn_node):
        branch = _branch_from_node(child)
        if branch:
            branches.append(branch)

        if isinstance(child, ast.BoolOp) and len(child.values) > 1:
            extra_boolean += len(child.values) - 1

        if isinstance(child, ast.comprehension):
            extra_boolean += len(child.ifs)

    decision_count = len(branches) + extra_boolean
    return branches, decision_count


def _function_record(node: ast.FunctionDef | ast.AsyncFunctionDef, parent: str | None) -> dict[str, Any]:
    name = node.name
    qualified = f"{parent}.{name}" if parent else name
    branches, decision_count = _decision_points(node)
    return {
        "name": name,
        "qualified_name": qualified,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "params": _collect_params(node.args),
        "return_type": _annotation_to_str(node.returns),
        "lineno": node.lineno,
        "end_lineno": getattr(node, "end_lineno", node.lineno),
        "decorators": [_expr_to_str(d) for d in node.decorator_list],
        "branches": branches,
        "branch_count": len(branches),
        "cyclomatic_complexity": decision_count + 1,
        "docstring": ast.get_docstring(node),
    }


def analyze_source(source_code: str) -> dict[str, Any]:
    """Parse source into a structured function/branch map for white-box generation."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        raise CodeAnalysisError(
            f"Python syntax error on line {exc.lineno}: {exc.msg}"
        ) from exc

    functions: list[dict[str, Any]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            parent = ".".join(self.class_stack) if self.class_stack else None
            functions.append(_function_record(node, parent))
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            parent = ".".join(self.class_stack) if self.class_stack else None
            functions.append(_function_record(node, parent))
            self.generic_visit(node)

    Visitor().visit(tree)

    return {
        "module_docstring": ast.get_docstring(tree),
        "function_count": len(functions),
        "functions": functions,
    }


def analyze_session(session_id: str) -> dict[str, Any]:
    payload = load_session(session_id)
    source_path = session_dir(session_id) / "source.py"
    source_code = source_path.read_text(encoding="utf-8")
    analysis = analyze_source(source_code)
    payload["code_analysis"] = analysis
    payload["status"] = "code_analyzed"
    return save_session(payload)
