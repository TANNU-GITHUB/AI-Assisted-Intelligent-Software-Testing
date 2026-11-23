"""Turn many Python files into one module the existing pipeline can test."""

from __future__ import annotations

import ast
import re
from typing import Any

SKIP_DIR_PARTS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "site-packages",
    "venv",
}

_TEST_DIR_PARTS = {"test", "tests", "testing"}
_PIP_LINE = re.compile(r"^[A-Za-z0-9_.\-]+(\[[^\]]+\])?\s*([=<>!~]=|[=~><]).*")


def should_skip_path(path: str) -> bool:
    parts = [p.lower() for p in path.replace("\\", "/").split("/") if p]
    if any(part in SKIP_DIR_PARTS for part in parts):
        return True
    if any(part in _TEST_DIR_PARTS for part in parts[:-1]):
        return True
    name = parts[-1] if parts else ""
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    if name in {"conftest.py", "setup.py", "setup.cfg"}:
        return True
    return False


def is_python_source(path: str) -> bool:
    return path.replace("\\", "/").lower().endswith(".py") and not should_skip_path(path)


_SPEC_NAMES = {
    # plain text / markdown specs
    "readme.md", "readme.rst", "readme.txt",
    "spec.md", "specs.md", "requirements.md",
    "spec.txt", "specs.txt", "requirement.txt",
    # OpenAPI / Swagger / AsyncAPI spec files (YAML or JSON)
    "openapi.yaml", "openapi.yml", "openapi.json",
    "swagger.yaml", "swagger.yml", "swagger.json",
    "asyncapi.yaml", "asyncapi.yml", "asyncapi.json",
    # common spec naming conventions
    "api-spec.yaml", "api-spec.yml", "api-spec.json",
    "api_spec.yaml", "api_spec.yml", "api_spec.json",
    "spec.yaml", "spec.yml", "spec.json",
    "specs.yaml", "specs.yml", "specs.json",
}

_SPEC_STEM_KEYWORDS = {
    "spec", "specs", "specification", "specifications",
    "requirements", "requirement", "openapi", "swagger", "asyncapi",
}


def _has_spec_stem(name: str) -> bool:
    """Return True when the filename stem strongly implies a spec file."""
    stem = name.rsplit(".", 1)[0].lower().replace("-", "_").replace(" ", "_")
    return stem in _SPEC_STEM_KEYWORDS or any(kw in stem for kw in ("_spec", "spec_", "_req", "req_"))


def is_requirement_doc(path: str, text: str = "") -> bool:
    rel = path.replace("\\", "/").lower()
    name = rel.rsplit("/", 1)[-1]
    if should_skip_path(path):
        return False
    # Exact well-known names
    if name in _SPEC_NAMES:
        return True
    # docs/ folder: any .md/.rst/.txt/.yaml/.yml/.json is a candidate
    if "docs/" in rel and name.endswith((".md", ".rst", ".txt", ".yaml", ".yml", ".json")):
        return True
    # spec/ or specs/ folder: everything
    parts = rel.rsplit("/", 1)[0].split("/") if "/" in rel else []
    if any(p in {"spec", "specs", "specification", "specifications", "api", "api-docs"} for p in parts):
        return True
    # Filename stem looks like a spec
    if _has_spec_stem(name) and name.endswith((".md", ".txt", ".rst", ".yaml", ".yml", ".json")):
        return True
    # requirements.txt that is NOT a pip lockfile
    if name == "requirements.txt":
        return not _looks_like_pip_lock(text)
    return False


