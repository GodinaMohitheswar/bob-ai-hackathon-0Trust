# 🚀 [Cyber Fraud Network Analyzer]

> ⚠️ **Replace everything in `[ ]` brackets with your actual content before submission.**

---

## 👥 Team

| Field | Value |
|---|---|


# 🔍 FRAUDGRAPH — Cyber Fraud Investigation & Network Intelligence Platform

> Automated fraud network analysis for Indian cyber-crime investigators — built for the IBM Bob AI Hackathon.

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | [0Trust] |
| **Track** | [Cyber forensics] |
| **Team Lead** | [Mohitheswar Godina] — [mohitheswargodina@gmail.com] |
| **Members** | [Rishiraam Gopinath], [Anem Pritam], [Soumya T J] |
---

## 🎯 Problem Statement

Indian cyber-crime investigators — police officers at state cyber-cells and bank fraud analysts — spend days to weeks manually cross-referencing transaction records, call logs, device IDs, and identity data across spreadsheets to trace organised fraud networks. Inspired by the real Jamtara SIM-swap ring (95,000+ UPI fraud cases in FY2023), most cases go unsolved not because of a lack of evidence, but because there are no tools to connect it. In the 100-case dataset modelled by this project, ~41% of fraud cases had no complaint filed at all, and roughly 75% remain unresolved.

---

## 💡 Solution

FRAUDGRAPH automatically ingests multi-source case data (transactions, call logs, device registrations, identity records), constructs a `NetworkX` relationship graph, runs 10 independent behavioural signal detectors, scores each case by investigation priority (LOW → CRITICAL), maps the complete Kingpin → Mule → Victim organisational hierarchy, and presents everything through an interactive investigation dashboard. What previously took investigators days of manual spreadsheet work now takes under one second per case.

---

## ✨ Key Features

- **Fraud Network Graph** — Interactive ReactFlow canvas connecting 7 node types (case, identity, account, phone, device, transaction, call) with 10+ named relationship edges. Nodes are colour-coded by type and role (kingpin, mule, victim).
- **10-Signal Pattern Detection Engine** — Automatically detects Fan-Out Distribution, Layering Chains, Transaction Cycles, Shared Devices (SIM-swap), OTP Relay calls, Caller ID Spoofing, Communication Loops, and more — all from raw behavioral data, never from fraud labels.
- **Investigation Priority Scoring** — Weighted, capped evidence scoring (max 100 pts across 10 categories) maps each case to a CRITICAL / HIGH / MEDIUM / LOW priority band for triage.
- **Kingpin → Mule → Victim Hierarchy** — Full organisational chart of every identity in the case, showing role, mule level, account, phone, and jurisdiction — the exact data needed to prioritise arrests and account freezes.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3.13, JavaScript (ES2023) |
| **Frameworks** | FastAPI, Uvicorn, React 19, Vite 8, ReactFlow 11 |
| **IBM Technologies** | IBM Bob (AI-assisted development throughout) |
| **Data / Graph** | pandas, NetworkX (`MultiDiGraph`) |
| **Databases** | None — mock data served from CSV files |
| **Other** | CORS middleware, SVG (custom India map), GitHub Actions (validation) |

---

## 📁 Repository Structure

```
├── src/
│   ├── backend/
│   │   ├── main.py                  # FastAPI REST API (10 endpoints)
│   │   ├── data_loader.py           # CSV ingestion & schema validation
│   │   ├── fraud_graph.py           # NetworkX MultiDiGraph builder
│   │   ├── pattern_detector.py      # 10 behavioural signal detectors
│   │   ├── risk_scoring.py          # Evidence consolidation & priority scoring
│   │   ├── relationship_engine.py   # Shared-device & transaction utilities
│   │   └── data/raw/                # 5 mock CSV datasets (100 cases)
│   └── frontend/
│       └── src/
│           ├── App.jsx              # Investigation dashboard
│           └── GeoAnalytics.jsx     # Geographic analytics dashboard
├── docs/
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
├── demo/
│   ├── screenshots/
│   └── demo-video-link.txt
├── presentation/
└── submission.yaml
```

---

## ⚡ How to Run

> No IBM Cloud account, database, or API keys required. All data is pre-loaded as CSV files.

```bash
# 1. Clone the repo
git clone https://github.com/your-org/bob-ai-hackathon-0Trust.git
cd bob-ai-hackathon-0Trust

# 2. Backend — install Python dependencies (Terminal 1)
cd src/backend
python -m venv .venv

# Activate (macOS/Linux):
source .venv/bin/activate
# Activate (Windows PowerShell):
.\.venv\Scripts\Activate.ps1

pip install fastapi uvicorn pandas networkx
python main.py
# → API running at http://127.0.0.1:8000

# 3. Frontend — install and start (Terminal 2)
cd src/frontend
npm install
npm run dev
# → Dashboard running at http://localhost:5173
```

Full setup instructions, verification steps, and troubleshooting: [`docs/setup-guide.md`](docs/setup-guide.md)

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/](presentation/) |

---

## ⚠️ Known Limitations

- **Synthetic data only** — All 100 cases, identities, transactions, and calls are mock data. No real PII or financial records are used. A disclaimer is surfaced on every case brief.
- **No authentication** — The API has no access control; all endpoints are publicly accessible on localhost. Not production-ready.
- **Stateless CSV backend** — The API reloads all 5 CSVs on every request. At production scale this would need a database (PostgreSQL / Neo4j) with a connection pool.
- **No automated test suite** — Verification is manual; no `pytest` tests are included in this prototype.
- **Frontend tested on Chrome and Firefox** — Behaviour on other browsers has not been validated.
- **Graph layout is algorithmic, not force-directed** — Nodes are positioned in horizontal bands by type. Highly connected cases can appear dense; the ReactFlow minimap and zoom controls help navigate.

---

## 🏅 What We're Most Proud Of

The **pattern detection engine** (`pattern_detector.py`) and its connection to the **interactive fraud network graph**. Ten independent detectors run against raw behavioral data — no fraud labels used — and every finding is linked back to specific graph nodes so investigators can click a signal and immediately see which accounts, phones, and devices are implicated. The scoring system (weighted, category-capped, consolidation-first) is also genuinely novel: it forces a high score to reflect breadth of evidence across multiple signal types rather than noise from a single over-firing detector. Together, these turn a raw CSV case file into a prioritised, navigable, court-documentable investigation brief in under one second.

---
