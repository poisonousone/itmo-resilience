from functools import lru_cache
from pathlib import Path

import joblib

model_path = Path(__file__).resolve().parent.parent / "models" / "baseline.joblib"


@lru_cache(maxsize=1)
def load_model():
    return joblib.load(model_path)


def validate_text(text):
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    if not text.strip():
        raise ValueError("Empty text")
    if len(text) > 10000:
        raise ValueError("Text is too long")
    if "\x00" in text:
        raise ValueError("Invalid character")
    return text


def predict(text):
    return int(load_model().predict([validate_text(text)])[0])

