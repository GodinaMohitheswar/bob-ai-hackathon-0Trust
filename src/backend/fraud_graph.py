from pathlib import Path

import networkx as nx

from data_loader import load_all_data


# ---------------------------------------------------------
# FRAUDGRAPH - Case-Centric Network Engine
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent


def add_node(
    graph,
    node_id,
    node_type,
    **attributes,
):
    """
    Add a node to the investigation graph.
    """

    graph.add_node(
        node_id,
        type=node_type,
        **attributes,
    )


def build_case_graph(case_id: str):
    """
    Build a NetworkX graph for one investigation case.

    The graph connects:

        CASE
          |
          +-- IDENTITY
          |     +-- PHONE
          |     +-- ACCOUNT
          |     +-- DEVICE
          |
          +-- TRANSACTION
          |
          +-- CALL

    Returns:
        NetworkX MultiDiGraph
    """

    data = load_all_data()

    cases = data["cases"]
    identities = data["identities"]
    devices = data["devices"]
    transactions = data["transactions"]
    calls = data["calls"]

    case_id = str(case_id)

    # -----------------------------------------------------
    # Filter all datasets to the requested case
    # -----------------------------------------------------

    case_rows = cases[
        cases["case_id"].astype(str) == case_id
    ]

    identity_rows = identities[
        identities["case_id"].astype(str) == case_id
    ]

    device_rows = devices[
        devices["case_id"].astype(str) == case_id
    ]

    transaction_rows = transactions[
        transactions["case_id"].astype(str) == case_id
    ]

    call_rows = calls[
        calls["case_id"].astype(str) == case_id
    ]

    # -----------------------------------------------------
    # Create graph
    # -----------------------------------------------------

    graph = nx.MultiDiGraph(
        case_id=case_id
    )

    # -----------------------------------------------------
    # CASE NODE
    # -----------------------------------------------------

    if not case_rows.empty:

        case = case_rows.iloc[0]

        case_attributes = {
            "case_id": case_id,
        }

        # Add useful case-level fields if present.
        for column in [
            "pattern_type",
            "suspicious",
            "case_status",
            "city",
            "state",
        ]:
            if column in case.index:
                value = case[column]

                if value == value:
                    case_attributes[column] = value

        add_node(
            graph,
            case_id,
            "case",
            **case_attributes,
        )

    else:
        add_node(
            graph,
            case_id,
            "case",
        )

    # -----------------------------------------------------
    # IDENTITY NODES
    # -----------------------------------------------------

    for _, row in identity_rows.iterrows():

        identity_id = str(row["identity_id"])

        add_node(
            graph,
            identity_id,
            "identity",
            case_id=case_id,
            name=row.get("name"),
            role=row.get("role"),
            mule_level=row.get("mule_level"),
            phone=row.get("phone"),
            account_id=row.get("account_id"),
            address_city=row.get("address_city"),
            address_state=row.get("address_state"),
            kyc_status=row.get("kyc_status"),
            prior_fraud_flag=row.get(
                "prior_fraud_flag",
                False,
            ),
        )

        # CASE -> IDENTITY
        graph.add_edge(
            case_id,
            identity_id,
            relationship="contains_identity",
        )

        # -------------------------------------------------
        # PHONE NODE
        # -------------------------------------------------

        phone = row.get("phone")

        if phone and str(phone) != "nan":

            phone = str(phone)

            add_node(
                graph,
                phone,
                "phone",
                case_id=case_id,
            )

            graph.add_edge(
                identity_id,
                phone,
                relationship="has_phone",
            )

        # -------------------------------------------------
        # ACCOUNT NODE
        # -------------------------------------------------

        account_id = row.get("account_id")

        if account_id and str(account_id) != "nan":

            account_id = str(account_id)

            add_node(
                graph,
                account_id,
                "account",
                case_id=case_id,
            )

            graph.add_edge(
                identity_id,
                account_id,
                relationship="owns_account",
            )

    # -----------------------------------------------------
    # DEVICE NODES
    # -----------------------------------------------------

    for _, row in device_rows.iterrows():

        device_id = str(row["device_id"])
        identity_id = str(row["identity_id"])

        add_node(
            graph,
            device_id,
            "device",
            case_id=case_id,
            device_type=row.get("device_type"),
            telecom_circle=row.get("telecom_circle"),
            device_risk_flag=row.get(
                "device_risk_flag",
                False,
            ),
        )

        # IDENTITY -> DEVICE
        graph.add_edge(
            identity_id,
            device_id,
            relationship="uses_device",
        )

    # -----------------------------------------------------
    # TRANSACTION NODES + EDGES
    # -----------------------------------------------------

    for _, row in transaction_rows.iterrows():

        transaction_id = str(
            row["transaction_id"]
        )

        sender = str(row["sender_account"])
        receiver = str(row["receiver_account"])

        # Transaction itself becomes an evidence node.
        add_node(
            graph,
            transaction_id,
            "transaction",
            case_id=case_id,
            amount=float(row["amount"]),
            channel=row.get("channel"),
            status=row.get("status"),
            is_new_beneficiary=row.get(
                "is_new_beneficiary",
                False,
            ),
            is_fraudulent=row.get(
                "is_fraudulent",
                False,
            ),
            originating_device_id=row.get(
                "originating_device_id"
            ),
            originating_ip=row.get(
                "originating_ip"
            ),
            linked_complaint_id=row.get(
                "linked_complaint_id"
            ),
        )

        # Make sure account nodes exist.
        add_node(
            graph,
            sender,
            "account",
            case_id=case_id,
        )

        add_node(
            graph,
            receiver,
            "account",
            case_id=case_id,
        )

        # ACCOUNT -> TRANSACTION
        graph.add_edge(
            sender,
            transaction_id,
            relationship="sent_transaction",
        )

        # TRANSACTION -> ACCOUNT
        graph.add_edge(
            transaction_id,
            receiver,
            relationship="received_by",
        )

        # Direct ACCOUNT -> ACCOUNT relationship.
        graph.add_edge(
            sender,
            receiver,
            relationship="transaction",
            transaction_id=transaction_id,
            amount=float(row["amount"]),
            channel=row.get("channel"),
            status=row.get("status"),
            is_new_beneficiary=row.get(
                "is_new_beneficiary",
                False,
            ),
        )

        # TRANSACTION -> DEVICE
        originating_device = row.get(
            "originating_device_id"
        )

        if (
            originating_device
            and str(originating_device) != "nan"
        ):

            originating_device = str(
                originating_device
            )

            add_node(
                graph,
                originating_device,
                "device",
                case_id=case_id,
            )

            graph.add_edge(
                transaction_id,
                originating_device,
                relationship="originated_on",
            )

    # -----------------------------------------------------
    # CALL NODES + EDGES
    # -----------------------------------------------------

    for _, row in call_rows.iterrows():

        call_id = str(row["call_id"])

        caller = str(row["caller"])
        receiver = str(row["receiver"])

        add_node(
            graph,
            call_id,
            "call",
            case_id=case_id,
            duration_seconds=int(
                row["duration_seconds"]
            ),
            call_type=row.get("call_type"),
            device_id_used=row.get(
                "device_id_used"
            ),
            cell_location=row.get(
                "cell_location"
            ),
            caller_id_spoof_suspected=row.get(
                "caller_id_spoof_suspected",
                False,
            ),
        )

        # Make sure phone nodes exist.
        add_node(
            graph,
            caller,
            "phone",
            case_id=case_id,
        )

        add_node(
            graph,
            receiver,
            "phone",
            case_id=case_id,
        )

        # PHONE -> CALL
        graph.add_edge(
            caller,
            call_id,
            relationship="made_call",
        )

        # CALL -> PHONE
        graph.add_edge(
            call_id,
            receiver,
            relationship="received_call",
        )

        # Direct PHONE -> PHONE communication edge.
        graph.add_edge(
            caller,
            receiver,
            relationship="call",
            call_id=call_id,
            duration_seconds=int(
                row["duration_seconds"]
            ),
            call_type=row.get("call_type"),
            cell_location=row.get(
                "cell_location"
            ),
            caller_id_spoof_suspected=row.get(
                "caller_id_spoof_suspected",
                False,
            ),
        )

        # CALL -> DEVICE
        device_id = row.get("device_id_used")

        if (
            device_id
            and str(device_id) != "nan"
        ):

            device_id = str(device_id)

            add_node(
                graph,
                device_id,
                "device",
                case_id=case_id,
            )

            graph.add_edge(
                call_id,
                device_id,
                relationship="used_device",
            )

    return graph


