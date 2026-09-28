from collections import defaultdict

from pattern_detector import detect_case_patterns


# =========================================================
# FRAUDGRAPH
# Investigation Evidence & Priority Engine
# =========================================================
#
# IMPORTANT:
#
# This score is NOT:
#   - probability of fraud
#   - proof of fraud
#   - guilt score
#
# It is an INVESTIGATION PRIORITY SCORE based on
# independently observed synthetic evidence.
#
# Ground-truth fields such as:
#   is_fraudulent
#   case pattern_type
#
# are NOT used to calculate this score.
# They can be used later for evaluation/testing.
# =========================================================


# ---------------------------------------------------------
# SIGNAL WEIGHTS
# ---------------------------------------------------------

SIGNAL_WEIGHTS = {
    "Shared Device": 15,
    "OTP Relay Signal": 15,
    "Caller ID Spoof Signal": 15,
    "Transaction Cycle": 15,
    "Fan-Out Distribution": 12,
    "Layering Chain": 12,
    "Risk-Flagged Devices": 6,
    "Prior Fraud Flag": 6,
    "Communication Loop": 5,
    "New Beneficiary": 3,
}


# ---------------------------------------------------------
# CATEGORY CAPS
# ---------------------------------------------------------
#
# Repeated evidence from the same category cannot
# endlessly increase the investigation score.
# ---------------------------------------------------------

CATEGORY_CAPS = {
    "Shared Device": 15,
    "OTP Relay Signal": 15,
    "Caller ID Spoof Signal": 15,
    "Transaction Cycle": 15,
    "Fan-Out Distribution": 12,
    "Layering Chain": 12,
    "Risk-Flagged Devices": 12,
    "Prior Fraud Flag": 6,
    "Communication Loop": 10,
    "New Beneficiary": 9,
}


# ---------------------------------------------------------
# RECOMMENDED ACTIONS
# ---------------------------------------------------------
#
# Each pattern type maps to a list of concrete investigative
# actions an officer should take when that signal is present.
#
# These are structural / procedural recommendations only.
# They do NOT assert guilt or establish fraud.
# ---------------------------------------------------------

RECOMMENDED_ACTIONS = {
    "Shared Device": [
        "Obtain the IMEI/device record for the shared device from the "
        "telecom operator under Section 91 CrPC.",
        "Verify whether the device was reported stolen or SIM-swapped "
        "prior to the incident date.",
        "Collect statements from all identities linked to the shared "
        "device to establish lawful custody.",
    ],
    "OTP Relay Signal": [
        "Seize and preserve the device used for OTP relay as digital "
        "evidence under Section 65B of the Indian Evidence Act.",
        "Request Call Detail Records (CDR) from the telecom operator "
        "for the caller and receiver numbers.",
        "Identify the banking or payment application linked to the "
        "OTP flow and contact their nodal officer.",
    ],
    "Caller ID Spoof Signal": [
        "Report the spoofed number to the telecom operator's fraud "
        "management team for trace and block.",
        "Request IPDR (IP Detail Records) from the operator to trace "
        "the originating call gateway.",
        "File a complaint with TRAI under the Unsolicited Commercial "
        "Communications framework if applicable.",
    ],
    "Transaction Cycle": [
        "Issue a lien / freeze request to the concerned banks for all "
        "accounts in the cycle under Section 102 CrPC.",
        "Obtain certified bank statements for each account in the "
        "cycle covering the period of the detected transactions.",
        "Request CCTV footage from branches or ATMs used by the "
        "accounts during the transaction window.",
    ],
    "Fan-Out Distribution": [
        "Freeze the hub account and all immediate downstream "
        "accounts under Section 102 CrPC to prevent further dispersal.",
        "Request account-opening KYC documents for all receiver "
        "accounts from the respective banks.",
        "Examine whether the downstream accounts were opened within "
        "30 days of the first inward transaction — a common mule "
        "account indicator.",
    ],
    "Layering Chain": [
        "Map the full layering path and issue freeze notices to every "
        "intermediate account along the chain.",
        "Calculate net inflow and outflow per account to identify "
        "where residual funds currently sit.",
        "Coordinate with the Financial Intelligence Unit (FIU-IND) "
        "if total layered value exceeds ₹10 lakhs.",
    ],
    "Risk-Flagged Devices": [
        "Cross-reference the flagged device IDs against the CEIR "
        "(Central Equipment Identity Register) for stolen/blocked "
        "IMEI status.",
        "Collect the physical devices if accessible and send for "
        "forensic imaging under a court order.",
        "Verify device registration against the identity's KYC "
        "documents at the telecom operator.",
    ],
    "Prior Fraud Flag": [
        "Pull the previous case file(s) linked to the flagged "
        "identity and check for overlap in devices, accounts, or "
        "phone numbers.",
        "Verify whether the identity is on the NCRP (National Cyber "
        "Crime Reporting Portal) watchlist.",
        "Consider preventive detention or anticipatory bail opposition "
        "if the identity has a prior conviction.",
    ],
    "Communication Loop": [
        "Request CDR for all phones in the loop covering at least "
        "30 days prior to the incident.",
        "Plot call timestamps against transaction timestamps to "
        "establish coordination evidence.",
        "Identify the cell tower locations used during calls to "
        "establish physical proximity of the accused.",
    ],
    "New Beneficiary": [
        "Request the beneficiary addition logs from the victim's bank "
        "to confirm whether the addition was authorised.",
        "Check the IP address and device fingerprint used to add the "
        "beneficiary against known devices in the case.",
        "Initiate a chargeback or reversal request through the "
        "payment system's dispute resolution process if within the "
        "eligible window.",
    ],
}


