# Solution Overview

## What We Built

**FRAUDGRAPH** is a cyber-fraud investigation and network intelligence platform purpose-built for Indian cyber-crime investigators. It ingests multi-source case data — transaction records, call logs, device registrations, and identity records — automatically constructs a relationship graph, runs 10 independent behavioural signal detectors, scores each case by investigation priority, maps the complete Kingpin → Mule → Victim organisational hierarchy, and presents everything through an interactive investigation dashboard with a geographic analytics view.

The platform turns what previously required days of manual spreadsheet work into a seconds-long automated analysis — giving investigators a network graph, a ranked evidence panel, a hierarchy grid, and a structured case brief the moment they select a case.

---

## How It Works

1. **Data ingestion** — Five structured CSV datasets (cases, identities, devices, transactions, calls) are loaded and schema-validated by `data_loader.py`. Each dataset is type-cleaned: booleans, numerics, and timestamps are normalised before any analysis begins.

2. **Graph construction** — `fraud_graph.py` builds a `NetworkX MultiDiGraph` per case, connecting 7 node types: `case`, `identity`, `account`, `phone`, `device`, `transaction`, and `call`. Every relationship is a named directed edge — `owns_account`, `sent_transaction`, `made_call`, `originated_on`, `used_device` — creating a fully traversable network of all entities involved in the case.

3. **Pattern detection** — `pattern_detector.py` runs 10 independent detectors against each case's data. None of them use ground-truth fraud labels (`is_fraudulent`, `pattern_type`) — all signals are derived purely from behavioral evidence:

   | Detector | What it finds |
   |---|---|
   | `detect_shared_devices()` | One device linked to multiple identities (SIM-swap signal) |
   | `detect_device_risk_flags()` | Devices carrying an explicit risk flag |
   | `detect_prior_fraud_identities()` | Identities with a prior fraud history |
   | `detect_fan_out()` | One account distributing funds to multiple receivers |
   | `detect_layering_chains()` | Multi-hop transaction paths ≥ 4 accounts deep |
   | `detect_transaction_cycles()` | Circular money flows (A → B → C → A) |
   | `detect_new_beneficiary_activity()` | Transactions to newly added, unverified beneficiaries |
   | `detect_otp_relay_calls()` | Calls explicitly typed as `otp_relay` |
   | `detect_spoof_suspected_calls()` | Calls with `caller_id_spoof_suspected = True` |
   | `detect_call_loops()` | Closed communication loops between phone numbers |

4. **Evidence consolidation** — `risk_scoring.py` deduplicates the raw detector output: overlapping layering paths are reduced to the longest chain, device and identity alerts are aggregated into single evidence items, and communication loops are deduplicated by their participating phone set. This prevents score inflation from redundant findings.

5. **Investigation scoring** — Each consolidated evidence category contributes a weighted score (max 100), capped per category to ensure breadth of evidence is required for high scores. The total maps to a priority band: `CRITICAL` (≥ 60), `HIGH` (≥ 40), `MEDIUM` (≥ 20), `LOW` (< 20).

6. **REST API** — `main.py` (FastAPI) exposes 10 endpoints. The `/cases/{id}/brief-data` endpoint is the primary composite: it assembles the investigation score, priority, evidence list, network summary, and the full Kingpin → Mule → Victim hierarchy into a single JSON response. A `make_json_safe()` utility ensures all pandas/numpy values are JSON-serialisable.

7. **Investigation dashboard** — `App.jsx` (React 19 + ReactFlow 11) renders the full case view: a fraud network graph with 7 colour-coded node layers, a clickable evidence panel that highlights related graph nodes on click, a hierarchy grid showing every identity by role and mule level, and a case brief summary. The case selector at the top loads any of the 100 cases on demand.

---

## Architecture Diagram

> See [`architecture.md`](architecture.md) for the full diagram, node/edge schema, and API reference.

```
CSV Datasets (5 files)
       │
       ▼
 data_loader.py  ──►  fraud_graph.py  ──►  NetworkX MultiDiGraph
       │                                         │
       ▼                                         │
pattern_detector.py (10 detectors)               │
       │                                         │
       ▼                                         ▼
 risk_scoring.py  ──────────────────►  main.py (FastAPI :8000)
                                             │
                          ┌──────────────────┴───────────────────┐
                          ▼                                       ▼
                    App.jsx                               GeoAnalytics.jsx
             (Investigation Dashboard)              (Geographic Analytics)
                  localhost:5173
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Ground-truth labels excluded from scoring** | `is_fraudulent` and `pattern_type` fields in the CSV are never used to produce findings. The investigation score is derived entirely from behavioural signals, so it generalises to unseen cases where labels are unknown. |
| **NetworkX `MultiDiGraph` instead of a relational join** | Fraud networks are fundamentally graph problems — cycle detection, shortest paths, fan-out degree. A graph structure makes these computations natural and efficient; SQL joins would require complex recursive CTEs for the same result. |
| **Per-category scoring caps** | Without caps, a case with 20 layering path variants would dominate. Caps force the score to reflect the breadth of different signal types present, not the loudness of a single detector. |
| **Evidence consolidation before scoring** | Raw detectors can produce dozens of overlapping path findings (A→B→C, A→B→C→D, B→C→D). Consolidating first — keeping only the longest chain — gives investigators one clean finding instead of noise. |
| **Evidence cards linked to graph nodes** | Clicking a signal in the evidence panel calls `getEvidenceFocus()` which resolves all entity IDs referenced in that finding and highlights them in the ReactFlow graph. This turns abstract evidence text into a visual, navigable network trace. |
| **Stateless backend with CSV data** | For a hackathon prototype, CSV files eliminate the need for a running database. The `data_loader.py` validation layer ensures the system fails loudly (not silently) if the data schema drifts. |
| **SVG India map without external libraries** | The geographic dashboard uses a hand-crafted SVG path for India's outline and hardcoded coordinates for 40+ cities (including Jamtara, Deoghar, Dhanbad — the specific fraud hotspots). No Mapbox/Leaflet token or network request is needed. |

---

## IBM Technologies Used

- **IBM Bob:** Used as the primary AI-assisted development environment throughout the project — for code generation, architecture review, pattern detection algorithm design, evidence consolidation logic, and documentation. Bob's agent mode enabled rapid iteration across the full-stack codebase (Python backend + React frontend) within the hackathon timeline.

---

## What the User Experience Looks Like

An investigator opens the dashboard and selects a case from the dropdown. Within seconds they see:

1. **Priority badge** — CRITICAL / HIGH / MEDIUM / LOW — telling them immediately how urgently this case needs attention.
2. **Metric row** — investigation score out of 100, number of evidence signals, total graph nodes.
3. **Evidence panel** (left) — each detected signal as a card showing pattern type, severity, and a plain-English description. Clicking any card highlights the relevant accounts, phones, or devices in the network graph.
4. **Fraud network graph** (right) — a zoomable, draggable ReactFlow canvas with nodes colour-coded by type (identity, account, phone, device, transaction, call) and role (kingpin nodes highlighted differently from mule and victim nodes).
5. **Hierarchy grid** — every person in the case listed by their role (kingpin, mule level 1/2/3, victim) with their identity ID, account, and phone — the exact information needed to prioritise arrests and account freezes.
6. **Case brief panel** — a compact structured summary of score, priority, evidence count, and network size — the starting point for drafting an FIR.

The entire analysis — from raw CSV data to scored, visualised, hierarchically mapped case brief — runs in under one second per case.
