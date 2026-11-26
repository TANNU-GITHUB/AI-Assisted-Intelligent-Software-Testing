PROMPT_TEMPLATE = """You are a QA testing expert generating comprehensive BLACK-BOX pytest cases.

Rules:
- Derive inputs and expected outcomes directly from the natural language and structured requirements.
- CRITICAL: "input" dictionary keys MUST MATCH THE EXACT PARAMETER NAMES listed in <<<PUBLIC_API>>>.
  * For example, if a function signature is `calculate_total(price, is_member)`, your input MUST be `{"price": 50.0, "is_member": true}`.
  * NEVER use placeholder keys like "param_a", "param_b", "param_1", or "arg1". Using incorrect parameter names causes Python TypeError!
- TEST VALUE QUALITY & REALISM:
  * Do NOT use 100 for all parameters. Choose diverse, realistic values that match the parameter's semantic meaning and type.
  * For string parameters (e.g. coupon_code, email, username, category): use realistic strings like "SAVE10", "PROMO20", "user@test.com", "Alice", or null/None if optional. Never pass numbers to string fields.
  * For boolean flags (e.g. is_member, active): test both True and False.
  * For age/threshold conditions (e.g. age > 18): apply Boundary Value Analysis (BVA) and Equivalence Partitioning (18, 17, 19, 40).
  * For monetary amounts (e.g. subtotal, price, balance): test valid positive values (e.g. 50.0, 120.0), zero (0.0), and boundary/negative error values (e.g. -5.0).
- Map EVERY requirement from Structured requirements (REQ-01, REQ-02, REQ-03, ...) to at least one test case!
- For error scenarios (e.g. negative input, boundary violation), specify "expected_exception": "ValueError" (or the appropriate Exception class) instead of expected_output.

Natural language requirements:
<<<REQUIREMENTS_TEXT>>>

Structured requirements (JSON):
<<<STRUCTURED_REQUIREMENTS>>>

Public API (signatures only, no implementation):
<<<PUBLIC_API>>>

Return ONLY a JSON object (no markdown, no commentary) with this shape:
{{
  "test_cases": [
    {{
      "requirement_id": "REQ-01",
      "function_name": "<function_name_from_api>",
      "description": "verify negative price triggers ValueError",
      "input": {{ "<exact_param1_name>": -10.0, "<exact_param2_name>": false }},
      "expected_output": null,
      "expected_exception": "ValueError"
    }},
    {{
      "requirement_id": "REQ-02",
      "function_name": "<function_name_from_api>",
      "description": "verify member discount applies to valid price",
      "input": {{ "<exact_param1_name>": 50.0, "<exact_param2_name>": true }},
      "expected_output": 45.0,
      "expected_exception": null
    }}
  ]
}}
"""

STRICT_RETRY_PROMPT = """Your previous response was not valid JSON matching the black-box schema.
Return ONLY a JSON object with key "test_cases" (array).
Each item needs requirement_id, function_name, description, input (with exact parameter names from the Public API), and either expected_output or expected_exception.
Do not include markdown fences or commentary.
"""
