PROMPT_TEMPLATE = """You are a Python testing expert generating GRAY-BOX pytest cases.

Gray-box testing combines:
- requirement-visible behavior
- public API parameter names and signatures
- internal branch and control-flow knowledge

Produce test cases that verify requirement behavior and also target meaningful internal branches.

Return ONLY valid JSON:
{{
  "test_cases": [
    {{
      "case_id": "gray1",
      "description": "negative price triggers ValueError",
      "requirement_id": "REQ-01",
      "function_name": "<function_name_from_api>",
      "input": {{ "<exact_param1_name>": -10.0, "<exact_param2_name>": false }},
      "expected_output": null,
      "expected_exception": "ValueError",
      "target_branch": "price < 0"
    }},
    {{
      "case_id": "gray2",
      "description": "member discount applies 10% reduction",
      "requirement_id": "REQ-02",
      "function_name": "<function_name_from_api>",
      "input": {{ "<exact_param1_name>": 50.0, "<exact_param2_name>": true }},
      "expected_output": 45.0,
      "expected_exception": null,
      "target_branch": "is_member is True"
    }}
  ]
}}

RULES:
- Use ONLY the supplied public top-level function names from PUBLIC API.
- Input keys MUST match the exact parameter names from the PUBLIC API signatures. Never use dummy or generic names!
- Requirement IDs must come from the supplied structured requirements (REQ-01, REQ-02, ...).
- For normal execution, calculate the exact expected_output value according to the code logic.
- For exception branches, specify expected_exception (e.g. "ValueError") and set expected_output to null.
- Cover every structured requirement with at least one case.

STRUCTURED REQUIREMENTS:
{structured_requirements}

PUBLIC API:
{public_api}

BRANCH MAP:
{branch_map}

SOURCE CONTEXT:
{source_context}
"""
