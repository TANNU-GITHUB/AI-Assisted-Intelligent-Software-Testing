# Pipeline demo (compact)

Use in **Live Lab**: paste `source.py` and `requirements.txt` (filename `source.py`).

| File | Lines |
|------|-------|
| `source.py` | ~55 |
| `requirements.txt` | 7 bullets (trim to 6 in UI if you prefer) |

**Designed for:** code analysis (7 functions, multiple branches), requirement IDs, white-box / integration / negative tests, pytest execution, and **coverage on `source.py`**.

**Quick sanity (optional):**

```bash
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_pipeline_integration.py -q
```