# ---------------------------------------------------------
# PRIORITY BANDS
# ---------------------------------------------------------

def score_to_priority(score):
    """
    Convert the investigation score into a priority band.

    This is an investigation-priority classification,
    not a determination of fraud.
    """

    if score >= 60:
        return "CRITICAL"

    if score >= 40:
        return "HIGH"

    if score >= 20:
        return "MEDIUM"

    return "LOW"


# =========================================================
# EVIDENCE CONSOLIDATION
# =========================================================

def consolidate_findings(findings):
    """
    Convert raw detector output into cleaner investigator-
    facing evidence.

    The raw pattern detector may generate multiple findings
    representing the same underlying signal.

    This function:
        - keeps structural findings
        - keeps the strongest layering chain
        - aggregates risk-flagged devices
        - aggregates prior-fraud identities
        - deduplicates communication loops
        - aggregates new-beneficiary activity
    """

    if not findings:
        return []

    consolidated = []

    case_id = findings[0].get(
        "case_id"
    )

    # -----------------------------------------------------
    # 1. STRUCTURAL SIGNALS
    # -----------------------------------------------------
    #
    # These are already meaningful individual structures.
    # -----------------------------------------------------

    structural_types = {
        "Transaction Cycle",
        "Fan-Out Distribution",
        "Shared Device",
        "OTP Relay Signal",
        "Caller ID Spoof Signal",
    }

    for finding in findings:

        pattern_type = finding.get(
            "pattern_type"
        )

        if pattern_type in structural_types:

            consolidated.append(
                finding
            )

    # -----------------------------------------------------
    # 2. LAYERING CHAINS
    # -----------------------------------------------------
    #
    # The raw detector can generate overlapping paths.
    #
    # Example:
    #
    # A -> B -> C
    # A -> B -> C -> D
    # B -> C -> D
    #
    # We keep the longest chain.
    # -----------------------------------------------------

    layering_findings = [
        finding
        for finding in findings
        if finding.get(
            "pattern_type"
        ) == "Layering Chain"
    ]

    if layering_findings:

        longest_chain = max(
            layering_findings,
            key=lambda finding: len(
                finding.get(
                    "path",
                    []
                )
            ),
        )

        consolidated.append(
            longest_chain
        )

    # -----------------------------------------------------
    # 3. RISK-FLAGGED DEVICES
    # -----------------------------------------------------
    #
    # Multiple device alerts become ONE evidence item.
    # Individual device IDs remain available.
    # -----------------------------------------------------

    risk_devices = {}

    for finding in findings:

        if finding.get(
            "pattern_type"
        ) != "Risk-Flagged Device":
            continue

        device_id = finding.get(
            "device_id"
        )

        if device_id:

            risk_devices[
                device_id
            ] = finding

    if risk_devices:

        device_ids = list(
            risk_devices.keys()
        )

        identity_ids = [
            finding.get(
                "identity_id"
            )
            for finding in risk_devices.values()
            if finding.get(
                "identity_id"
            )
        ]

        device_text = ", ".join(
            device_ids
        )

        identity_text = ", ".join(
            identity_ids
        )

        consolidated.append({
            "case_id": case_id,
            "pattern_type": (
                "Risk-Flagged Devices"
            ),
            "severity": "MEDIUM",
            "entities": (
                device_ids
                + identity_ids
            ),
            "device_ids": device_ids,
            "identity_ids": identity_ids,
            "device_count": len(
                device_ids
            ),
            "evidence": [
                (
                    f"{len(device_ids)} devices "
                    "carry explicit device risk flags."
                ),
                (
                    f"Devices: {device_text}"
                ),
                (
                    "Associated identities: "
                    f"{identity_text}"
                ),
            ],
            "description": (
                f"{len(device_ids)} devices "
                "associated with the case carry "
                "explicit device risk flags."
            ),
        })

    # -----------------------------------------------------
    # 4. PRIOR-FRAUD IDENTITIES
    # -----------------------------------------------------
    #
    # Multiple prior-fraud flags become one evidence item.
    # -----------------------------------------------------

    prior_fraud_identities = {}

    for finding in findings:

        if finding.get(
            "pattern_type"
        ) != "Prior Fraud Flag":
            continue

        identity_id = finding.get(
            "identity_id"
        )

        if identity_id:

            prior_fraud_identities[
                identity_id
            ] = finding

    if prior_fraud_identities:

        identity_ids = list(
            prior_fraud_identities.keys()
        )

        identity_text = ", ".join(
            identity_ids
        )

        consolidated.append({
            "case_id": case_id,
            "pattern_type": (
                "Prior Fraud Flag"
            ),
            "severity": "MEDIUM",
            "entities": identity_ids,
            "identity_ids": identity_ids,
            "identity_count": len(
                identity_ids
            ),
            "evidence": [
                (
                    f"{len(identity_ids)} identities "
                    "have a prior-fraud flag."
                ),
                (
                    f"Identities: {identity_text}"
                ),
            ],
            "description": (
                f"{len(identity_ids)} identities "
                "associated with the case have "
                "a prior-fraud flag."
            ),
        })

    # -----------------------------------------------------
    # 5. COMMUNICATION LOOPS
    # -----------------------------------------------------
    #
    # Deduplicate loops based on their participating phones.
    # -----------------------------------------------------

    communication_loops = {}

    for finding in findings:

        if finding.get(
            "pattern_type"
        ) != "Communication Loop":
            continue

        phones = tuple(
            sorted(
                finding.get(
                    "entities",
                    []
                )
            )
        )

        if phones:

            communication_loops[
                phones
            ] = finding

    consolidated.extend(
        communication_loops.values()
    )

    # -----------------------------------------------------
    # 6. NEW BENEFICIARY ACTIVITY
    # -----------------------------------------------------
    #
    # Do NOT create one alert for every transaction.
    #
    # Instead:
    #
    #   6 transactions
    #   total amount
    #   transaction IDs
    #
    # become ONE evidence item.
    # -----------------------------------------------------

    new_beneficiary_findings = [
        finding
        for finding in findings
        if finding.get(
            "pattern_type"
        ) == "New Beneficiary"
    ]

    if new_beneficiary_findings:

        transaction_ids = []

        total_amount = 0.0

        for finding in (
            new_beneficiary_findings
        ):

            transaction_id = finding.get(
                "transaction_id"
            )

            if transaction_id:

                transaction_ids.append(
                    transaction_id
                )

            # ---------------------------------------------
            # Extract amount from detector evidence.
            # ---------------------------------------------

            for evidence in finding.get(
                "evidence",
                []
            ):

                if not isinstance(
                    evidence,
                    str,
                ):
                    continue

                if evidence.startswith(
                    "Amount: ₹"
                ):

                    value = (
                        evidence
                        .replace(
                            "Amount: ₹",
                            "",
                        )
                        .replace(
                            ",",
                            "",
                        )
                        .strip()
                    )

                    try:

                        total_amount += (
                            float(value)
                        )

                    except ValueError:
                        pass

        transaction_ids = list(
            dict.fromkeys(
                transaction_ids
            )
        )

        consolidated.append({
            "case_id": case_id,
            "pattern_type": (
                "New Beneficiary"
            ),
            "severity": "MEDIUM",
            "entities": [],
            "transaction_ids": (
                transaction_ids
            ),
            "transaction_count": len(
                new_beneficiary_findings
            ),
            "total_amount": (
                total_amount
            ),
            "evidence": [
                (
                    f"{len(new_beneficiary_findings)} "
                    "transactions used newly added "
                    "beneficiaries."
                ),
                (
                    "Transactions: "
                    + ", ".join(
                        transaction_ids
                    )
                ),
                (
                    f"Total amount: "
                    f"₹{total_amount:,.0f}"
                ),
            ],
            "description": (
                f"{len(new_beneficiary_findings)} "
                "transactions used newly added "
                "beneficiaries."
            ),
        })

    # ---------------------------------------------------------
    # Stamp recommended_actions onto every consolidated finding.
    # Each finding gets the actions for its own pattern_type.
    # ---------------------------------------------------------

    for finding in consolidated:

        pattern_type = finding.get(
            "pattern_type",
            "",
        )

        finding["recommended_actions"] = (
            RECOMMENDED_ACTIONS.get(
                pattern_type,
                [],
            )
        )

    return consolidated


