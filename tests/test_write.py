"""Tests for write endpoints (POST /nodes, PATCH /nodes/{id}) and auth."""
import requests

BASE_URL = "http://localhost:8001"
API_KEY = "aaa"


def auth():
    return {"X-API-Key": API_KEY}


# ---------------------------------------------------------------------------
# Auth — POST /nodes
# ---------------------------------------------------------------------------

def test_post_without_key_returns_401():
    r = requests.post(f"{BASE_URL}/nodes", json={"name": "Test"})
    assert r.status_code == 401


def test_post_with_wrong_key_returns_401():
    r = requests.post(
        f"{BASE_URL}/nodes",
        headers={"X-API-Key": "wrong"},
        json={"name": "Test"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Auth — PATCH /nodes/{id}
# ---------------------------------------------------------------------------

def test_patch_without_key_returns_401():
    r = requests.patch(
        f"{BASE_URL}/nodes/spelling-errors",
        json={"description": "Updated"},
    )
    assert r.status_code == 401


def test_patch_with_wrong_key_returns_401():
    r = requests.patch(
        f"{BASE_URL}/nodes/spelling-errors",
        headers={"X-API-Key": "bad-key"},
        json={"description": "Updated"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /nodes — valid requests
# ---------------------------------------------------------------------------

def test_post_creates_child_node(restore_custom):
    r = requests.post(
        f"{BASE_URL}/nodes",
        headers=auth(),
        json={
            "name": "AI hallucination output",
            "parent_id": "calculation-errors",
            "description": "Model outputs confident but factually wrong results.",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "AI hallucination output"
    assert data["parent_id"] == "calculation-errors"
    assert data["level"] == 2


def test_post_child_node_id_is_slugified(restore_custom):
    r = requests.post(
        f"{BASE_URL}/nodes",
        headers=auth(),
        json={"name": "My New Error Type", "parent_id": "error-handling"},
    )
    assert r.status_code == 201
    assert r.json()["id"] == "my-new-error-type"


def test_post_creates_top_level_category(restore_custom):
    r = requests.post(
        f"{BASE_URL}/nodes",
        headers=auth(),
        json={"name": "AI-Specific Errors", "description": "Errors unique to ML systems."},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["level"] == 1
    assert data["parent_id"] is None


def test_post_created_node_is_retrievable(restore_custom):
    requests.post(
        f"{BASE_URL}/nodes",
        headers=auth(),
        json={"name": "Retrievable Node Test", "parent_id": "hardware"},
    )
    r = requests.get(f"{BASE_URL}/nodes/retrievable-node-test")
    assert r.status_code == 200
    assert r.json()["name"] == "Retrievable Node Test"


def test_post_response_includes_breadcrumb(restore_custom):
    r = requests.post(
        f"{BASE_URL}/nodes",
        headers=auth(),
        json={"name": "Breadcrumb Check Node", "parent_id": "race-conditions"},
    )
    assert r.status_code == 201
    breadcrumb_names = [b["name"] for b in r.json()["breadcrumb"]]
    assert "Race Conditions" in breadcrumb_names


# ---------------------------------------------------------------------------
# POST /nodes — invalid requests
# ---------------------------------------------------------------------------

def test_post_unknown_parent_returns_404():
    r = requests.post(
        f"{BASE_URL}/nodes",
        headers=auth(),
        json={"name": "Orphan", "parent_id": "no-such-parent"},
    )
    assert r.status_code == 404


def test_post_empty_name_returns_422():
    r = requests.post(
        f"{BASE_URL}/nodes",
        headers=auth(),
        json={"name": ""},
    )
    assert r.status_code == 422


def test_post_missing_name_returns_422():
    r = requests.post(
        f"{BASE_URL}/nodes",
        headers=auth(),
        json={"description": "No name provided"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /nodes/{id} — valid requests
# ---------------------------------------------------------------------------

def test_patch_updates_description(restore_custom):
    new_desc = "Typos in UI text. Customers notice even when developers do not."
    r = requests.patch(
        f"{BASE_URL}/nodes/spelling-errors",
        headers=auth(),
        json={"description": new_desc},
    )
    assert r.status_code == 200
    assert r.json()["description"] == new_desc


def test_patch_updates_name(restore_custom):
    r = requests.patch(
        f"{BASE_URL}/nodes/verbosity",
        headers=auth(),
        json={"name": "Excessive verbosity"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Excessive verbosity"


def test_patch_updates_both_fields(restore_custom):
    r = requests.patch(
        f"{BASE_URL}/nodes/factual-errors",
        headers=auth(),
        json={"name": "Factual errors (updated)", "description": "Incorrect facts in help text."},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Factual errors (updated)"
    assert data["description"] == "Incorrect facts in help text."


def test_patch_preserves_unmodified_fields(restore_custom):
    original = requests.get(f"{BASE_URL}/nodes/infinite-loop").json()
    requests.patch(
        f"{BASE_URL}/nodes/infinite-loop",
        headers=auth(),
        json={"description": "Loop with no exit condition."},
    )
    updated = requests.get(f"{BASE_URL}/nodes/infinite-loop").json()
    assert updated["level"] == original["level"]
    assert updated["parent_id"] == original["parent_id"]


# ---------------------------------------------------------------------------
# PATCH /nodes/{id} — invalid requests
# ---------------------------------------------------------------------------

def test_patch_unknown_node_returns_404():
    r = requests.patch(
        f"{BASE_URL}/nodes/no-such-node",
        headers=auth(),
        json={"description": "Ghost update"},
    )
    assert r.status_code == 404


def test_patch_no_fields_returns_422():
    r = requests.patch(
        f"{BASE_URL}/nodes/spelling-errors",
        headers=auth(),
        json={},
    )
    assert r.status_code == 422
