## Agentic Auditor – LangChain × SurrealDB MVP

Agentic Auditor is a hackathon-grade, explainable fraud detection prototype built on:

- **Backend**: Python, FastAPI, LangChain, LangGraph
- **Database**: SurrealDB (graph + transactions)
- **Frontend**: React + Vite + TailwindCSS + React Flow

The app runs deterministic SurrealDB queries to detect fraud motifs, then uses a constrained LLM to generate grounded explanations (no invented evidence), and persists alerts/cases back into SurrealDB.

---

### Backend structure

Backend code lives in `backend/`:

- `backend/main.py` – FastAPI application entrypoint
- `backend/app/db.py` – SurrealDB async client, env-driven configuration
- `backend/app/models.py` – Pydantic models and shared investigation state
- `backend/app/queries.py` – SurrealDB fraud/graph queries
- `backend/app/tools.py` – LangChain tool wrappers around the queries
- `backend/app/graph.py` – LangGraph workflow (run_detections → score_risk → generate_explanation → persist_alert_case)
- `backend/app/explain.py` – LLM-based explanation generation, strictly grounded in evidence
- `backend/app/persist.py` – Alert/case creation + relations in SurrealDB
- `backend/app/api.py` – FastAPI routes (`/health`, `/investigate`, `/feedback`)

SurrealDB connection is configured via environment variables:

- `SURREAL_URL`
- `SURREAL_USER`
- `SURREAL_PASS`
- `SURREAL_NS`
- `SURREAL_DB`

The OpenAI LLM is configured via:

- `OPENAI_API_KEY`
- `LLM_MODEL` (defaults to `gpt-4o-mini`)

---

### Frontend structure

Frontend code lives in `frontend/`:

- `frontend/index.html` – Vite entry HTML
- `frontend/vite.config.mts` – Vite React setup
- `frontend/tailwind.config.cjs` + `frontend/postcss.config.cjs` – TailwindCSS config
- `frontend/src/main.jsx` – React root
- `frontend/src/App.jsx` – Main dashboard layout
  - **Left panel**: transaction ID input + “Run investigation”
  - **Center panel**: React Flow relationship graph
  - **Right panel**: risk score, severity, explanations, evidence, alert/case IDs, analyst feedback
- `frontend/src/GraphView.jsx` – Graph visualisation using React Flow
- `frontend/src/api.js` – Small API client for `/health`, `/investigate`, `/feedback`
- `frontend/src/index.css` – Tailwind base + dark dashboard styling

The frontend talks to the backend via:

- `VITE_API_BASE_URL` (optional, defaults to `http://localhost:8001`)

---

### Deterministic fraud detection

Three core fraud motifs are implemented as SurrealDB queries, wrapped as LangChain tools and orchestrated by LangGraph:

- **Star pattern** (`detect_star_pattern`)  
  Uses `sent_to` relation edges to find **source accounts** sending to many destinations in a recent time window.
- **Circular flow** (`detect_circular_flow`)  
  For the MVP, surfaces the known ring of accounts seeded in the dataset.
- **Flagged association** (`detect_flagged_association`)  
  Uses `linked_to_flag` edges to find accounts linked directly to confirmed fraud accounts.

The LangGraph state includes:

- `transaction_id`
- `detections`
- `risk_score`
- `severity`
- `evidence`
- `explanation_short`
- `explanation_long`
- `alert_id`
- `case_id`
- `analyst_decision`

Scoring logic (deterministic):

- Star pattern: **+30**
- Circular flow: **+20**
- Flagged association: **+25**

Severity bands:

- `high` if score ≥ 50
- `medium` if score ≥ 25
- `low` otherwise

---

### LLM explanations (grounded)

Once deterministic detections are collected, the backend calls a constrained LLM:

- `backend/app/explain.py` (`generate_explanations`) receives **only structured evidence**, `risk_score`, and `severity`.
- It must:
  - Use only the evidence provided
  - Mention pattern names and counts when relevant
  - Avoid made-up entities, probabilities, or unsupported claims
- It returns:
  - `explanation_short`: one-sentence summary
  - `explanation_long`: concise analyst-style narrative

These explanations, along with raw evidence, are returned in `/investigate` and persisted in `alert` and `case_record` records.

---

### Alert and case persistence

`backend/app/persist.py`:

- Creates an **`alert`** record with:
  - `transaction`
  - `risk_score`
  - `severity`
  - `evidence`
  - `explanation_short`
  - `explanation_long`