# =========================================================
# SCORE CALCULATION
# =========================================================

def calculate_signal_score(findings):
    """
    Calculate the investigation score.

    Each evidence category contributes independently.

    Repeated findings from the same category are capped.
    """

    category_counts = defaultdict(
        int
    )

    for finding in findings:

        pattern_type = finding.get(
            "pattern_type"
        )

        category_counts[
            pattern_type
        ] += 1

    category_scores = {}

    for category, count in (
        category_counts.items()
    ):

        weight = SIGNAL_WEIGHTS.get(
            category,
            0,
        )

        cap = CATEGORY_CAPS.get(
            category,
            weight,
        )

        score = min(
            weight * count,
            cap,
        )

        category_scores[
            category
        ] = score

    total_score = sum(
        category_scores.values()
    )

    # Never allow the score to exceed 100.
    total_score = min(
        total_score,
        100,
    )

    return (
        total_score,
        category_scores,
    )


# =========================================================
# COMPLETE CASE SCORE
# =========================================================

def get_case_score(case_id):
    """
    Generate the complete investigation score
    for one case.
    """

    raw_findings = detect_case_patterns(
        case_id
    )

    consolidated_findings = (
        consolidate_findings(
            raw_findings
        )
    )

    score, category_scores = (
        calculate_signal_score(
            consolidated_findings
        )
    )

    priority = score_to_priority(
        score
    )

    # ---------------------------------------------------------
    # Build a deduplicated, ordered list of all recommended
    # actions across every finding in this case.
    #
    # Ordering: by signal weight (highest-weight pattern first),
    # then by position within each pattern's action list.
    # Actions that appear in multiple findings are not repeated.
    # ---------------------------------------------------------

    seen_actions = set()

    case_recommended_actions = []

    sorted_findings = sorted(
        consolidated_findings,
        key=lambda f: SIGNAL_WEIGHTS.get(
            f.get("pattern_type", ""),
            0,
        ),
        reverse=True,
    )

    for finding in sorted_findings:

        for action in finding.get(
            "recommended_actions",
            [],
        ):

            if action not in seen_actions:

                seen_actions.add(action)

                case_recommended_actions.append(
                    action
                )

    return {
        "case_id": str(
            case_id
        ),
        "score": score,
        "priority": priority,

        "raw_finding_count": len(
            raw_findings
        ),

        "consolidated_finding_count": len(
            consolidated_findings
        ),

        "category_scores": (
            category_scores
        ),

        "findings": (
            consolidated_findings
        ),

        "recommended_actions": (
            case_recommended_actions
        ),
    }


