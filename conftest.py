import os

import pytest


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    """CLI --base-url takes precedence over BASE_URL and the local address."""
    return (
        pytestconfig.getoption("--base-url")
        or os.environ.get("BASE_URL")
        or "http://localhost:8000/"
    )
