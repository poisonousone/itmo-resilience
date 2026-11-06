import hashlib
import json
import math
import sys
from pathlib import Path

import joblib
from sklearn.metrics import f1_score

from src.train import load

root = Path(__file__).resolve().parent.parent


def main():
    baseline = json.loads((root / "metrics" / "baseline.json").read_text())

    for name in ["train", "validation", "test"]:
        path = root / "data" / f"{name}.csv"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != baseline["dataset_sha256"][name]:
            raise ValueError("Dataset version mismatch")

    validation = load("validation")
    test = load("test")
    validation = validation[~validation["key"].isin(test["key"])]

    if len(validation) != baseline["validation"]["count"]:
        raise ValueError("Validation set changed")

    path = root / "models" / "baseline.joblib"
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    saved_hash = (root / "models" / "baseline.sha256").read_text().split()[0]

    if actual_hash != saved_hash or actual_hash != baseline["model_sha256"]:
        raise ValueError("Model SHA256 mismatch")

    if "--demo-weak" in sys.argv:
        predictions = [0] * len(validation)
    else:
        model = joblib.load(path)
        predictions = model.predict(validation["text"])

    score = f1_score(validation["label"], predictions, pos_label=1, zero_division=0)
    reference = baseline["validation"]["classes"]["1"]["f1-score"]
    threshold = reference * 0.95

    print(f"Baseline F1: {reference:.4f}")
    print(f"Candidate F1: {score:.4f}")
    print(f"Threshold: {threshold:.4f}")

    if not math.isfinite(score) or score < threshold:
        raise SystemExit("FAILED: model quality gate")

    print("PASSED: model quality gate")


if __name__ == "__main__":
    main()

