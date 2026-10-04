# Case 05 — Payroll rounding and boundaries

**Intent:** Requirements specify **banker's rounding**, overtime after **40** hours at **1.5×**, and cap on deductions. Code uses **binary float rounding**, overtime after **41** hours, and a deduction bug for exact minimum wage employees.

**Failure to detect:** Branch-heavy code gets many white-box tests; subtle numeric and off-by-one bugs often **miss** unless tests use exact decimal expectations from requirements.

**Expected:** Pipeline completes; inspect failed/passed tests around 40 vs 41 hours and `$0.005` rounding cases.
