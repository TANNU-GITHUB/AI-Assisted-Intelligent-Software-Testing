# AI-Assisted-Intelligent-Software-Testing

An AI-assisted software testing system that automatically generates, executes, and evaluates software tests using functional requirements and source-code information.

## 📌 Overview

The system takes:

* Source code of a software project
* Functional requirements written in natural language

It analyzes both the requirements and source code to generate relevant test cases.

Unlike simple one-time AI test generation, the proposed system uses execution results, code coverage, and mutation feedback to identify testing gaps and generate additional targeted tests.

## 🎯 Objectives

The main objectives of the project are to:

* Analyze source code to identify functions, conditions, branches, and execution paths.
* Understand functional requirements written in natural language.
* Map functional requirements to relevant parts of the source code.
* Generate black-box and white-box test cases.
* Generate negative and boundary test cases where applicable.
* Automatically execute generated tests.
* Measure code and requirement coverage.
* Identify uncovered or weakly tested areas.
* Regenerate targeted tests using coverage feedback.
* Evaluate test quality using mutation testing.
* Generate a requirement-to-test traceability report.

## 🔄 Proposed Workflow

```text
Source Code + Functional Requirements
                ↓
        Requirement Analysis
                ↓
          Code Analysis
                ↓
    Requirement-Code Mapping
                ↓
       Initial Test Generation
                ↓
        Test Validation
                ↓
        Test Execution
                ↓
     Coverage Measurement
                ↓
       Testing Gap Detection
                ↓
     Targeted Test Generation
                ↓
        Mutation Testing
                ↓
          Final Report
```

## 🧪 Testing Techniques

The system will initially focus on:

* Black-box testing
* White-box testing
* Unit testing
* Negative testing
* Boundary value testing
* Equivalence partitioning
* Decision-based testing
* Regression testing
* Coverage-guided test generation
* Mutation testing

## 💡 Key Contribution

The project focuses on making AI-generated tests requirement-aware and feedback-guided.

Instead of generating tests only once, the system uses:

```text
Requirements
     ↓
Generated Tests
     ↓
Execution
     ↓
Coverage
     ↓
Mutation Feedback
     ↓
Testing Gaps
     ↓
Targeted New Tests
```

This allows the generated test suite to be iteratively improved.

## 🛠️ Planned Technology Stack

### Backend

* Python
* FastAPI

### AI

* Large Language Model API
* Structured JSON-based test generation

### Code Analysis

* Python AST
* Coverage.py

### Testing

* pytest
* mutmut

### Frontend

* React.js

### Database

* SQLite


## 📊 Evaluation Metrics

The system will be evaluated using:

* Line coverage
* Branch coverage
* Requirement coverage
* Mutation score
* Number of valid generated tests
* Number of defects detected
* Test generation efficiency
* Redundant test cases

### Where to paste the Gemini API key

Open **`backend/.env`** and set:

```env
GEMINI_API_KEY=paste_your_key_here
```

Create a key at [Google AI Studio](https://aistudio.google.com/apikey). Do not commit `.env`.

### Run locally (both must be running)

Terminal 1 — backend:

```bash
cd backend
..\venv\Scripts\activate
uvicorn app:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000/live-lab](http://localhost:3000/live-lab). The Next.js app proxies `/api/*` to `http://127.0.0.1:8000`.

Click **Run Analysis** on Live Lab (Tasks 2–5, execution, coverage), then **View Full Report** on the Dashboard.

### Jev (semantic UI testing)

The frontend includes optional [Jev](https://www.shipwithjev.com/builds/playwright-jev) + Playwright checks under `frontend/e2e/`.

1. Copy `frontend/.env.example` → `frontend/.env` and set `OPENROUTER_API_KEY` or `TYPESAFE_API_KEY`.
2. Install browsers once: `cd frontend && npx playwright install chromium`
3. With backend running, set `E2E_BACKEND_URL=http://127.0.0.1:8000`.
4. Run:
   - `npm run test:e2e:smoke` — basic UI/API smoke (no Jev key required for UI tests)
   - `npm run test:e2e:jev` — semantic Live Lab checks (requires Jev key + `playwright-jev`)

```bash
cd backend
..\venv\Scripts\python.exe -m pytest -q
```

## 📚 Project Status



The project is being developed as a final-year B.Tech major project by a team of three students.

## 📄 Documentation

Detailed project documentation, architecture diagrams, experiments, and reports will be added as development progresses.

## ⚠️ Current Scope

The initial prototype will focus on Python applications to keep the system achievable within the project timeline.

Support for additional programming languages may be considered as future work.

