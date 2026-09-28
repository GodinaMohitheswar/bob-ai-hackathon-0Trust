from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# FRAUDGRAPH - Unified Data Loader
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"


REQUIRED_COLUMNS = {
    "cases": [
        "case_id",
    ],
    "identities": [
        "case_id",
        "identity_id",
        "name",
        "phone",
        "account_id",
        "role",
        "mule_level",
        "address_city",
        "address_state",
        "police_station_jurisdiction",
        "kyc_status",
        "prior_fraud_flag",
    ],
    "devices": [
        "case_id",
        "device_id",
        "identity_id",
        "device_type",
        "telecom_circle",
        "device_risk_flag",
    ],
    "transactions": [
        "case_id",
        "transaction_id",
        "sender_account",
        "receiver_account",
        "amount",
        "channel",
        "status",
        "originating_device_id",
        "is_new_beneficiary",
        "is_fraudulent",
    ],
    "calls": [
        "case_id",
        "call_id",
        "timestamp",
        "caller",
        "receiver",
        "duration_seconds",
        "call_type",
        "device_id_used",
        "cell_location",
        "caller_id_spoof_suspected",
    ],
}


def load_csv(filename: str) -> pd.DataFrame:
    """
    Load a CSV file from data/raw.
    """
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    return pd.read_csv(path)


def validate_columns(
    dataframe: pd.DataFrame,
    dataset_name: str,
) -> None:
    """
    Check that the dataset contains the columns
    required by FRAUDGRAPH.
    """

    required = REQUIRED_COLUMNS[dataset_name]

    missing = [
        column
        for column in required
        if column not in dataframe.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset_name}.csv is missing required columns: "
            f"{missing}"
        )


def load_all_data():
    """
    Load and validate all FRAUDGRAPH datasets.

    Returns:
        dict containing:
            cases
            identities
            devices
            transactions
            calls
    """

    cases = load_csv("cases.csv")
    identities = load_csv("identities.csv")
    devices = load_csv("devices.csv")
    transactions = load_csv("transactions.csv")
    calls = load_csv("calls.csv")

    validate_columns(cases, "cases")
    validate_columns(identities, "identities")
    validate_columns(devices, "devices")
    validate_columns(transactions, "transactions")
    validate_columns(calls, "calls")

    # -----------------------------------------------------
    # Basic type cleanup
    # -----------------------------------------------------

    identities["mule_level"] = pd.to_numeric(
        identities["mule_level"],
        errors="coerce",
    )

    identities["prior_fraud_flag"] = (
        identities["prior_fraud_flag"]
        .astype(str)
        .str.upper()
        .eq("TRUE")
    )

    devices["device_risk_flag"] = (
        devices["device_risk_flag"]
        .astype(str)
        .str.upper()
        .eq("TRUE")
    )

    transactions["amount"] = pd.to_numeric(
        transactions["amount"],
        errors="coerce",
    )

    transactions["is_new_beneficiary"] = (
        transactions["is_new_beneficiary"]
        .astype(str)
        .str.upper()
        .eq("TRUE")
    )

    transactions["is_fraudulent"] = (
        transactions["is_fraudulent"]
        .astype(str)
        .str.upper()
        .eq("TRUE")
    )

    calls["duration_seconds"] = pd.to_numeric(
        calls["duration_seconds"],
        errors="coerce",
    )

    calls["caller_id_spoof_suspected"] = (
        calls["caller_id_spoof_suspected"]
        .astype(str)
        .str.upper()
        .eq("TRUE")
    )

    # Calls contain usable timestamps in the supplied dataset.
    calls["timestamp"] = pd.to_datetime(
        calls["timestamp"],
        dayfirst=True,
        errors="coerce",
    )

    return {
        "cases": cases,
        "identities": identities,
        "devices": devices,
        "transactions": transactions,
        "calls": calls,
    }


def get_case_data(case_id: str):
    """
    Return all available information associated with
    a specific case.

    Missing source records are returned as empty
    DataFrames rather than being fabricated.
    """

    data = load_all_data()

    result = {}

    for dataset_name, dataframe in data.items():
        if "case_id" in dataframe.columns:
            result[dataset_name] = dataframe[
                dataframe["case_id"].astype(str) == str(case_id)
            ].copy()
        else:
            result[dataset_name] = dataframe.copy()

    return result


def get_case_ids():
    """
    Return all case IDs from the cases dataset.
    """

    data = load_all_data()

    return (
        data["cases"]["case_id"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )


def print_data_summary():
    """
    Print a useful summary of the loaded datasets.
    """

    data = load_all_data()

    print("\n========================================")
    print("        FRAUDGRAPH DATA SUMMARY")
    print("========================================")

    for dataset_name, dataframe in data.items():
        print(
            f"{dataset_name.capitalize():15} "
            f"{len(dataframe):5} rows | "
            f"{len(dataframe.columns):3} columns"
        )

    print("----------------------------------------")

    print(
        "Unique cases:    ",
        data["cases"]["case_id"].nunique()
    )

    print(
        "Identity cases:  ",
        data["identities"]["case_id"].nunique()
    )

    print(
        "Device cases:    ",
        data["devices"]["case_id"].nunique()
    )

    print(
        "Transaction cases:",
        data["transactions"]["case_id"].nunique()
    )

    print(
        "Call cases:      ",
        data["calls"]["case_id"].nunique()
    )

    print("========================================\n")


if __name__ == "__main__":
    print_data_summary()

    print("First 10 case IDs:")

    for case_id in get_case_ids()[:10]:
        print(f"  - {case_id}")

    print("\nData loader test completed successfully.")