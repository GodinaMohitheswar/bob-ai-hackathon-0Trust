import pandas as pd


DATA_PATH = "data/raw"


def load_data():
    identities = pd.read_csv(f"{DATA_PATH}/identities.csv")
    devices = pd.read_csv(f"{DATA_PATH}/devices.csv")
    transactions = pd.read_csv(f"{DATA_PATH}/transactions.csv")
    calls = pd.read_csv(f"{DATA_PATH}/calls.csv")

    return identities, devices, transactions, calls


def find_shared_devices(devices):
    """
    Find devices that are associated with more than one identity.
    """

    device_counts = devices.groupby("device_id")["identity_id"].nunique()

    shared_device_ids = device_counts[
        device_counts > 1
    ].index.tolist()

    return devices[
        devices["device_id"].isin(shared_device_ids)
    ]


def build_transaction_relationships(transactions):
    """
    Create account-to-account relationships from transactions.
    """

    relationships = transactions[
        [
            "sender_account",
            "receiver_account",
            "amount",
            "timestamp",
        ]
    ].copy()

    return relationships


def main():
    identities, devices, transactions, calls = load_data()

    print("\n=== DATA SUMMARY ===")
    print(f"Identities: {len(identities)}")
    print(f"Device records: {len(devices)}")
    print(f"Transactions: {len(transactions)}")
    print(f"Calls: {len(calls)}")

    print("\n=== SHARED DEVICES ===")

    shared_devices = find_shared_devices(devices)

    if shared_devices.empty:
        print("No shared devices detected.")
    else:
        print(shared_devices.to_string(index=False))

    print("\n=== TRANSACTION RELATIONSHIPS ===")

    relationships = build_transaction_relationships(transactions)

    print(relationships.to_string(index=False))


if __name__ == "__main__":
    main()