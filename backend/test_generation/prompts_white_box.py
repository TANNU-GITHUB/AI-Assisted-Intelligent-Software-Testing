PROMPT_TEMPLATE = """You are a Python testing expert generating WHITE-BOX pytest cases.

Given ONE function, its branch map, and full module context, produce test cases that
exercise each branch at least once (branch coverage goal).

Return ONLY valid JSON (no markdown):
{{
  "test_cases": [
    {{
      "case_id": "case1",
      "description": "short label",
      "input": {{ "param_name": value }},
      "expected_output": null,
      "expected_exception": null
    }}
  ]
}}

Rules:
- `input` keys must match the function parameter names exactly.
- Use `expected_output` for normal returns (number, string, bool, list, dict, null).
- Use `expected_exception` as an exception class name string (e.g. "ValueError") when the branch should raise.
- Do not import anything; tests will call the function directly from the uploaded module.
- Prefer the smallest number of cases that still cover every branch listed.
- Do not invent parameters that are not in the function signature.

FUNCTION NAME: {function_name}
BRANCH MAP (from static analysis):
{branch_map}

FUNCTION SOURCE:
{function_source}

FULL MODULE (for context):
{module_source}
"""

STRICT_RETRY_PROMPT = """Your previous reply was not valid JSON.

Return ONLY:
{{ "test_cases": [ {{ "case_id": "...", "description": "...", "input": {{}}, "expected_output": ..., "expected_exception": null }} ] }}

FUNCTION NAME: {function_name}
BRANCH MAP:
{branch_map}

FUNCTION SOURCE:
{function_source}
"""
