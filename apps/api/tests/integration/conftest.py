import os
from urllib.parse import urlparse

import pytest

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DDQ_TEST_DATABASE_URL")
    if not url:
        if os.environ.get("DDQ_REQUIRE_INTEGRATION"):
            pytest.fail("DDQ_REQUIRE_INTEGRATION is set but DDQ_TEST_DATABASE_URL is missing")
        pytest.skip("DDQ_TEST_DATABASE_URL is not set")
    # These tests run `alembic downgrade base`: only ever against a loopback database.
    if urlparse(url).hostname not in LOCAL_HOSTS:
        pytest.fail("refusing to run destructive migration tests against a non-local database")
    return url
