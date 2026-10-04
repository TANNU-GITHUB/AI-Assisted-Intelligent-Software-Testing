# Case 01 — E-commerce orders (baseline)

**Intent:** Large, mostly correct module so you can verify the full pipeline (analysis → Gemini → tests → execute → coverage).

**What to watch:** Negative/integration tests may still fail on type expectations (`TypeError` vs actual Python behavior). That is a generator weakness, not necessarily a product bug.

**Expected:** Pipeline completes; high line coverage on `source.py`; some generated tests may fail on edge types.
