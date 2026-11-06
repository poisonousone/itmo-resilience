import hashlib
import json
import time
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import make_pipeline

root = Path(__file__).resolve().parent.parent


def load(name):
    df = pd.read_csv(root / "data" / f"{name}.csv")
    original_size = len(df)

    df = df.dropna(subset=["text", "label"])
    df = df[df["label"].isin([0, 1])].copy()
    df["key"] = df["text"].str.strip().str.casefold()
    df = df[df["key"].str.len().between(1, 10000)]
    df = df.drop_duplicates("key")

    print(f"{name}: {original_size} -> {len(df)}")
    return df

def baseline(train_data, test_data):
    model = DummyClassifier(strategy="most_frequent")
    model.fit(train_data[["label"]], train_data["label"])
    predictions = model.predict(test_data[["label"]])
    return float(accuracy_score(test_data["label"], predictions))


def train():
    train_data = load("train")
    val_data = load("validation")
    test_data = load("test")

    # Удаляем одинаковые тексты между выборками
    val_data = val_data[~val_data["key"].isin(test_data["key"])]
    train_data = train_data[~train_data["key"].isin(pd.concat([val_data["key"], test_data["key"]]))]

    print("После проверки пересечений:")
    print("Train:", len(train_data))
    print("Validation:", len(val_data))
    print("Test:", len(test_data))

    model = make_pipeline(
        TfidfVectorizer(max_features=20000),
        LogisticRegression(max_iter=1000, random_state=42)
    )

    start = time.time()
    model.fit(train_data["text"], train_data["label"])
    seconds = round(time.time() - start, 2)

    def evaluate(data):
        predictions = model.predict(data["text"])
        return {
            "accuracy": float(accuracy_score(data["label"], predictions)),
            "classes": classification_report(data["label"], predictions, labels=[0, 1], output_dict=True, zero_division=0),
            "matrix": confusion_matrix(data["label"], predictions, labels=[0, 1]).tolist(),
            "count": len(data)
        }

    results = {
        "seed": 42,
        "model": "TF-IDF + Logistic Regression",
        "max_features": 20000,
        "max_iter": 1000,
        "sklearn_version": sklearn.__version__,
        "training_seconds": seconds,
        "train_size": len(train_data),
        "baseline_accuracy": baseline(train_data, test_data),
        "validation": evaluate(val_data),
        "test": evaluate(test_data)
    }

    joblib.dump(model, root / "models" / "baseline.joblib")

    model_hash = hashlib.sha256((root / "models" / "baseline.joblib").read_bytes()).hexdigest()
    (root / "models" / "baseline.sha256").write_text(f"{model_hash}  baseline.joblib\n")

    results["model_sha256"] = model_hash
    results["dataset_sha256"] = {
        name: hashlib.sha256((root / "data" / f"{name}.csv").read_bytes()).hexdigest()
        for name in ["train", "validation", "test"]
    }

    (root / "metrics" / "baseline.json").write_text(json.dumps(results, indent=2))

    print("Accuracy:", round(results["test"]["accuracy"], 4))
    print("F1 INJECTION:", round(results["test"]["classes"]["1"]["f1-score"], 4))
    print("Majority baseline:", round(results["baseline_accuracy"], 4))
    print("Training time:", seconds, "s")

    return results


if __name__ == "__main__":
    train()
