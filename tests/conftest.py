import pytest


@pytest.fixture
def temp_dir(tmp_path):
    """Compatibility alias used by the upstream tests we ported."""
    return tmp_path
