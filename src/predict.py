from pathlib import Path
from functools import lru_cache
import joblib

model_path = Path(__file__).resolve().parent.parent / "models" / "baseline.joblib"


@lru_cache(maxsize=1)
def load_model():
    return joblib.load(model_path)


def predict(text):
    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    if not text.strip():
        raise ValueError("Empty text")

    if len(text) > 10000:
        raise ValueError("Text is too long")

    if "\x00" in text:
        raise ValueError("Invalid character")

    return int(load_model().predict([text])[0])

