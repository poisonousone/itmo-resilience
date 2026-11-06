import pytest
from src.predict import predict


def test_wrong_type():
    with pytest.raises(TypeError):
        predict(123)


def test_empty():
    with pytest.raises(ValueError):
        predict("")


def test_too_long():
    with pytest.raises(ValueError):
        predict("a" * 10001)


def test_invalid_character():
    with pytest.raises(ValueError):
        predict("hello\x00world")


def test_valid():
    assert predict("What is machine learning?") in [0, 1]

