PROMPT_TEMPLATE = """You are a QA engineer generating BLACK-BOX pytest cases.

Rules:
- Derive inputs and expected outcomes ONLY from the requirements and public API signatures.
- Do NOT use or infer internal branches, implementation details, or source code logic.
- Each test case must map to exactly one requirement_id.
- Use only the listed public functions and their parameter names.

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
      "input": {"param": value},
      "expected_output": <value>
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
