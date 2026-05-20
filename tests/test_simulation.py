"""Tests for simulation endpoints: /flaky, /async, and /rabbit."""
import time

import pytest
import requests

BASE_URL = "http://localhost:8001"


# ---------------------------------------------------------------------------
# GET /flaky
# ---------------------------------------------------------------------------

def test_flaky_returns_valid_status_code():
    r = requests.get(f"{BASE_URL}/flaky")
    assert r.status_code in (200, 503)


def test_flaky_200_body_is_hello_world():
    for _ in range(20):
        r = requests.get(f"{BASE_URL}/flaky")
        if r.status_code == 200:
            assert r.text == "Hello world!"
            return
    pytest.skip("Did not receive a 200 in 20 attempts — run again.")


def test_flaky_503_has_detail():
    for _ in range(20):
        r = requests.get(f"{BASE_URL}/flaky")
        if r.status_code == 503:
            assert "detail" in r.json()
            return
    pytest.skip("Did not receive a 503 in 20 attempts — run again.")


def test_flaky_succeeds_eventually_within_retry_budget():
    """Illustrates retry logic: eventually get a 200 within a reasonable budget."""
    for attempt in range(10):
        r = requests.get(f"{BASE_URL}/flaky")
        if r.status_code == 200:
            assert r.text == "Hello world!"
            return
    pytest.fail("Never received 200 in 10 attempts (p≈0.000017 if endpoint is correct).")


def test_flaky_both_outcomes_observed_across_sample():
    """Over many calls both 200 and 503 must appear — neither is impossible."""
    statuses = {requests.get(f"{BASE_URL}/flaky").status_code for _ in range(30)}
    assert 200 in statuses, "Expected at least one 200 in 30 calls"
    assert 503 in statuses, "Expected at least one 503 in 30 calls"


# ---------------------------------------------------------------------------
# POST /async  +  GET /async/{job_id}
# ---------------------------------------------------------------------------

def test_start_async_job_returns_202():
    r = requests.post(f"{BASE_URL}/async")
    assert r.status_code == 202


def test_start_async_job_body_has_job_id_and_pending_status():
    data = requests.post(f"{BASE_URL}/async").json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert data["result"] is None


def test_start_async_job_ids_are_unique():
    ids = {requests.post(f"{BASE_URL}/async").json()["job_id"] for _ in range(5)}
    assert len(ids) == 5


def test_poll_unknown_job_returns_404():
    r = requests.get(f"{BASE_URL}/async/no-such-job-id")
    assert r.status_code == 404


def test_poll_first_two_calls_are_pending():
    job_id = requests.post(f"{BASE_URL}/async").json()["job_id"]
    for _ in range(2):
        data = requests.get(f"{BASE_URL}/async/{job_id}").json()
        assert data["status"] == "pending"
        assert data["result"] is None


def test_third_poll_returns_complete_with_result():
    job_id = requests.post(f"{BASE_URL}/async").json()["job_id"]
    requests.get(f"{BASE_URL}/async/{job_id}")
    requests.get(f"{BASE_URL}/async/{job_id}")
    data = requests.get(f"{BASE_URL}/async/{job_id}").json()
    assert data["status"] == "complete"
    assert data["result"] == 42


def test_poll_loop_until_complete():
    """Illustrates the canonical polling pattern: keep polling until done."""
    job_id = requests.post(f"{BASE_URL}/async").json()["job_id"]
    deadline = time.time() + 5
    while time.time() < deadline:
        data = requests.get(f"{BASE_URL}/async/{job_id}").json()
        if data["status"] == "complete":
            assert data["result"] == 42
            return
        time.sleep(0.1)
    pytest.fail("Job did not reach 'complete' within timeout.")


def test_poll_response_includes_job_id():
    job_id = requests.post(f"{BASE_URL}/async").json()["job_id"]
    data = requests.get(f"{BASE_URL}/async/{job_id}").json()
    assert data["job_id"] == job_id


# ---------------------------------------------------------------------------
# GET /rabbit/{n}
# ---------------------------------------------------------------------------

def test_rabbit_one():
    data = requests.get(f"{BASE_URL}/rabbit/{8}").json()
    assert data == {'input': 8, "result": 34}
