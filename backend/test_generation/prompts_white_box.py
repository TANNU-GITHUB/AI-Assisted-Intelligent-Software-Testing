PROMPT_TEMPLATE = """You are a Python testing expert generating WHITE-BOX pytest cases.

Given ONE function, its branch map, and full module context, produce test cases that
exercise each branch at least once (achieving 100% branch and statement coverage).

Return ONLY valid JSON (no markdown):
{{
  "test_cases": [
    {{
      "case_id": "wb-case-1",
      "description": "Descriptive purpose of test case (e.g. Valid member with SAVE10 coupon)",
      "input": {{ "param1": 50.0, "param2": true, "param3": "SAVE10" }},
      "expected_output": 45.0,
      "expected_exception": null
    }}
  ]
}}

Rules:
1. `input` keys must match the function parameter names exactly with REALISTIC, context-appropriate values.
2. DO NOT use 100 as a generic placeholder for everything:
   - For conditions like `param < 0`: generate negative inputs (e.g. -5.0) for the error branch, 0.0 at the boundary, and realistic positive numbers (e.g. 50.0, 150.0) for valid branches.
   - For string comparisons like `code == "SAVE10"`: generate the exact string ("SAVE10") for one branch, non-matching strings ("INVALID", "") or None for other branches.
   - For boolean parameters (e.g. `is_member`): generate both `true` and `false` across different test cases.
   - For thresholds (e.g. `val >= 100`): test values strictly below (e.g. 50.0), at the boundary (100.0), and strictly above (e.g. 150.0).
3. Use `expected_output` for normal returns (number, string, bool, list, dict, null). Calculate the exact expected return value according to the function logic.
4. Use `expected_exception` as the exception class name string (e.g. "ValueError") when the branch raises an exception. In that case, `expected_output` must be null.
5. Cover all decision branches identified in the BRANCH MAP (both True and False paths).
6. Do not import anything; tests call the function directly.

FUNCTION NAME: {function_name}
BRANCH MAP (from static analysis):
{branch_map}

FUNCTION SOURCE:
{function_source}

FULL MODULE (for context):
{module_source}
"""

STRICT_RETRY_PROMPT = """Your previous reply was not valid JSON.

Return ONLY a valid JSON object matching this structure:
{{
  "test_cases": [
    {{
      "case_id": "case1",
      "description": "...",
      "input": {{}},
      "expected_output": null,
      "expected_exception": null
    }}
  ]
}}

Ensure input parameters match {function_name} exactly and use domain-appropriate values (not generic 100).

FUNCTION NAME: {function_name}
BRANCH MAP:
{branch_map}

FUNCTION SOURCE:
{function_source}
"""