# =========================================================
# DASHBOARD-FRIENDLY SUMMARY
# =========================================================

def get_score_summary(case_id):
    """
    Return a compact structure suitable for FastAPI
    and the future React dashboard.
    """

    result = get_case_score(
        case_id
    )

    evidence_summary = []

    for finding in result[
        "findings"
    ]:

        evidence_summary.append({
            "pattern_type": finding.get(
                "pattern_type"
            ),
            "severity": finding.get(
                "severity"
            ),
            "description": finding.get(
                "description",
                "",
            ),
        })

    return {
        "case_id": result[
            "case_id"
        ],

        "investigation_score": result[
            "score"
        ],

        "priority": result[
            "priority"
        ],

        "evidence_count": result[
            "consolidated_finding_count"
        ],

        "category_scores": result[
            "category_scores"
        ],

        "evidence": evidence_summary,
    }


# =========================================================
# HUMAN-READABLE CASE REPORT
# =========================================================

def print_case_score(case_id):
    """
    Print a readable investigation summary.
    """

    result = get_case_score(
        case_id
    )

    print()
    print(
        "========================================"
    )
    print(
        "     FRAUDGRAPH INVESTIGATION SCORE"
    )
    print(
        "========================================"
    )

    print(
        f"Case ID: {result['case_id']}"
    )

    print(
        f"Investigation Score: "
        f"{result['score']}/100"
    )

    print(
        f"Priority: "
        f"{result['priority']}"
    )

    print(
        f"Raw findings: "
        f"{result['raw_finding_count']}"
    )

    print(
        f"Consolidated evidence: "
        f"{result['consolidated_finding_count']}"
    )

    print()
    print(
        "--- SIGNAL CONTRIBUTIONS ---"
    )

    sorted_scores = sorted(
        result[
            "category_scores"
        ].items(),
        key=lambda item: item[1],
        reverse=True,
    )

    for category, score in (
        sorted_scores
    ):

        print(
            f"{category:25} "
            f"+{score}"
        )

    print()
    print(
        "--- INVESTIGATIVE EVIDENCE ---"
    )

    for index, finding in enumerate(
        result["findings"],
        start=1,
    ):

        print()
        print(
            f"[{index}] "
            f"{finding.get('pattern_type')}"
        )

        print(
            f"Severity: "
            f"{finding.get('severity')}"
        )

        print(
            f"Description: "
            f"{finding.get('description', '')}"
        )

    print()
    print(
        "========================================"
    )


# =========================================================
# SHOWCASE CASE COMPARISON
# =========================================================

def compare_showcase_cases():
    """
    Display several synthetic cases to verify that the
    evidence engine behaves consistently.

    This is NOT a ranking of people or guilt.

    It is simply a development/testing view of the
    investigation-priority engine.
    """

    showcase_cases = [
        "CASE004",
        "CASE006",
        "CASE007",
        "CASE008",
        "CASE010",
    ]

    print()
    print(
        "========================================"
    )
    print(
        "       FRAUDGRAPH CASE OVERVIEW"
    )
    print(
        "========================================"
    )

    print(
        f"{'CASE':10}"
        f"{'SCORE':10}"
        f"{'PRIORITY':12}"
        f"{'EVIDENCE':10}"
    )

    print(
        "----------------------------------------"
    )

    for case_id in (
        showcase_cases
    ):

        result = get_case_score(
            case_id
        )

        print(
            f"{case_id:10}"
            f"{result['score']:10}"
            f"{result['priority']:12}"
            f"{result['consolidated_finding_count']:10}"
        )

    print(
        "========================================"
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    # Detailed CASE004 investigation.
    print_case_score(
        "CASE004"
    )

    # Showcase comparison.
    compare_showcase_cases()