- Creates a **`case_record`** linked to the alert
- Creates relations:
  - `alert -> for_transaction -> transaction`
  - `alert -> in_case -> case_record`

Analyst feedback (`/feedback`) creates `analyst_feedback` records and links them to the case using `case_record -> has_feedback -> analyst_feedback`.

---

### API endpoints

Backend endpoints (served by FastAPI):

- **GET `/health`**  
  Simple healthcheck. Returns `{"status": "ok"}` if backend is alive.

- **POST `/investigate`**  
  **Body**:
  ```json
  { "transaction_id": "transaction:txn_00001" }
  ```
  **Response**:
  ```json
  {
    "state": {
      "transaction_id": "...",
      "detections": [...],
      "risk_score": 75,
      "severity": "high",
      "evidence": [...],
      "explanation_short": "...",
      "explanation_long": "...",
      "alert_id": "alert:...",
      "case_id": "case_record:...",
      "analyst_decision": null
    },
    "graph": {
      "transaction": {...},
      "source_account": "account:...",
      "destination_account": "account:...",
      "linked_flagged_accounts": [...],
      "devices": [...],
      "ips": [...]
    }
  }
  ```

- **POST `/feedback`**  
  **Body**:
  ```json
  {
    "case_id": "case_record:...",
    "decision": "confirmed_suspicious|false_positive|escalate",
    "note": "optional free text"
  }
  ```
  **Response**:
  ```json
  { "status": "ok", "feedback": { ... } }
  ```

---

### Environment variables

Copy `.env.example` to `.env` (or export values in your shell) and adjust as needed:

```bash
SURREAL_URL=http://localhost:8000
SURREAL_USER=root
SURREAL_PASS=root
SURREAL_NS=hackathon
SURREAL_DB=agentic_auditor

OPENAI_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
```

Frontend can optionally use:

```bash
VITE_API_BASE_URL=http://localhost:8001
```

> **Note**: SurrealDB commonly listens on port `8000`. The instructions below start FastAPI on port `8001` to avoid conflicts.

---

### Installing dependencies

#### Backend (Python)

From the project root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Frontend (Node)

From the project root:

```bash
cd frontend
npm install
```

---

### Running the backend

1. Ensure **SurrealDB** is running and seeded with the synthetic fraud dataset:
   - Namespace: `hackathon`
   - Database: `agentic_auditor`
   - Tables: `account`, `card`, `device`, `ip_address`, `merchant`, `transaction`, `fraud_pattern`, and relations like `sent_to`, `uses_device`, `uses_ip`, `linked_to_flag`
2. Export or configure the environment variables from `.env.example`.
3. Start the FastAPI app (on port 8001 to avoid clashing with SurrealDB):

```bash
cd backend
uvicorn main:app --reload --port 8001
```

Backend base URL: `http://localhost:8001`

You can verify it with:

```bash
curl http://localhost:8001/health
```

---

### Running the frontend

1. Ensure the backend is running on `http://localhost:8001`.
2. Optionally create `frontend/.env` with:

```bash
VITE_API_BASE_URL=http://localhost:8001
```

3. Start the Vite dev server:

```bash
cd frontend
npm run dev
```

Frontend will be available at `http://localhost:5173`.

---

### Demo flow

1. Open the dashboard at `http://localhost:5173`.
2. In the **left panel**, enter a transaction ID, e.g. a seeded one like:
   - Star pattern around `account:acct_231`
   - Circular flow ring among `account:acct_232`–`account:acct_236`
   - Flagged association accounts linked to known fraud accounts
3. Click **“Run investigation”**.
4. The app will:
   - Run deterministic SurrealDB queries for star pattern, circular flow, and flagged associations.
   - Compute a risk score and severity.
   - Call a constrained LLM to generate **short** and **long** explanations using only detected evidence.
   - Persist an **alert** and **case_record**, and return their IDs.
5. The **center panel** shows a small relationship graph:
   - Source account → destination account
   - Links to flagged accounts
   - Shared device/IP nodes
6. The **right panel** shows:
   - Risk score + severity
   - Human-readable explanations
   - Structured evidence by motif
   - Alert ID and Case ID
   - Analyst feedback buttons: **Confirm suspicious**, **False positive**, **Escalate**

---

### Where key logic lives

- **LangGraph workflow**: `backend/app/graph.py`  
  (`workflow` object, nodes: `run_detections`, `score_risk`, `generate_explanation`, `persist_alert_case`)
- **SurrealDB queries**: `backend/app/queries.py`

These files are the main entry points for hacking on the fraud logic and orchestration during the hackathon.

#   H a c k a t h o n  
 