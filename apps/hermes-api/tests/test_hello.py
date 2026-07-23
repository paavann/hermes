"""Hello unit test module."""

from main import hello


def test_hello():
    """Test the hello function."""
    assert hello() == "Hello hermes-api"
