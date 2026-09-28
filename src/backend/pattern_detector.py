from collections import defaultdict

import pandas as pd
import networkx as nx

from data_loader import load_all_data
from fraud_graph import build_case_graph


# ---------------------------------------------------------
# FRAUDGRAPH - Pattern Detection Engine
# ---------------------------------------------------------


def detect_shared_devices(devices, case_id):
    """
    Detect devices associated with more than one identity
    within the same case.

    This is a strong SIM/device-sharing investigation signal.
    """

    case_devices = devices[
        devices["case_id"].astype(str) == str(case_id)
    ].copy()

    findings = []

    grouped = case_devices.groupby("device_id")

    for device_id, group in grouped:

        identities = (
            group["identity_id"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        if len(identities) > 1:

            findings.append({
                "case_id": str(case_id),
                "pattern_type": "Shared Device",
                "severity": "HIGH",
                "entities": identities,
                "evidence": [
                    f"Device {device_id} is associated with "
                    f"{len(identities)} identities."
                ],
                "device_id": str(device_id),
                "identities": identities,
                "description": (
                    f"Device {device_id} is linked to multiple "
                    f"identities: {', '.join(identities)}."
                ),
            })

    return findings


def detect_device_risk_flags(devices, case_id):
    """
    Detect explicitly risk-flagged devices.

    This is evidence from the dataset, not a prediction.
    """

    case_devices = devices[
        devices["case_id"].astype(str) == str(case_id)
    ].copy()

    case_devices = case_devices[
        case_devices["device_risk_flag"] == True
    ]

    findings = []

    for _, row in case_devices.iterrows():

        findings.append({
            "case_id": str(case_id),
            "pattern_type": "Risk-Flagged Device",
            "severity": "MEDIUM",
            "entities": [
                str(row["identity_id"]),
                str(row["device_id"]),
            ],
            "evidence": [
                f"Device {row['device_id']} is explicitly "
                f"marked with device_risk_flag=True."
            ],
            "device_id": str(row["device_id"]),
            "identity_id": str(row["identity_id"]),
            "description": (
                f"Device {row['device_id']} associated with "
                f"{row['identity_id']} carries a device risk flag."
            ),
        })

    return findings


def detect_prior_fraud_identities(identities, case_id):
    """
    Detect identities with prior_fraud_flag=True.

    This is a contextual investigation signal.
    """

    case_identities = identities[
        identities["case_id"].astype(str) == str(case_id)
    ].copy()

    case_identities = case_identities[
        case_identities["prior_fraud_flag"] == True
    ]

    findings = []

    for _, row in case_identities.iterrows():

        findings.append({
            "case_id": str(case_id),
            "pattern_type": "Prior Fraud Flag",
            "severity": "MEDIUM",
            "entities": [
                str(row["identity_id"]),
            ],
            "evidence": [
                f"Identity {row['identity_id']} has "
                f"prior_fraud_flag=True."
            ],
            "identity_id": str(row["identity_id"]),
            "description": (
                f"Identity {row['identity_id']} has a prior "
                f"fraud flag in the supplied investigation data."
            ),
        })

    return findings


def detect_fan_out(transactions, case_id):
    """
    Detect one account sending money to multiple downstream
    accounts.

    Example:

        A -> B
        A -> C
        A -> D

    This can indicate fan-out distribution.
    """

    case_transactions = transactions[
        transactions["case_id"].astype(str) == str(case_id)
    ].copy()

    findings = []

    grouped = (
        case_transactions
        .groupby("sender_account")["receiver_account"]
        .unique()
    )

    for sender, receivers in grouped.items():

        receivers = [
            str(receiver)
            for receiver in receivers
            if str(receiver) != "nan"
        ]

        if len(receivers) >= 2:

            transaction_ids = case_transactions[
                case_transactions["sender_account"] == sender
            ]["transaction_id"].astype(str).tolist()

            findings.append({
                "case_id": str(case_id),
                "pattern_type": "Fan-Out Distribution",
                "severity": "HIGH",
                "entities": [
                    str(sender),
                    *receivers,
                ],
                "evidence": [
                    f"Account {sender} sends funds to "
                    f"{len(receivers)} different accounts.",
                    f"Receivers: {', '.join(receivers)}",
                    f"Transactions: {', '.join(transaction_ids)}",
                ],
                "source_account": str(sender),
                "destination_accounts": receivers,
                "transaction_ids": transaction_ids,
                "description": (
                    f"Account {sender} distributes funds across "
                    f"{len(receivers)} downstream accounts."
                ),
            })

    return findings


def detect_layering_chains(transactions, case_id):
    """
    Detect transaction chains where money moves through
    multiple accounts.

    Example:

        A -> B -> C -> D -> E
    """

    case_transactions = transactions[
        transactions["case_id"].astype(str) == str(case_id)
    ].copy()

    graph = nx.DiGraph()

    for _, row in case_transactions.iterrows():

        sender = str(row["sender_account"])
        receiver = str(row["receiver_account"])

        graph.add_edge(
            sender,
            receiver,
            transaction_id=str(row["transaction_id"]),
            amount=float(row["amount"]),
        )

    findings = []

    # Look for directed paths of length >= 3 edges.
    for source in graph.nodes:

        for target in graph.nodes:

            if source == target:
                continue

            try:
                paths = nx.all_simple_paths(
                    graph,
                    source=source,
                    target=target,
                    cutoff=5,
                )

                for path in paths:

                    if len(path) < 4:
                        continue

                    transaction_ids = []

                    for index in range(len(path) - 1):

                        edge_data = graph.get_edge_data(
                            path[index],
                            path[index + 1],
                        )

                        if edge_data:
                            transaction_ids.append(
                                edge_data["transaction_id"]
                            )

                    findings.append({
                        "case_id": str(case_id),
                        "pattern_type": "Layering Chain",
                        "severity": "HIGH",
                        "entities": path,
                        "evidence": [
                            "Multi-hop transaction path detected.",
                            "Path: " + " → ".join(path),
                            (
                                "Transactions: "
                                + ", ".join(transaction_ids)
                            ),
                        ],
                        "path": path,
                        "transaction_ids": transaction_ids,
                        "description": (
                            "Funds move through multiple "
                            "intermediary accounts: "
                            + " → ".join(path)
                        ),
                    })

            except nx.NetworkXNoPath:
                continue

    # Remove duplicate paths.
    unique = []
    seen = set()

    for finding in findings:

        key = tuple(finding["path"])

        if key not in seen:
            seen.add(key)
            unique.append(finding)

    return unique


def detect_transaction_cycles(transactions, case_id):
    """
    Detect circular transaction paths.

    Example:

        A -> B -> C -> A
    """

    case_transactions = transactions[
        transactions["case_id"].astype(str) == str(case_id)
    ].copy()

    graph = nx.DiGraph()

    for _, row in case_transactions.iterrows():

        sender = str(row["sender_account"])
        receiver = str(row["receiver_account"])

        graph.add_edge(
            sender,
            receiver,
            transaction_id=str(row["transaction_id"]),
        )

    findings = []

    try:
        cycles = list(nx.simple_cycles(graph))
    except nx.NetworkXError:
        cycles = []

    for cycle in cycles:

        if len(cycle) < 3:
            continue

        # Normalize cycle so rotations are not duplicated.
        rotations = [
            tuple(
                cycle[index:] + cycle[:index]
            )
            for index in range(len(cycle))
        ]

        normalized = min(rotations)

        transaction_ids = []

        for index in range(len(cycle)):

            source = cycle[index]
            target = cycle[
                (index + 1) % len(cycle)
            ]

            edge_data = graph.get_edge_data(
                source,
                target,
            )

            if edge_data:
                transaction_ids.append(
                    edge_data["transaction_id"]
                )

        findings.append({
            "case_id": str(case_id),
            "pattern_type": "Transaction Cycle",
            "severity": "HIGH",
            "entities": list(normalized),
            "evidence": [
                "Circular transaction path detected.",
                (
                    "Cycle: "
                    + " → ".join(normalized)
                    + " → "
                    + normalized[0]
                ),
                (
                    "Transactions: "
                    + ", ".join(transaction_ids)
                ),
            ],
            "cycle": list(normalized),
            "transaction_ids": transaction_ids,
            "description": (
                "A circular flow of funds was detected: "
                + " → ".join(normalized)
                + " → "
                + normalized[0]
            ),
        })

    return findings


def detect_new_beneficiary_activity(
    transactions,
    case_id,
):
    """
    Detect transactions involving newly added beneficiaries.

    Multiple such transactions can be an investigation signal.
    """

    case_transactions = transactions[
        transactions["case_id"].astype(str) == str(case_id)
    ].copy()

    case_transactions = case_transactions[
        case_transactions["is_new_beneficiary"] == True
    ]

    if case_transactions.empty:
        return []

    findings = []

    for _, row in case_transactions.iterrows():

        findings.append({
            "case_id": str(case_id),
            "pattern_type": "New Beneficiary",
            "severity": "MEDIUM",
            "entities": [
                str(row["sender_account"]),
                str(row["receiver_account"]),
            ],
            "evidence": [
                (
                    f"Transaction {row['transaction_id']} "
                    "uses a newly added beneficiary."
                ),
                (
                    f"Amount: ₹{float(row['amount']):,.0f}"
                ),
                (
                    f"Channel: {row['channel']}"
                ),
            ],
            "transaction_id": str(
                row["transaction_id"]
            ),
            "description": (
                f"Transaction {row['transaction_id']} "
                f"from {row['sender_account']} to "
                f"{row['receiver_account']} used a "
                "new beneficiary."
            ),
        })

    return findings


def detect_otp_relay_calls(calls, case_id):
    """
    Detect calls explicitly marked as OTP relay.
    """

    case_calls = calls[
        calls["case_id"].astype(str) == str(case_id)
    ].copy()

    case_calls = case_calls[
        case_calls["call_type"]
        .astype(str)
        .str.lower()
        .eq("otp_relay")
    ]

    findings = []

    for _, row in case_calls.iterrows():

        findings.append({
            "case_id": str(case_id),
            "pattern_type": "OTP Relay Signal",
            "severity": "HIGH",
            "entities": [
                str(row["caller"]),
                str(row["receiver"]),
                str(row["device_id_used"]),
            ],
            "evidence": [
                (
                    f"Call {row['call_id']} is marked "
                    "as otp_relay."
                ),
                (
                    f"Device: {row['device_id_used']}"
                ),
                (
                    f"Location: {row['cell_location']}"
                ),
            ],
            "call_id": str(row["call_id"]),
            "device_id": str(
                row["device_id_used"]
            ),
            "description": (
                f"OTP relay communication detected "
                f"between {row['caller']} and "
                f"{row['receiver']}."
            ),
        })

    return findings


def detect_spoof_suspected_calls(calls, case_id):
    """
    Detect calls explicitly marked as caller-ID spoof
    suspected.
    """

    case_calls = calls[
        calls["case_id"].astype(str) == str(case_id)
    ].copy()

    case_calls = case_calls[
        case_calls["caller_id_spoof_suspected"] == True
    ]

    findings = []

    for _, row in case_calls.iterrows():

        findings.append({
            "case_id": str(case_id),
            "pattern_type": "Caller ID Spoof Signal",
            "severity": "HIGH",
            "entities": [
                str(row["caller"]),
                str(row["receiver"]),
            ],
            "evidence": [
                (
                    f"Call {row['call_id']} has "
                    "caller_id_spoof_suspected=True."
                ),
                (
                    f"Device: {row['device_id_used']}"
                ),
            ],
            "call_id": str(row["call_id"]),
            "description": (
                f"Caller-ID spoofing is explicitly "
                f"flagged for call {row['call_id']}."
            ),
        })

    return findings


def detect_call_loops(calls, case_id):
    """
    Detect simple communication loops such as:

        A -> B
        B -> C
        C -> A
    """

    case_calls = calls[
        calls["case_id"].astype(str) == str(case_id)
    ].copy()

    graph = nx.DiGraph()

    for _, row in case_calls.iterrows():

        caller = str(row["caller"])
        receiver = str(row["receiver"])

        graph.add_edge(
            caller,
            receiver,
            call_id=str(row["call_id"]),
        )

    findings = []

    try:
        cycles = list(nx.simple_cycles(graph))
    except nx.NetworkXError:
        cycles = []

    for cycle in cycles:

        if len(cycle) < 3:
            continue

        findings.append({
            "case_id": str(case_id),
            "pattern_type": "Communication Loop",
            "severity": "MEDIUM",
            "entities": cycle,
            "evidence": [
                (
                    "A circular communication path was detected: "
                    + " → ".join(cycle)
                    + " → "
                    + cycle[0]
                )
            ],
            "cycle": cycle,
            "description": (
                "A circular communication relationship "
                "exists among "
                + ", ".join(cycle)
                + "."
            ),
        })

    return findings


def detect_case_patterns(case_id):
    """
    Run all independent pattern detectors for a case.

    Ground-truth fields such as is_fraudulent and the
    case pattern label are NOT used to create findings.
    """

    data = load_all_data()

    findings = []

    findings.extend(
        detect_shared_devices(
            data["devices"],
            case_id,
        )
    )

    findings.extend(
        detect_device_risk_flags(
            data["devices"],
            case_id,
        )
    )

    findings.extend(
        detect_prior_fraud_identities(
            data["identities"],
            case_id,
        )
    )

    findings.extend(
        detect_fan_out(
            data["transactions"],
            case_id,
        )
    )

    findings.extend(
        detect_layering_chains(
            data["transactions"],
            case_id,
        )
    )

    findings.extend(
        detect_transaction_cycles(
            data["transactions"],
            case_id,
        )
    )

    findings.extend(
        detect_new_beneficiary_activity(
            data["transactions"],
            case_id,
        )
    )

    findings.extend(
        detect_otp_relay_calls(
            data["calls"],
            case_id,
        )
    )

    findings.extend(
        detect_spoof_suspected_calls(
            data["calls"],
            case_id,
        )
    )

    findings.extend(
        detect_call_loops(
            data["calls"],
            case_id,
        )
    )

    return findings


def summarize_findings(findings):
    """
    Create a compact summary of pattern findings.
    """

    severity_counts = defaultdict(int)
    pattern_counts = defaultdict(int)

    for finding in findings:

        severity = finding.get(
            "severity",
            "UNKNOWN",
        )

        pattern = finding.get(
            "pattern_type",
            "Unknown",
        )

        severity_counts[severity] += 1
        pattern_counts[pattern] += 1

    return {
        "total_findings": len(findings),
        "severity_counts": dict(
            severity_counts
        ),
        "pattern_counts": dict(
            pattern_counts
        ),
    }


def print_case_analysis(case_id):
    """
    Run and print the complete pattern analysis.
    """

    findings = detect_case_patterns(case_id)

    summary = summarize_findings(findings)

    print("\n========================================")
    print("       FRAUDGRAPH PATTERN ANALYSIS")
    print("========================================")

    print(f"Case ID: {case_id}")

    print(
        f"Total findings: "
        f"{summary['total_findings']}"
    )

    print("\n--- SEVERITY SUMMARY ---")

    for severity, count in sorted(
        summary["severity_counts"].items()
    ):
        print(
            f"{severity:10} {count}"
        )

    print("\n--- PATTERN SUMMARY ---")

    for pattern, count in sorted(
        summary["pattern_counts"].items()
    ):
        print(
            f"{pattern:25} {count}"
        )

    print("\n--- FINDINGS ---")

    for index, finding in enumerate(
        findings,
        start=1,
    ):

        print(
            f"\n[{index}] "
            f"{finding['pattern_type']}"
        )

        print(
            f"Severity: "
            f"{finding['severity']}"
        )

        print(
            f"Description: "
            f"{finding['description']}"
        )

        if finding.get("evidence"):

            print("Evidence:")

            for evidence in finding[
                "evidence"
            ]:
                print(
                    f"  - {evidence}"
                )

    print("\n========================================")


if __name__ == "__main__":

    # Showcase cases selected because they
    # demonstrate different fraud structures.
    showcase_cases = [
        "CASE004",
        "CASE006",
        "CASE007",
        "CASE008",
        "CASE010",
    ]

    for case_id in showcase_cases:

        print_case_analysis(case_id)