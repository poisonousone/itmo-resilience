import hashlib
import json
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parent.parent


def validate(df, min_rows, min_fraction):
    if set(df.columns) != {"text", "label"}:
        raise ValueError("Invalid columns")

    if len(df) < min_rows:
        raise ValueError("Not enough rows")

    if df.isna().any().any():
        raise ValueError("Missing values")

    if not df["text"].map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        raise ValueError("Invalid text")

    if not df["label"].isin([0, 1]).all():
        raise ValueError("Invalid labels")

    fractions = df["label"].value_counts(normalize=True)

    if any(fractions.get(label, 0) < min_fraction for label in [0, 1]):
        raise ValueError("Class imbalance exceeds limit")


def main():
    policy = json.loads((root / "data" / "data_policy.json").read_text())

    lines = (root / "data" / "sha256sum.txt").read_text().splitlines()
    hashes = {line.split()[1]: line.split()[0] for line in lines}

    for name, min_rows in policy["min_rows"].items():
        path = root / "data" / f"{name}.csv"
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        if actual_hash != hashes.get(f"{name}.csv"):
            raise ValueError(f"{name}: SHA256 mismatch")

        df = pd.read_csv(path)
        validate(df, min_rows, policy["min_class_fraction"])

        print(f"{name}: {len(df)} rows, SHA256 OK, data OK")


if __name__ == "__main__":
    main()

