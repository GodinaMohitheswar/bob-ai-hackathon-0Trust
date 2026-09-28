"""
FRAUDGRAPH — watsonx.ai Narrative Generator
============================================

Generates the FIR case narrative using IBM watsonx.ai (Granite).

Uses the watsonx.ai REST API directly (no SDK) so the model spec
prefetch that requires a WML service association is skipped entirely.

Degrades gracefully:
  - If env vars are missing  → falls back to template.
  - If IAM token fetch fails → falls back to template.
  - If generation API fails  → falls back to template.

In all fallback cases, source = "template".
When the LLM responds,   source = "watsonx".

Environment variables (set in src/backend/.env):
    WATSONX_API_KEY
    WATSONX_PROJECT_ID
    WATSONX_URL  (default: https://us-south.ml.cloud.ibm.com)
"""

import os
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from the backend directory (gitignored — credentials safe)
load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

WATSONX_URL        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_API_KEY    = os.getenv("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
GENERATION_URL = (
    f"{WATSONX_URL}/ml/v1/text/generation?version=2023-05-29"
)

MODEL_ID = "ibm/granite-3-8b-instruct"

GENERATE_PARAMS = {
    "max_new_tokens":     350,
    "min_new_tokens":     80,
    "temperature":        0.2,
    "top_p":              0.85,
    "repetition_penalty": 1.1,
    "stop_sequences":     ["\n\n", "---"],
}


# =========================================================
# IAM TOKEN
# =========================================================

def _get_iam_token(api_key: str) -> str:
    """Exchange an IBM Cloud API key for a short-lived IAM bearer token."""
    resp = requests.post(
        IAM_TOKEN_URL,
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# =========================================================
# PROMPT BUILDER
# =========================================================

def _build_prompt(ctx: dict) -> str:
    patterns_str = ", ".join(ctx.get("patterns", []))
    return (
        "<|system|>\n"
        "You are a cyber-crime investigation assistant for Indian law "
        "enforcement. Write factual, formal case narrative paragraphs "
        "suitable for inclusion in a First Information Report (FIR). "
        "Use only the evidence provided. Do not invent facts. "
        "Do not conclude guilt. Use 'alleged' or 'suspected' where "
        "appropriate. Write exactly one cohesive paragraph.\n"
        "<|user|>\n"
        "Write a formal FIR case narrative paragraph.\n\n"
        f"Case ID: {ctx['case_id']}\n"
        f"Jurisdiction: {ctx['location']}\n"
        f"Victim: {ctx['victim_name']} (Phone: {ctx['victim_phone']})\n"
        f"Alleged orchestrator (Kingpin): {ctx['kingpin_name']} "
        f"(ID: {ctx['kingpin_id']})\n"
        f"Mule chain: {ctx['mule_summary']}\n"
        f"Total funds moved: {ctx['total_amount']}\n"
        f"Detected fraud patterns: {patterns_str}\n"
        f"Investigation priority score: {ctx['score']}/100 "
        f"({ctx['priority']})\n"
        f"Evidence signal count: {ctx['evidence_count']}\n\n"
        "Narrative paragraph:\n"
        "<|assistant|>\n"
    )


# =========================================================
# CONTEXT BUILDER
# =========================================================

def _build_context(fir_data: dict) -> dict:
    victim  = fir_data.get("victim") or {}
    accused = fir_data.get("accused") or []
    meta    = fir_data.get("fir_meta") or {}
    signals = fir_data.get("evidence_signals") or []

    kingpin = next((a for a in accused if a.get("role") == "kingpin"), {})
    mules   = [a for a in accused if a.get("role") == "mule"]

    if mules:
        levels = [str(m["mule_level"]) for m in mules if m.get("mule_level")]
        mule_summary = (
            f"{len(mules)} mule(s)"
            + (f" (Levels: {', '.join(levels)})" if levels else "")
        )
    else:
        mule_summary = "none identified"

    city     = meta.get("jurisdiction_city", "")
    state    = meta.get("jurisdiction_state", "")
    location = ", ".join(filter(None, [city, state])) or "unknown jurisdiction"

    total_amount = meta.get("total_amount_moved")
    try:
        amount_str = f"\u20b9{float(total_amount):,.0f}"
    except (TypeError, ValueError):
        amount_str = "an undisclosed amount"

    return {
        "case_id":       fir_data.get("case_id", ""),
        "location":      location,
        "victim_name":   victim.get("name", "Unknown"),
        "victim_phone":  victim.get("phone", "Unknown"),
        "kingpin_name":  kingpin.get("name", "Unknown"),
        "kingpin_id":    kingpin.get("identity_id", "Unknown"),
        "mule_summary":  mule_summary,
        "total_amount":  amount_str,
        "patterns":      [s["pattern_type"] for s in signals],
        "score":         meta.get("investigation_score", 0),
        "priority":      meta.get("priority", "UNKNOWN"),
        "evidence_count": meta.get("evidence_count", 0),
    }


# =========================================================
# MAIN ENTRY POINT
# =========================================================

def generate_narrative(
    fir_data: dict,
    template_fallback_fn=None,
) -> tuple[str, str]:
    """
    Generate the FIR narrative using IBM watsonx.ai Granite.

    Returns (narrative_text, source) where source is
    "watsonx" or "template".
    """

    def _fallback(reason: str) -> tuple[str, str]:
        logger.info("watsonx narrative unavailable: %s — using template", reason)
        if template_fallback_fn:
            return template_fallback_fn(), "template"
        return fir_data.get("narrative", "Narrative unavailable."), "template"

    # 1. Credentials present?
    if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
        return _fallback("WATSONX_API_KEY or WATSONX_PROJECT_ID not set")

    # 2. Get IAM token
    try:
        token = _get_iam_token(WATSONX_API_KEY)
    except Exception as exc:
        return _fallback(f"IAM token error: {exc}")

    # 3. Call generation endpoint directly — no SDK, no model spec prefetch
    try:
        ctx    = _build_context(fir_data)
        prompt = _build_prompt(ctx)

        resp = requests.post(
            GENERATION_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "Accept":        "application/json",
            },
            json={
                "model_id":   MODEL_ID,
                "input":      prompt,
                "parameters": GENERATE_PARAMS,
                "project_id": WATSONX_PROJECT_ID,
            },
            timeout=30,
        )

        if resp.status_code == 403:
            error_code = resp.json().get("errors", [{}])[0].get("code", "")
            if error_code == "no_associated_service_instance_error":
                return _fallback(
                    "watsonx project has no Watson Machine Learning instance — "
                    "associate one at cloud.ibm.com to enable AI generation"
                )
            return _fallback(f"403 from watsonx: {resp.text[:200]}")

        resp.raise_for_status()

        results = resp.json().get("results", [])
        if not results:
            return _fallback("empty results array from watsonx")

        narrative = results[0].get("generated_text", "").strip()
        if not narrative:
            return _fallback("empty generated_text from watsonx")

        return narrative, "watsonx"

    except Exception as exc:
        return _fallback(f"generation error: {exc}")