def get_graph_summary(graph):
    """
    Return a compact summary of a case graph.
    """

    node_types = {}

    for _, attributes in graph.nodes(
        data=True
    ):

        node_type = attributes.get(
            "type",
            "unknown",
        )

        node_types[node_type] = (
            node_types.get(node_type, 0) + 1
        )

    relationship_counts = {}

    for _, _, attributes in graph.edges(
        data=True
    ):

        relationship = attributes.get(
            "relationship",
            "unknown",
        )

        relationship_counts[relationship] = (
            relationship_counts.get(
                relationship,
                0,
            )
            + 1
        )

    return {
        "case_id": graph.graph.get(
            "case_id"
        ),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "node_types": node_types,
        "relationship_types": relationship_counts,
    }


def print_graph_summary(case_id):
    """
    Print a human-readable graph summary.
    """

    graph = build_case_graph(case_id)

    summary = get_graph_summary(graph)

    print("\n========================================")
    print("       FRAUDGRAPH CASE NETWORK")
    print("========================================")

    print(
        f"Case ID: {summary['case_id']}"
    )

    print(
        f"Nodes:   {summary['nodes']}"
    )

    print(
        f"Edges:   {summary['edges']}"
    )

    print("\n--- NODE TYPES ---")

    for node_type, count in sorted(
        summary["node_types"].items()
    ):
        print(
            f"{node_type:15} {count}"
        )

    print("\n--- RELATIONSHIPS ---")

    for relationship, count in sorted(
        summary["relationship_types"].items()
    ):
        print(
            f"{relationship:20} {count}"
        )

    print("\n--- SAMPLE NODES ---")

    for node, attributes in list(
        graph.nodes(data=True)
    )[:15]:

        print(
            f"{node} -> "
            f"{attributes.get('type')}"
        )

    print("\n========================================")


if __name__ == "__main__":

    # CASE004 is deliberately used because
    # it contains strong cross-source signals:
    #
    # shared device
    # OTP relay
    # device risk flags
    # transaction chain
    # identity hierarchy

    print_graph_summary("CASE004")