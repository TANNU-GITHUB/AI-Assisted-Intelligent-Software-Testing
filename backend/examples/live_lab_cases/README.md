# Live Lab stress cases

Five self-contained scenarios for **Live Lab** (`/live-lab`). Each folder has:

| File | Use in Live Lab |
|------|------------------|
| `source.py` | Paste into **Source code** (filename e.g. `source.py`) |
| `requirements.txt` | Paste into **Requirements** |
| `ABOUT.md` | What the case is meant to expose (do not paste) |

## How to run

1. Start backend with `backend/run_dev.ps1` (avoids reload breaking coverage).
2. Open frontend **Live Lab**.
3. Pick a case folder below, copy both files into the form, run the pipeline.
4. Compare results to **ABOUT.md** — these cases target places the tool **may miss** defects or mis-trace requirements.

## Cases

| Folder | Focus |
|--------|--------|
| `case_01_ecommerce_orders` | Large correct baseline; reference for coverage and pass/fail mix |
| `case_02_spec_code_mismatch` | Requirements describe different tax/shipping/discount rules than code |
| `case_03_banking_transfer_bugs` | Intentional logic bugs; tests may assert wrong behavior if LLM reads code not spec |
| `case_04_nfr_requirements_gap` | Heavy non-functional requirements with no implementation in source |
| `case_05_payroll_rounding_edges` | Float rounding, overtime off-by-one, boundary payroll rules |

## Optional API

Only `examples/sample_*.py` is loaded by `GET /api/examples`. These cases are file-based for manual copy/paste.
