PROMPT_TEMPLATE = """You are a software test analyst.

Read the functional requirements below and extract ALL discrete, numbered, TESTABLE scenarios.
Each distinct sentence, bullet point, or rule MUST become its own requirement entry (REQ-01, REQ-02, REQ-03, ...).

Return ONLY valid JSON that matches this schema (no markdown, no commentary):
{{
  "requirements": [
    {{
      "requirement_id": "REQ-01",
      "condition": "Price is negative (< 0)",
      "expected_result": "System raises ValueError",
      "source_excerpt": "Reject negative prices with ValueError."
    }},
    {{
      "requirement_id": "REQ-02",
      "condition": "Customer is a member (is_member is True)",
      "expected_result": "Apply 10% discount to price",
      "source_excerpt": "Members get 10% off."
    }},
    {{
      "requirement_id": "REQ-03",
      "condition": "Customer is a non-member (is_member is False)",
      "expected_result": "Charge $5 delivery fee",
      "source_excerpt": "Non-members pay a $5 delivery fee."
    }}
  ]
}}

Rules:
1. Extract EVERY distinct requirement into a separate object (REQ-01, REQ-02, REQ-03, ... in order).
2. DO NOT stop after just one requirement. If there are 3 rules or lines in the input, you MUST output at least 3 requirement objects.
3. "condition" must state the specific IF condition clearly (e.g. "Price is negative", "is_member is True", "is_member is False").
4. "expected_result" must state the specific THEN outcome (e.g. "Raises ValueError", "Apply 10% discount", "Add $5 delivery fee").
5. "source_excerpt" must be the exact or near-verbatim sentence from the requirements.

FUNCTIONAL REQUIREMENTS:
{requirements_text}
"""

STRICT_RETRY_PROMPT = """Your previous reply was not valid JSON.

Return ONLY a JSON object with a "requirements" array containing ALL requirements extracted from the text.
No markdown fences. No extra keys. No prose.

Each element must have:
- requirement_id (string: REQ-01, REQ-02, etc.)
- condition (string)
- expected_result (string)
- source_excerpt (string)

FUNCTIONAL REQUIREMENTS:
{requirements_text}
"""
