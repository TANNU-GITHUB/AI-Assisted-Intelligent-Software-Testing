PROMPT_TEMPLATE = """You are a Python testing expert generating GRAY-BOX pytest cases.

Gray-box testing combines:
- requirement-visible behavior
- public API inputs
- selected internal branch and control-flow knowledge

Produce test cases that verify requirement behavior and also target meaningful branches.

Return ONLY valid JSON:
{{
  "test_cases": [
    {{
      "case_id": "gray1",
      "description": "short label",
      "requirement_id": "REQ-01",
      "function_name": "calculate_discount",
      "input": {{}},
      "expected_output": null,
      "expected_exception": null,
      "target_branch": "optional branch or condition"
    }}
  ]
}}

RULES:
- Use only the supplied public top-level function names.
- Input keys must match the function parameter names exactly.
- Requirement IDs must come from the supplied structured requirements.
- Cover positive behavior and boundary/error behavior when justified.
- Prefer a small set of strong cases over duplicate cases.

STRUCTURED REQUIREMENTS:
{structured_requirements}

PUBLIC API:
{public_api}

BRANCH MAP:
{branch_map}

SOURCE CONTEXT:
{source_context}
"""
