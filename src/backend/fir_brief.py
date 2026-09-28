"""
FRAUDGRAPH — FIR Brief Generator
=================================

Assembles a structured First Information Report (FIR) brief from
the case data already held in the investigation engine.

Nothing here is duplicated logic.  All scoring and pattern data
is sourced from risk_scoring.get_case_score() and
data_loader.get_case_data().

IMPORTANT:
  The generated narrative and legal sections are investigative
  aids derived from synthetic mock data.  They do NOT constitute
  a formal FIR, legal advice, or a determination of guilt.
"""

from data_loader import get_case_data, load_all_data
from risk_scoring import get_case_score
from watsonx_narrative import generate_narrative


# =========================================================
# LEGAL SECTIONS
# =========================================================
#
# Maps each detected pattern type to the Indian legal
# provisions that are typically applicable.
#
# Sources:
#   IT Act 2000 (as amended 2008)
#   Indian Penal Code 1860
#   Code of Criminal Procedure 1973
#   Prevention of Money Laundering Act 2002
# =========================================================

LEGAL_SECTIONS = {
    "Shared Device": [
        {
            "act": "IT Act 2000",
            "section": "Section 66",
            "description": (
                "Computer-related offences — unauthorised access "
                "or use of a device."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 420",
            "description": (
                "Cheating and dishonestly inducing delivery of "
                "property."
            ),
        },
    ],
    "OTP Relay Signal": [
        {
            "act": "IT Act 2000",
            "section": "Section 66C",
            "description": (
                "Identity theft — fraudulent use of another "
                "person's electronic signature, password, or "
                "unique identification feature."
            ),
        },
        {
            "act": "IT Act 2000",
            "section": "Section 66D",
            "description": (
                "Cheating by personation using a computer "
                "resource."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 419",
            "description": (
                "Punishment for cheating by personation."
            ),
        },
    ],
    "Caller ID Spoof Signal": [
        {
            "act": "IT Act 2000",
            "section": "Section 66D",
            "description": (
                "Cheating by personation using a communication "
                "device."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 419",
            "description": (
                "Punishment for cheating by personation."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 420",
            "description": (
                "Cheating and dishonestly inducing delivery of "
                "property."
            ),
        },
    ],
    "Transaction Cycle": [
        {
            "act": "PMLA 2002",
            "section": "Section 3",
            "description": (
                "Offence of money laundering — concealment, "
                "possession, acquisition, or use of proceeds "
                "of crime."
            ),
        },
        {
            "act": "PMLA 2002",
            "section": "Section 4",
            "description": (
                "Punishment for money laundering — rigorous "
                "imprisonment of three to seven years."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 420",
            "description": (
                "Cheating and dishonestly inducing delivery of "
                "property."
            ),
        },
    ],
    "Fan-Out Distribution": [
        {
            "act": "PMLA 2002",
            "section": "Section 3",
            "description": (
                "Offence of money laundering — layering and "
                "distribution of proceeds of crime."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 420",
            "description": (
                "Cheating and dishonestly inducing delivery of "
                "property."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 120B",
            "description": (
                "Criminal conspiracy to commit a punishable "
                "offence."
            ),
        },
    ],
    "Layering Chain": [
        {
            "act": "PMLA 2002",
            "section": "Section 3",
            "description": (
                "Offence of money laundering — multi-hop "
                "layering through intermediary accounts."
            ),
        },
        {
            "act": "PMLA 2002",
            "section": "Section 4",
            "description": (
                "Punishment for money laundering."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 120B",
            "description": (
                "Criminal conspiracy."
            ),
        },
    ],
    "Risk-Flagged Devices": [
        {
            "act": "IT Act 2000",
            "section": "Section 66",
            "description": (
                "Computer-related offences using a risk-flagged "
                "device."
            ),
        },
        {
            "act": "CrPC 1973",
            "section": "Section 102",
            "description": (
                "Power of police officer to seize certain "
                "property — applicable to risk-flagged devices."
            ),
        },
    ],
    "Prior Fraud Flag": [
        {
            "act": "IPC 1860",
            "section": "Section 420",
            "description": (
                "Cheating — prior flag indicates repeat offence "
                "pattern."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 75",
            "description": (
                "Enhanced punishment for person previously "
                "convicted of offences against property."
            ),
        },
    ],
    "Communication Loop": [
        {
            "act": "IPC 1860",
            "section": "Section 120B",
            "description": (
                "Criminal conspiracy — circular communication "
                "pattern indicates coordinated activity."
            ),
        },
        {
            "act": "IT Act 2000",
            "section": "Section 66",
            "description": (
                "Computer-related offences using communication "
                "devices."
            ),
        },
    ],
    "New Beneficiary": [
        {
            "act": "IT Act 2000",
            "section": "Section 66C",
            "description": (
                "Identity theft — fraudulent addition of new "
                "beneficiary using victim credentials."
            ),
        },
        {
            "act": "IT Act 2000",
            "section": "Section 66D",
            "description": (
                "Cheating by personation using a computer "
                "resource."
            ),
        },
        {
            "act": "IPC 1860",
            "section": "Section 420",
            "description": (
                "Cheating and dishonestly inducing delivery of "
                "property."
            ),
        },
    ],
}


# =========================================================
# NARRATIVE TEMPLATES
# =========================================================

def build_narrative(case_id, score_data, case_meta, identities):
    """
    Build a plain-language FIR narrative paragraph from the
    case evidence.  Uses only data already present in the
    investigation record.
    """

    priority   = score_data["priority"]
    score      = score_data["score"]
    patterns   = [
        f["pattern_type"]
        for f in score_data["findings"]
    ]

    victim  = next(
        (p for p in identities if p.get("role") == "victim"),
        None,
    )
    kingpin = next(
        (p for p in identities if p.get("role") == "kingpin"),
        None,
    )
    mules   = [p for p in identities if p.get("role") == "mule"]

    city  = case_meta.get("jurisdiction_city", "unknown jurisdiction")
    state = case_meta.get("jurisdiction_state", "")
    location = f"{city}, {state}".strip(", ")

    total_amount = case_meta.get("total_amount_moved")
    amount_str = (
        f"₹{float(total_amount):,.0f}"
        if total_amount
        else "an undisclosed amount"
    )

    # --- Victim sentence ---
    if victim:
        victim_line = (
            f"The complainant / victim in this case is "
            f"{victim['name']} (Identity ID: {victim['identity_id']}, "
            f"Phone: {victim['phone']}, {location})."
        )
    else:
        victim_line = (
            f"A victim has been identified in this case "
            f"({location})."
        )

    # --- Pattern summary ---
    pattern_list = ", ".join(patterns)
    pattern_line = (
        f"Network analysis of transaction records, call logs, "
        f"and device data has identified the following "
        f"investigative signals: {pattern_list}."
    )

    # --- Financial line ---
    financial_line = (
        f"Total funds moved across the detected network amount "
        f"to {amount_str}."
    )

    # --- Accused line ---
    if kingpin:
        accused_line = (
            f"The alleged network appears to be orchestrated by "
            f"{kingpin['name']} (Identity ID: {kingpin['identity_id']}, "
            f"Role: Kingpin)"
        )
        if mules:
            mule_names = ", ".join(
                f"{m['name']} (L{m['mule_level']})"
                for m in mules
                if m.get("mule_level")
            )
            if mule_names:
                accused_line += (
                    f", operating through {len(mules)} mule "
                    f"account(s): {mule_names}"
                )
        accused_line += "."
    else:
        accused_line = (
            f"The investigation involves {len(identities)} "
            f"identified parties."
        )

    # --- Priority line ---
    priority_line = (
        f"The investigation priority score is {score}/100 "
        f"({priority}), derived from {len(score_data['findings'])} "
        f"consolidated evidence signals."
    )

    return " ".join([
        victim_line,
        pattern_line,
        financial_line,
        accused_line,
        priority_line,
    ])


# =========================================================
# TRANSACTION EXHIBIT
# =========================================================

def build_transaction_exhibit(case_id):
    """
    Build a numbered transaction exhibit table from the
    case's transaction records.

    Omits originating IPs.  Includes: transaction ID,
    sender account, receiver account, amount, channel,
    status, new-beneficiary flag.
    """

    data = load_all_data()

    txns = data["transactions"]

    case_txns = txns[
        txns["case_id"].astype(str) == str(case_id)
    ].copy()

    exhibit = []

    for i, (_, row) in enumerate(
        case_txns.iterrows(),
        start=1,
    ):

        amount = row.get("amount")

        try:
            amount_str = f"₹{float(amount):,.0f}"
        except (TypeError, ValueError):
            amount_str = str(amount)

        exhibit.append({
            "exhibit_no": i,
            "transaction_id": str(row.get("transaction_id", "")),
            "sender_account":  str(row.get("sender_account", "")),
            "receiver_account": str(row.get("receiver_account", "")),
            "amount": amount_str,
            "channel": str(row.get("channel", "")),
            "status":  str(row.get("status", "")),
            "new_beneficiary": bool(row.get("is_new_beneficiary", False)),
        })

    return exhibit


# =========================================================
# APPLICABLE LEGAL SECTIONS
# =========================================================

def collect_legal_sections(findings):
    """
    Collect deduplicated legal sections from all detected
    patterns, preserving insertion order.
    """

    seen = set()

    sections = []

    for finding in findings:

        pattern_type = finding.get("pattern_type", "")

        for section in LEGAL_SECTIONS.get(
            pattern_type,
            [],
        ):

            key = (section["act"], section["section"])

            if key not in seen:

                seen.add(key)

                sections.append(section)

    return sections


# =========================================================
# ACCUSED LIST
# =========================================================

def build_accused_list(identities):
    """
    Return the accused list (non-victim identities) with
    safe fields only.  Excludes Aadhaar, IFSC, raw account
    numbers.
    """

    accused = []

    for person in identities:

        if person.get("role") == "victim":
            continue

        raw_level = person.get("mule_level")
        try:
            mule_level = int(raw_level) if (raw_level is not None and raw_level == raw_level) else None
        except (TypeError, ValueError):
            mule_level = None

        accused.append({
            "identity_id": person.get("identity_id"),
            "name":        person.get("name"),
            "role":        person.get("role"),
            "mule_level":  mule_level,
            "phone":       person.get("phone"),
            "city":        person.get("city"),
            "state":       person.get("state"),
        })

    return accused


# =========================================================
# MAIN BRIEF ASSEMBLER
# =========================================================

def generate_fir_brief(case_id):
    """
    Generate a complete FIR brief for one case.

    Returns a dict with:
        case_id
        fir_meta          — case metadata from the dataset
        narrative         — plain-language paragraph
        victim            — victim identity record
        accused           — non-victim identities
        transaction_exhibit — numbered transaction table
        evidence_signals  — pattern + severity + description
        legal_sections    — applicable IT Act / IPC sections
        recommended_actions — ordered action list
        disclaimer
    """

    score_data  = get_case_score(case_id)
    case_data   = get_case_data(case_id)

    # ----------------------------------------------------------
    # Case metadata from the cases dataset
    # ----------------------------------------------------------

    all_data   = load_all_data()
    cases_df   = all_data["cases"]
    case_row   = cases_df[
        cases_df["case_id"].astype(str) == str(case_id)
    ]

    case_meta = {}

    if not case_row.empty:

        row = case_row.iloc[0]

        for col in [
            "complaint_id",
            "complaint_date",
            "jurisdiction_city",
            "jurisdiction_state",
            "case_status",
            "total_amount_moved",
            "num_identities",
            "num_mules",
        ]:

            val = row.get(col)

            if val == val:  # NaN check
                case_meta[col] = val

    # ----------------------------------------------------------
    # Identity roster (safe fields only)
    # ----------------------------------------------------------

    identities = []

    for _, row in case_data["identities"].iterrows():

        raw_level = row.get("mule_level")
        try:
            mule_level = int(raw_level) if (raw_level is not None and raw_level == raw_level) else None
        except (TypeError, ValueError):
            mule_level = None

        identities.append({
            "identity_id": str(row.get("identity_id", "")),
            "name":        str(row.get("name", "")),
            "role":        str(row.get("role", "")),
            "mule_level":  mule_level,
            "phone":       str(row.get("phone", "")),
            "city":        str(row.get("address_city", "")),
            "state":       str(row.get("address_state", "")),
        })

    victim = next(
        (p for p in identities if p["role"] == "victim"),
        None,
    )

    # ----------------------------------------------------------
    # Evidence signals (pattern + severity + description only)
    # ----------------------------------------------------------

    evidence_signals = [
        {
            "pattern_type": f.get("pattern_type"),
            "severity":     f.get("severity"),
            "description":  f.get("description", ""),
        }
        for f in score_data["findings"]
    ]

    # ----------------------------------------------------------
    # Assemble a partial brief first so watsonx_narrative can
    # read fir_meta, accused, victim, and evidence_signals from
    # it when building the prompt context.
    # ----------------------------------------------------------

    partial_brief = {
        "case_id": str(case_id),

        "fir_meta": {
            "complaint_id":       case_meta.get("complaint_id"),
            "complaint_date":     case_meta.get("complaint_date"),
            "jurisdiction_city":  case_meta.get("jurisdiction_city"),
            "jurisdiction_state": case_meta.get("jurisdiction_state"),
            "case_status":        case_meta.get("case_status"),
            "investigation_score": score_data["score"],
            "priority":           score_data["priority"],
            "evidence_count":     score_data["consolidated_finding_count"],
            "total_amount_moved": case_meta.get("total_amount_moved"),
        },

        "victim": victim,

        "accused": build_accused_list(identities),

        "evidence_signals": evidence_signals,
    }

    # Template function passed as fallback — called only when watsonx
    # is unavailable, so no double computation on the happy path.
    def _template():
        return build_narrative(
            case_id,
            score_data,
            case_meta,
            identities,
        )

    narrative_text, narrative_source = generate_narrative(
        partial_brief,
        template_fallback_fn=_template,
    )

    return {
        "case_id": str(case_id),

        "fir_meta": partial_brief["fir_meta"],

        "narrative": narrative_text,

        "narrative_source": narrative_source,

        "victim": victim,

        "accused": build_accused_list(identities),

        "transaction_exhibit": build_transaction_exhibit(
            case_id
        ),

        "evidence_signals": evidence_signals,

        "legal_sections": collect_legal_sections(
            score_data["findings"]
        ),

        "recommended_actions": score_data["recommended_actions"],

        "disclaimer": (
            "This brief is generated from synthetic investigative "
            "signals derived from mock case records. It does not "
            "constitute a formal FIR, legal advice, or a "
            "determination of fraud, guilt, or criminal "
            "responsibility. All actions must be authorised by a "
            "competent officer."
        ),
    }
