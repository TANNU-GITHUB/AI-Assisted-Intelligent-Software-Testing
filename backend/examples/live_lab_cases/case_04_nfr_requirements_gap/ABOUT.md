# Case 04 — NFR / feature gap

**Intent:** Large `source.py` is a pure **analytics/transform** library. Requirements describe OAuth, encryption at rest, audit logging, 99.99% SLA, and GDPR — **none of which exist in code**.

**Failure to detect:** Tool may invent traceability and shallow tests on `transform_*` functions while **never flagging missing security/compliance features**. Coverage can look good on implemented helpers only.

**Expected:** Requirement count high; tests exercise math/string helpers; **no test proves OAuth or GDPR**.
