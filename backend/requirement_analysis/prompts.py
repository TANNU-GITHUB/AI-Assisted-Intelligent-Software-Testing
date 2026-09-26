PROMPT_TEMPLATE = """You are a software test analyst.

Read the functional requirements below and extract discrete, numbered, TESTABLE scenarios.

Return ONLY valid JSON that matches this schema (no markdown, no commentary):
{{
  "requirements": [
    {{
      "requirement_id": "REQ-01",
      "condition": "plain-language IF condition that can be checked",
      "expected_result": "plain-language THEN expected outcome",
      "source_excerpt": "short quote from the original text this came from"
    }}
  ]
}}

Rules:
- requirement_id must be REQ-01, REQ-02, ... in order.
- Each item must be independently testable.
- Split compound sentences into separate scenarios.
- Do not invent features that are not in the text.
- If a requirement is vague, still extract the testable core and keep expected_result specific.

FUNCTIONAL REQUIREMENTS:
{requirements_text}
"""

STRICT_RETRY_PROMPT = """Your previous reply was not valid JSON.

Return ONLY a JSON object with a "requirements" array.
No markdown fences. No extra keys. No prose.

Each element must have:
- requirement_id (string like REQ-01)
- condition (string)
- expected_result (string)
- source_excerpt (string)

FUNCTIONAL REQUIREMENTS:
{requirements_text}
"""
