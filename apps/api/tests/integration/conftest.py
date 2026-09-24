import os

import pytest


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DDQ_TEST_DATABASE_URL")
    if not url:
        pytest.skip("DDQ_TEST_DATABASE_URL is not set")
    if "supabase" in url.lower():
        pytest.fail("refusing to run destructive migration tests against a Supabase database")
    return url
