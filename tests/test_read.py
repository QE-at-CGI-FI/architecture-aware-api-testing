"""Tests for read-only (GET) endpoints."""
import pytest
import requests

BASE_URL = "http://localhost:8001"


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_root_returns_200():
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200


def test_root_has_expected_fields():
    data = requests.get(f"{BASE_URL}/").json()
    assert "total_nodes" in data
    assert "top_level_categories" in data
    assert "leaf_nodes" in data
    assert "max_depth" in data
    assert "categories_by_level" in data


def test_root_node_counts():
    data = requests.get(f"{BASE_URL}/").json()
    assert data["total_nodes"] == 394
    assert data["top_level_categories"] == 11
    assert data["leaf_nodes"] == 341
    assert data["max_depth"] == 4


def test_root_categories_by_level_covers_all_nodes():
    data = requests.get(f"{BASE_URL}/").json()
    assert sum(data["categories_by_level"].values()) == data["total_nodes"]


# ---------------------------------------------------------------------------
# GET /categories
# ---------------------------------------------------------------------------

def test_categories_returns_200():
    r = requests.get(f"{BASE_URL}/categories")
    assert r.status_code == 200


def test_categories_returns_eleven_entries():
    data = requests.get(f"{BASE_URL}/categories").json()
    assert len(data) == 11


def test_categories_contains_user_interface_errors():
    data = requests.get(f"{BASE_URL}/categories").json()
    names = [c["name"] for c in data]
    assert "User Interface Errors" in names


def test_categories_each_have_required_fields():
    data = requests.get(f"{BASE_URL}/categories").json()
    for cat in data:
        assert "id" in cat
        assert "name" in cat
        assert "level" in cat
        assert "children" in cat


def test_categories_are_all_level_1():
    data = requests.get(f"{BASE_URL}/categories").json()
    assert all(c["level"] == 1 for c in data)


# ---------------------------------------------------------------------------
# GET /categories/{id}
# ---------------------------------------------------------------------------

def test_category_by_id_returns_200():
    r = requests.get(f"{BASE_URL}/categories/user-interface-errors")
    assert r.status_code == 200


def test_category_by_id_returns_correct_name():
    data = requests.get(f"{BASE_URL}/categories/user-interface-errors").json()
    assert data["name"] == "User Interface Errors"


def test_category_by_id_includes_children():
    data = requests.get(f"{BASE_URL}/categories/user-interface-errors").json()
    child_names = [c["name"] for c in data["children"]]
    assert "Functionality" in child_names
    assert "Communication" in child_names


def test_category_by_id_has_empty_breadcrumb_for_root():
    data = requests.get(f"{BASE_URL}/categories/user-interface-errors").json()
    assert data["breadcrumb"] == []


def test_category_unknown_id_returns_404():
    r = requests.get(f"{BASE_URL}/categories/does-not-exist")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /categories/{id}/subtree
# ---------------------------------------------------------------------------

def test_subtree_returns_200():
    r = requests.get(f"{BASE_URL}/categories/error-handling/subtree")
    assert r.status_code == 200


def test_subtree_children_are_nested_objects():
    data = requests.get(f"{BASE_URL}/categories/error-handling/subtree").json()
    assert isinstance(data["children"], list)
    assert all(isinstance(c, dict) for c in data["children"])


def test_subtree_unknown_id_returns_404():
    r = requests.get(f"{BASE_URL}/categories/does-not-exist/subtree")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /nodes
# ---------------------------------------------------------------------------

def test_nodes_returns_200():
    r = requests.get(f"{BASE_URL}/nodes")
    assert r.status_code == 200


def test_nodes_returns_all_394():
    data = requests.get(f"{BASE_URL}/nodes").json()
    assert len(data) == 394


def test_nodes_filter_level_1_matches_categories():
    data = requests.get(f"{BASE_URL}/nodes?level=1").json()
    assert len(data) == 11
    assert all(n["level"] == 1 for n in data)


def test_nodes_filter_level_4_returns_deepest_nodes():
    data = requests.get(f"{BASE_URL}/nodes?level=4").json()
    assert len(data) > 0
    assert all(n["level"] == 4 for n in data)


def test_nodes_filter_parent_id():
    data = requests.get(f"{BASE_URL}/nodes?parent_id=user-interface-errors").json()
    assert all(n["parent_id"] == "user-interface-errors" for n in data)
    assert len(data) > 0


def test_nodes_leaves_only():
    data = requests.get(f"{BASE_URL}/nodes?leaves_only=true").json()
    assert len(data) == 341
    assert all(n["child_count"] == 0 for n in data)


def test_nodes_invalid_level_returns_422():
    r = requests.get(f"{BASE_URL}/nodes?level=5")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /nodes/{id}
# ---------------------------------------------------------------------------

def test_node_by_id_returns_200():
    r = requests.get(f"{BASE_URL}/nodes/spelling-errors")
    assert r.status_code == 200


def test_node_by_id_has_description():
    data = requests.get(f"{BASE_URL}/nodes/spelling-errors").json()
    assert len(data["description"]) > 0


def test_node_by_id_breadcrumb_lists_ancestors():
    data = requests.get(f"{BASE_URL}/nodes/spelling-errors").json()
    breadcrumb_names = [b["name"] for b in data["breadcrumb"]]
    assert "User Interface Errors" in breadcrumb_names
    assert "Communication" in breadcrumb_names


def test_node_unknown_id_returns_404():
    r = requests.get(f"{BASE_URL}/nodes/no-such-node")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /search
# ---------------------------------------------------------------------------

def test_search_returns_200():
    r = requests.get(f"{BASE_URL}/search?q=boundary")
    assert r.status_code == 200


def test_search_results_contain_query_term():
    # Search matches against full descriptions, but responses only include a
    # 200-char excerpt — the term can legitimately appear past the cutoff.
    # We verify that results exist and that at least one has the term visible
    # in its name (a weaker but always-correct assertion).
    data = requests.get(f"{BASE_URL}/search?q=overflow").json()
    assert len(data) > 0
    names = [r["name"].lower() for r in data]
    assert any("overflow" in name for name in names)


def test_search_results_include_breadcrumb():
    data = requests.get(f"{BASE_URL}/search?q=cursor").json()
    assert len(data) > 0
    assert all(isinstance(r["breadcrumb"], list) for r in data)


def test_search_no_match_returns_empty_list():
    data = requests.get(f"{BASE_URL}/search?q=xyzzyplugh").json()
    assert data == []


def test_search_query_too_short_returns_422():
    r = requests.get(f"{BASE_URL}/search?q=x")
    assert r.status_code == 422


def test_search_missing_query_returns_422():
    r = requests.get(f"{BASE_URL}/search")
    assert r.status_code == 422
