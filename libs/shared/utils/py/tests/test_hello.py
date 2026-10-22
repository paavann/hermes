"""Hello unit test module."""

from utils_py.hello import hello


def test_hello():
    """Test the hello function."""
    assert hello() == "Hello utils-py"
