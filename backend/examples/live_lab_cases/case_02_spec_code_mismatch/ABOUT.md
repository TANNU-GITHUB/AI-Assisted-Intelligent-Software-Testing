# Case 02 — Spec vs code mismatch

**Intent:** `requirements.txt` describes **15% member discount**, **8% sales tax on post-discount total**, and **free shipping over 300** — but `source.py` implements **10% discount**, **tax on pre-discount subtotal**, and **free shipping over 500**.

**Failure to detect:** Requirement analysis may still produce plausible REQ IDs; white-box tests often **mirror the code**, so tests **pass while the product violates the written spec**. Execution “green” does not mean spec compliance.

**Expected:** Pipeline may complete with passing tests; manual review should show REQ text ≠ code behavior.
