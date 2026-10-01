"""Hello unit test module."""

from hermes_worker.hello import hello


def test_hello():
    """Test the hello function."""
    assert hello() == "Hello hermes-worker"
