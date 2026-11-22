PROMPT_TEMPLATE = """You are a QA engineer generating BLACK-BOX pytest cases.

Rules:
- Derive inputs and expected outcomes from the requirements and public API signatures.
- "input" keys must match the exact parameter names from the Public API for that function (never use placeholder names like "param_name").
- When a requirement specifies concrete test values (for example: "x is 500 and y is 200"), use those exact values in "input".
- Each test case must map to exactly one requirement_id from Structured requirements.
- Generate at least one test case for each structured requirement.
- For error/exception scenarios (such as ValueError or invalid argument), use "expected_exception": "ValueError" instead of expected_output.
- Do NOT use internal implementation branches or logic not stated in requirements.

Natural language requirements:
<<<REQUIREMENTS_TEXT>>>

Structured requirements (JSON):
<<<STRUCTURED_REQUIREMENTS>>>

Public API (signatures only, no implementation):
<<<PUBLIC_API>>>

Return ONLY a JSON object (no markdown) with this shape:
{
  "test_cases": [
    {
      "requirement_id": "REQ-01",
      "function_name": "function_from_api",
      "description": "what behavior is verified",
      "input": {"param_name": 100},
      "expected_output": null
    }
  ]
}

For error scenarios use "expected_exception": "ValueError" instead of expected_output.
Include at least one test case per structured requirement when feasible.
"""

STRICT_RETRY_PROMPT = """Your previous response was not valid JSON matching the black-box schema.
Return ONLY a JSON object with key "test_cases" (array). Each item needs requirement_id,
function_name, description, input, and either expected_output or expected_exception.
Do not include markdown fences or commentary.
"""
