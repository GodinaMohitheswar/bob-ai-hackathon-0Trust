# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**

## Prerequisites

Before you begin, ensure you have the following installed:

- [ ] **Python 3.11+** (tested on Python 3.13) — [python.org/downloads](https://www.python.org/downloads/)
- [ ] **Node.js 18+** and **npm** — [nodejs.org](https://nodejs.org/)
- [ ] **Git**

> No IBM Cloud account, no database, and no external API keys are required to run this project.
> All data is pre-loaded as CSV files in `src/backend/data/raw/`.

---

## Environment Variables

This project does **not** require any environment variables to run locally.
The backend reads only local CSV files and has no external service dependencies.

The `.env.example` file at `src/.env.example` documents optional variables
(watsonx.ai, database, Slack) for future production extensions — none of them
are consumed by the current codebase.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/bob-ai-hackathon-0Trust.git
cd bob-ai-hackathon-0Trust
```

---

### 2. Backend — Python setup

```bash
cd src/backend

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS / Linux:
source .venv/bin/activate

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install fastapi uvicorn pandas networkx
```

> **Exact packages required:**
>
> | Package | Purpose |
> |---|---|
> | `fastapi` | REST API framework |
> | `uvicorn` | ASGI server to run FastAPI |
> | `pandas` | CSV ingestion and data processing |
> | `networkx` | Fraud relationship graph construction and pattern detection |

---

### 3. Frontend — Node setup

Open a **new terminal** and run:

```bash
cd src/frontend

# Install all frontend dependencies
npm install
```

> This installs React 19, ReactFlow 11, and Vite 8 as declared in `package.json`.

---

## Running the Application

Both the backend and frontend must run **simultaneously in two separate terminals**.

### Terminal 1 — Start the backend

```bash
cd src/backend

# Activate your virtual environment first (if not already active)
# macOS / Linux:
source .venv/bin/activate
# Windows:
.\.venv\Scripts\Activate.ps1

# Start the API server
python main.py
```

The backend will be available at: **`http://127.0.0.1:8000`**

You can verify it is running by visiting `http://127.0.0.1:8000/health` — you should see:

```json
{ "status": "healthy", "cases_loaded": 100 }
```

The interactive API docs are available at: **`http://127.0.0.1:8000/docs`**

---

### Terminal 2 — Start the frontend

```bash
cd src/frontend
npm run dev
```

The frontend will be available at: **`http://localhost:5173`**

Open this URL in your browser. The investigation dashboard loads automatically with **CASE008** selected as the default case.

---

## Verifying It Works

| Check | Expected result |
|---|---|
| `http://127.0.0.1:8000/health` | `{ "status": "healthy", "cases_loaded": 100 }` |
| `http://127.0.0.1:8000/cases` | JSON list of 100 cases (CASE001–CASE100) |
| `http://127.0.0.1:8000/cases/CASE008/network` | JSON with nodes and edges for the CASE008 fraud network |
| `http://127.0.0.1:8000/cases/CASE008/brief-data` | JSON with score, priority, hierarchy, and evidence for CASE008 |
| `http://localhost:5173` | Investigation dashboard renders with the CASE008 fraud network graph |
| Click **🗺 Geo Map** button | Geographic analytics dashboard renders with the India bubble map |

---

## Exploring the Data

All mock data lives in `src/backend/data/raw/`:

| File | Description |
|---|---|
| `cases.csv` | 100 cases (CASE001–CASE100), 87 fraud + 13 legitimate |
| `identities.csv` | Named identities with role (kingpin / mule / victim), KYC status, prior fraud flag |
| `devices.csv` | Devices linked to identities, with telecom circle and risk flags |
| `transactions.csv` | UPI/NEFT/IMPS transactions with sender, receiver, amount, channel |
| `calls.csv` | Call/SMS logs with caller, receiver, duration, cell location, spoof flag |

To quickly print a data summary from the command line:

```bash
# From src/backend/ with the venv active
python data_loader.py
```

To print the fraud network graph for a specific case:

```bash
python fraud_graph.py        # prints CASE004 graph summary by default
```

To print the full pattern analysis and risk score for a case:

```bash
python pattern_detector.py   # runs the showcase cases defined at the bottom of the file
```

---

## Running Tests

There is no automated test suite in this prototype. Manual verification steps are listed in the **Verifying It Works** section above.

---

## Quick Demo

The fastest way to see the full system in action:

1. Start both backend and frontend as described above.
2. Open `http://localhost:5173` — the dashboard loads with **CASE008** (Circular Layering, Ranchi, ₹12.5L).
3. Click any **evidence signal card** on the left panel — the related nodes highlight in the fraud network graph on the right.
4. Scroll down to the **Kingpin → Mule → Victim** hierarchy grid.
5. Use the **case selector** (top-right) to switch to other cases — try **CASE004** (SIM-Swap Ring) or **CASE054** (Layering Chain, highest amount ₹14L).
6. Click the **🗺 Geo Map** button (top-right) to open the geographic analytics dashboard.

---

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | Virtual environment not activated or packages not installed | Run `pip install fastapi uvicorn pandas networkx` inside the activated `.venv` |
| `ModuleNotFoundError: No module named 'networkx'` | Same as above | Same fix — install all four packages together |
| `FileNotFoundError: Dataset not found: ...cases.csv` | Running `main.py` from the wrong directory | Always run `python main.py` from inside `src/backend/`, not from the repo root |
| Backend starts but returns `500` errors | CSV files missing or corrupt | Verify all 5 files exist in `src/backend/data/raw/` |
| Frontend shows "Failed to load cases" | Backend is not running | Start the backend first in Terminal 1, then the frontend in Terminal 2 |
| Frontend shows "Network request failed" | CORS mismatch — frontend not on port 5173 | Ensure the Vite dev server is running on `http://localhost:5173` (default) |
| `npm install` fails | Node.js version too old | Ensure Node.js 18+ is installed: `node --version` |
| `Activate.ps1 cannot be loaded` on Windows | PowerShell execution policy | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` then retry |
| Graph renders but all nodes overlap | Browser window too small | Zoom out in the browser or use the ReactFlow minimap / Controls to navigate |
