from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import math
import uvicorn

from data_loader import get_case_data, get_case_ids, load_all_data
from fraud_graph import build_case_graph, get_graph_summary
from pattern_detector import detect_case_patterns
from risk_scoring import get_case_score, get_score_summary
from fir_brief import generate_fir_brief


app = FastAPI(
    title="FRAUDGRAPH API",
    description="Cyber Fraud Investigation and Network Intelligence Platform",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def clean_value(value):
    """
    Convert pandas/numpy values into JSON-safe Python values.

    Important:
    NaN and infinite float values are converted to None
    because JSON does not allow NaN or Infinity.
    """

    # Handle None
    if value is None:
        return None

    # Handle floating-point NaN / Infinity
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value

    # Handle numpy scalar values
    if hasattr(value, "item"):
        try:
            value = value.item()

            if isinstance(value, float) and not math.isfinite(value):
                return None

            return value

        except Exception:
            pass

    return value


def make_json_safe(obj):
    """
    Recursively convert dictionaries, lists, tuples,
    and graph data into JSON-safe values.
    """

    if isinstance(obj, dict):
        return {
            str(key): make_json_safe(value)
            for key, value in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [
            make_json_safe(value)
            for value in obj
        ]

    return clean_value(obj)


def validate_case(case_id: str):
    """Validate that a case exists."""

    if case_id not in get_case_ids():
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_id} not found."
        )


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "FRAUDGRAPH",
        "description": "Cyber Fraud Investigation and Network Intelligence Platform",
        "status": "running",
        "docs": "/docs",
    }


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/health")
def health():
    data = load_all_data()

    return {
        "status": "healthy",
        "cases_loaded": int(len(data["cases"])),
    }


# ---------------------------------------------------------
# Cases
# ---------------------------------------------------------

@app.get("/cases")
def get_cases():
    data = load_all_data()

    cases = data["cases"]

    return {
        "count": int(len(cases)),
        "cases": make_json_safe(
            cases.to_dict(orient="records")
        ),
    }


# ---------------------------------------------------------
# Single Case
# ---------------------------------------------------------

@app.get("/cases/{case_id}")
def get_case(case_id: str):
    validate_case(case_id)

    case_data = get_case_data(case_id)

    return {
        "case_id": case_id,
        "identities": make_json_safe(
            case_data["identities"].to_dict(orient="records")
        ),
        "devices": make_json_safe(
            case_data["devices"].to_dict(orient="records")
        ),
        "transactions": make_json_safe(
            case_data["transactions"].to_dict(orient="records")
        ),
        "calls": make_json_safe(
            case_data["calls"].to_dict(orient="records")
        ),
    }


# ---------------------------------------------------------
# Network
# ---------------------------------------------------------

@app.get("/cases/{case_id}/network")
def get_case_network(case_id: str):
    validate_case(case_id)

    graph = build_case_graph(case_id)

    summary = get_graph_summary(graph)

    nodes = []

    for node_id, attributes in graph.nodes(data=True):

        node_data = {
            "id": str(node_id),
            "type": attributes.get("type"),
            "attributes": make_json_safe(attributes),
        }

        nodes.append(node_data)

    edges = []

    for source, target, attributes in graph.edges(data=True):

        edge_data = {
            "source": str(source),
            "target": str(target),
            "type": attributes.get("type"),
            "attributes": make_json_safe(attributes),
        }

        edges.append(edge_data)

    return {
        "case_id": case_id,
        "summary": make_json_safe(summary),
        "nodes": nodes,
        "edges": edges,
    }


# ---------------------------------------------------------
# Risk
# ---------------------------------------------------------

@app.get("/cases/{case_id}/risk")
def get_case_risk(case_id: str):
    validate_case(case_id)

    return make_json_safe(
        get_score_summary(case_id)
    )


# ---------------------------------------------------------
# Alerts
# ---------------------------------------------------------

@app.get("/cases/{case_id}/alerts")
def get_case_alerts(case_id: str):
    validate_case(case_id)

    score_data = get_case_score(case_id)

    return {
        "case_id": case_id,
        "priority": score_data["priority"],
        "score": score_data["score"],
        "alerts": make_json_safe(
            score_data["findings"]
        ),
    }


# ---------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------

@app.get("/cases/{case_id}/hierarchy")
def get_case_hierarchy(case_id: str):
    validate_case(case_id)

    case_data = get_case_data(case_id)

    identities = case_data["identities"]

    hierarchy = []

    for _, row in identities.iterrows():

        hierarchy.append({
            "identity_id": clean_value(row.get("identity_id")),
            "name": clean_value(row.get("name")),
            "role": clean_value(row.get("role")),
            "mule_level": clean_value(row.get("mule_level")),
            "phone": clean_value(row.get("phone")),
            "account_id": clean_value(row.get("account_id")),
            "city": clean_value(row.get("address_city")),
            "state": clean_value(row.get("address_state")),
        })

    return {
        "case_id": case_id,
        "hierarchy": hierarchy,
    }


# ---------------------------------------------------------
# FIR Brief
# ---------------------------------------------------------

@app.get("/cases/{case_id}/fir-brief")
def get_case_fir_brief(case_id: str):
    validate_case(case_id)

    return make_json_safe(
        generate_fir_brief(case_id)
    )


# ---------------------------------------------------------
# Brief Data
# ---------------------------------------------------------

@app.get("/cases/{case_id}/brief-data")
def get_case_brief_data(case_id: str):
    validate_case(case_id)

    graph = build_case_graph(case_id)
    score = get_case_score(case_id)
    summary = get_graph_summary(graph)

    case_data = get_case_data(case_id)

    identities = []

    for _, row in case_data["identities"].iterrows():

        identities.append({
            "identity_id": clean_value(row.get("identity_id")),
            "name": clean_value(row.get("name")),
            "role": clean_value(row.get("role")),
            "mule_level": clean_value(row.get("mule_level")),
            "phone": clean_value(row.get("phone")),
            "account_id": clean_value(row.get("account_id")),
            "city": clean_value(row.get("address_city")),
            "state": clean_value(row.get("address_state")),
        })

    return make_json_safe({
        "case_id": case_id,

        "investigation": {
            "score": score["score"],
            "priority": score["priority"],
            "evidence_count": len(score["findings"]),
        },

        "network": summary,

        "hierarchy": identities,

        "evidence": score["findings"],

        "recommended_actions": score["recommended_actions"],

        "disclaimer": (
            "This output contains synthetic investigative signals "
            "derived from mock case records. It does not establish "
            "fraud, guilt, or criminal responsibility."
        ),
    })


# ---------------------------------------------------------
# Run Server
# ---------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
