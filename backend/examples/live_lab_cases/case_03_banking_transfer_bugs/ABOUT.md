# Case 03 — Banking transfers (hidden bugs)

**Intent:** Requirements forbid overdrafts and duplicate transfer IDs. Code contains deliberate bugs: allows balance to go negative in one path, weak duplicate check, incorrect daily limit accumulation.

**Failure to detect:** LLM-generated tests frequently **encode current code behavior** instead of requirements, so bugs can remain **undetected** even when tests pass.

**Expected:** Some tests may fail if LLM aligns with spec; many runs still pass buggy paths. Check `withdraw` / `transfer` / `daily_total` against requirements manually.