def _looks_like_pip_lock(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not lines:
        return True
    pins = sum(1 for line in lines if _PIP_LINE.match(line) or line.startswith("-r "))
    return pins / len(lines) >= 0.5


def _unique_name(name: str, used: set[str], path: str) -> str:
    if name not in used:
        return name
    prefix = re.sub(r"[^a-zA-Z0-9]+", "_", path.replace(".py", "")).strip("_") or "mod"
    if prefix[0].isdigit():
        prefix = f"m_{prefix}"
    candidate = f"{prefix}_{name}"[:72]
    if candidate not in used:
        return candidate
    index = 2
    while f"{candidate}_{index}" in used:
        index += 1
    return f"{candidate}_{index}"


def fit_python_source(source_code: str, max_chars: int) -> str:
    """Keep as much source as possible without cutting a statement in half."""
    if max_chars <= 0 or len(source_code) <= max_chars:
        return source_code

    try:
        tree = ast.parse(source_code)
    except (SyntaxError, RecursionError):
        text = source_code[:max_chars]
        while text:
            try:
                ast.parse(text)
                return text.rstrip() + "\n# ... (source trimmed to a parseable prefix) ...\n"
            except (SyntaxError, RecursionError):
                cut = text.rfind("\n")
                if cut <= 0:
                    break
                text = text[:cut]
        return source_code[:max_chars]

    pieces: list[str] = []
    size = 0
    for node in tree.body:
        try:
            chunk = ast.unparse(node).strip() + "\n\n"
        except Exception:
            continue
        if size + len(chunk) > max_chars:
            if not pieces:
                pieces.append(chunk[: max(0, max_chars - 80)])
            break
        pieces.append(chunk)
        size += len(chunk)
    fitted = "".join(pieces).rstrip() + "\n"
    if len(source_code) > len(fitted):
        fitted += "# ... (remaining source omitted so the file stays parseable) ...\n"
    return fitted


def flatten_python_modules(
    files: list[tuple[str, str]],
    *,
    max_chars: int | None = None,
) -> dict[str, Any]:
    """Return combined source plus inventory. files: (path, content)."""
    used: set[str] = set()
    chunks: list[str] = [
        '"""Combined project source generated by the GitHub project agent."""',
        "",
    ]
    included: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    function_count = 0
    budget = max_chars if max_chars and max_chars > 0 else None

    for path, text in files:
        if not is_python_source(path):
            skipped.append({"path": path, "reason": "not a testable Python module"})
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            skipped.append({"path": path, "reason": f"syntax error: {exc.msg}"})
            continue

        functions: list[str] = []
        has_supported_parts = False
        file_chunks = [f"# === {path} ==="]
        for node in tree.body:
            if isinstance(
                node,
                (
                    ast.Import,
                    ast.ImportFrom,
                    ast.Assign,
                    ast.AnnAssign,
                    ast.ClassDef,
                ),
            ):
                has_supported_parts = True
                try:
                    file_chunks.append(ast.unparse(node))
                except Exception:
                    skipped.append(
                        {"path": path, "reason": "could not serialize top-level dependency"}
                    )
                continue
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("test_"):
                continue
            has_supported_parts = True
            original = node.name
            node.name = _unique_name(original, used, path)
            used.add(node.name)
            functions.append(node.name)
            function_count += 1
            try:
                file_chunks.append(ast.unparse(node))
            except Exception:
                skipped.append({"path": path, "reason": f"could not serialize {original}"})
                used.discard(node.name)
                function_count -= 1
                functions.pop()
        if has_supported_parts:
            candidate = "\n".join(chunks + file_chunks + [""])
            if budget is not None and len(candidate) > budget and included:
                for name in functions:
                    used.discard(name)
                function_count -= len(functions)
                skipped.append(
                    {
                        "path": path,
                        "reason": "omitted so the combined project stays within the analysis budget",
                    }
                )
                continue
            chunks.extend(file_chunks)
            chunks.append("")
            included.append({"path": path, "functions": functions})
        else:
            skipped.append(
                {"path": path, "reason": "no supported top-level definitions or dependencies"}
            )

    source = "\n".join(chunks).strip() + "\n"
    if function_count == 0:
        chunks.extend(
            [
                "def project_placeholder() -> str:\n"
                '    """No top-level functions were found in the repository."""\n'
                '    return "empty"\n'
            ]
        )
        source = "\n".join(chunks).strip() + "\n"
        included.append({"path": "(generated)", "functions": ["project_placeholder"]})
        function_count = 1

    return {
        "source_code": source,
        "function_count": function_count,
        "included": included,
        "skipped": skipped,
    }


def _spec_priority(path: str) -> int:
    """Lower number = higher priority (spec/api files first, README last)."""
    name = path.replace("\\", "/").lower().rsplit("/", 1)[-1]
    if name in {
        "openapi.yaml", "openapi.yml", "openapi.json",
        "swagger.yaml", "swagger.yml", "swagger.json",
        "asyncapi.yaml", "asyncapi.yml", "asyncapi.json",
        "spec.yaml", "spec.yml", "spec.json",
        "api-spec.yaml", "api-spec.yml", "api-spec.json",
    }:
        return 0
    if name in {"spec.txt", "specs.txt", "spec.md", "specs.md", "requirement.txt", "requirements.txt"}:
        return 1
    if "docs/" in path.lower():
        return 2
    if name in {"readme.md", "readme.rst", "readme.txt"}:
        return 10
    return 5


def _yaml_to_plain_text(text: str, path: str) -> str:
    """Convert OpenAPI/Swagger/YAML spec to a readable requirements paragraph."""
    try:
        import json as _json
        import re as _re
        name = path.lower().rsplit("/", 1)[-1]
        # Try JSON parse first
        if name.endswith(".json"):
            data = _json.loads(text)
        else:
            # Simple YAML summary: extract summary/description fields
            descriptions: list[str] = []
            for line in text.splitlines():
                m = _re.match(r'\s*(?:summary|description|title):\s*(.+)', line)
                if m:
                    val = m.group(1).strip().strip('"\'')
                    if val and len(val) > 4:
                        descriptions.append(val)
            if descriptions:
                return "\n".join(descriptions[:200])
            return text  # return as-is if we can't parse it nicely
    except Exception:
        return text
    return text


def combine_requirement_docs(files: list[tuple[str, str]], *, max_chars: int = 20_000) -> str:
    parts: list[str] = []
    # Sort by priority: spec files first, READMEs last
    sorted_files = sorted(files, key=lambda item: _spec_priority(item[0]))
    for path, text in sorted_files:
        body = (text or "").strip()
        if not body or not is_requirement_doc(path, body):
            continue
        name = path.lower().rsplit("/", 1)[-1]
        # Convert YAML/JSON specs to plain text summary
        if name.endswith((".yaml", ".yml", ".json")):
            body = _yaml_to_plain_text(body, path)
        parts.append(f"# From {path}\n{body}")
    combined = "\n\n".join(parts).strip()
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n\n# …truncated…"
    return combined


def fallback_requirements_from_functions(included: list[dict[str, Any]]) -> str:
    lines = [
        "The combined GitHub project must expose the following public behaviors:",
    ]
    for item in included:
        path = item.get("path")
        for name in item.get("functions") or []:
            lines.append(f"- Function {name} from {path} must run without crashing on typical inputs.")
    if len(lines) == 1:
        lines.append("- The project must provide at least one callable entry point.")
    return "\n".join(lines) + "\n"
