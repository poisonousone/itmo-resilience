import pandas as pd
import pytest
from sklearn.metrics import f1_score

from src.data_gate import validate


def test_valid_data():
    df = pd.DataFrame({
        "text": ["hello", "world", "example", "test"],
        "label": [0, 1, 0, 1]
    })
    validate(df, 4, 0.35)


def test_invalid_schema():
    df = pd.DataFrame({"wrong_column": ["hello"]})
    with pytest.raises(ValueError):
        validate(df, 1, 0.35)


def test_invalid_label():
    df = pd.DataFrame({
        "text": ["hello", "world"],
        "label": [0, 5]
    })
    with pytest.raises(ValueError):
        validate(df, 2, 0.35)


def test_f1_calculation():
    actual = [0, 0, 1, 1]
    predicted = [0, 1, 1, 1]
    assert f1_score(actual, predicted) == pytest.approx(0.8)
