"""Kaner Common Software Errors Taxonomy REST API."""
from __future__ import annotations

import json
import random
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Annotated, Optional

import os

from fastapi import FastAPI, HTTPException, Query, Response, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from parser import KanerTaxonomy, TaxonomyNode

MD_PATH = Path(__file__).parent / "Kaner_CommonSoftwareErrors.md"
CUSTOM_PATH = Path(__file__).parent / "taxonomy_custom.json"

app = FastAPI(
    title="Kaner Common Software Errors Taxonomy API",
    version="1.0.0",
    description=(
        "REST API for navigating the bug taxonomy from Kaner, Falk, and Nguyen (1999). "
        "Provides hierarchical access to over 400 common software error types, "
        "organised into categories with full descriptions."
    ),
    contact={"name": "Architecture-Aware API Testing"},
    license_info={"name": "Reference: Kaner et al. 1999"},
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_API_KEY = os.environ.get("API_SECRET", "aaa")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str = Security(_api_key_header)) -> None:
    if key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_custom() -> dict:
    if CUSTOM_PATH.exists():
        return json.loads(CUSTOM_PATH.read_text())
    return {"additions": [], "edits": {}}


def _save_custom(data: dict) -> None:
    CUSTOM_PATH.write_text(json.dumps(data, indent=2))


def _build_taxonomy() -> tuple[KanerTaxonomy, dict]:
    t = KanerTaxonomy(MD_PATH)
    custom = _load_custom()
    for edit_id, fields in custom["edits"].items():
        t.update_node(edit_id, **fields)
    for addition in custom["additions"]:
        t.add_node(
            name=addition["name"],
            description=addition.get("description", ""),
            parent_id=addition.get("parent_id"),
        )
    return t, custom


# Load taxonomy once at startup.
taxonomy, _custom = _build_taxonomy()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class NodeSummary(BaseModel):
    id: str
    name: str
    level: int
    parent_id: Optional[str]
    child_count: int
    has_description: bool


class NodeDetail(BaseModel):
    id: str
    name: str
    level: int
    description: str
    parent_id: Optional[str]
    children: list[NodeSummary]
    breadcrumb: list[NodeSummary]


class NodeTree(BaseModel):
    id: str
    name: str
    level: int
    description: str
    parent_id: Optional[str]
    children: list["NodeTree"]

    model_config = {"from_attributes": True}


class CreateNodeRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the new error or category")
    parent_id: Optional[str] = Field(
        None,
        description="ID of the parent node. Omit to create a top-level category.",
    )
    description: str = Field("", description="Description text (Markdown supported)")


class UpdateNodeRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="New name")
    description: Optional[str] = Field(None, description="New description text (Markdown supported)")


class SearchResult(BaseModel):
    id: str
    name: str
    level: int
    description_excerpt: str
    parent_id: Optional[str]
    breadcrumb: list[str]


class RabbitResult(BaseModel):
    input: int
    result: int


class AsyncJobStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[int] = None


class TaxonomyStats(BaseModel):
    total_nodes: int
    top_level_categories: int
    leaf_nodes: int
    max_depth: int
    categories_by_level: dict[str, int]


def _summary(node: TaxonomyNode) -> NodeSummary:
    return NodeSummary(
        id=node.id,
        name=node.name,
        level=node.level,
        parent_id=node.parent_id,
        child_count=len(node.children),
        has_description=bool(node.description),
    )


def _detail(node: TaxonomyNode) -> NodeDetail:
    breadcrumb = [_summary(n) for n in taxonomy.path_to(node.id)[:-1]]
    children = [_summary(taxonomy.get(cid)) for cid in node.children]
    return NodeDetail(
        id=node.id,
        name=node.name,
        level=node.level,
        description=node.description,
        parent_id=node.parent_id,
        children=children,
        breadcrumb=breadcrumb,
    )


def _node_to_tree(node: TaxonomyNode) -> NodeTree:
    return NodeTree(
        id=node.id,
        name=node.name,
        level=node.level,
        description=node.description,
        parent_id=node.parent_id,
        children=[_node_to_tree(taxonomy.get(cid)) for cid in node.children],
    )


def _excerpt(text: str, max_len: int = 200) -> str:
    text = text.replace("\n", " ").strip()
    return text[:max_len] + "…" if len(text) > max_len else text


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


_RABBIT_SCRIPT = Path(__file__).parent / "rabbit.py"


def _call_rabbit(n: int) -> int:
    proc = subprocess.run(
        [sys.executable, str(_RABBIT_SCRIPT), str(n)],
        capture_output=True, text=True, timeout=10,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr.strip())
    return int(proc.stdout.strip())


# --- Simulation state (in-memory, resets on restart) ---
_unreliable_count = 0


class _AsyncBatch:
    def __init__(self, results: dict[str, int], reveal_order: list[str]) -> None:
        self.results = results
        self.reveal_order = reveal_order
        self.polls = 0


_async_pending: list[tuple[str, int]] = []
_async_job_to_batch: dict[str, _AsyncBatch] = {}


@app.get(
    "/rabbit/{n}",
    response_model=RabbitResult,
    summary="I take a number and return a number but what am I?",
    tags=["rabbit"],
)
def rabbit(n: int) -> RabbitResult:
    """Do what rabbit.py does."""
    if n < 1:
        raise HTTPException(status_code=422, detail="n must be a positive integer.")
    proc = subprocess.run(
        [sys.executable, str(_RABBIT_SCRIPT), str(n)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr.strip())
    return RabbitResult(input=n, result=int(proc.stdout.strip()))


@app.get("/", summary="API info and statistics", tags=["meta"])
def root() -> TaxonomyStats:
    """Return summary statistics about the loaded taxonomy."""
    all_nodes = taxonomy.flat_list()
    by_level: dict[int, int] = {}
    for n in all_nodes:
        by_level[n.level] = by_level.get(n.level, 0) + 1
    max_depth = max(by_level.keys(), default=0)
    return TaxonomyStats(
        total_nodes=len(all_nodes),
        top_level_categories=len(taxonomy.root_ids),
        leaf_nodes=len(taxonomy.leaves()),
        max_depth=max_depth,
        categories_by_level={f"level_{k}": v for k, v in sorted(by_level.items())},
    )


@app.get(
    "/taxonomy",
    response_model=list[NodeTree],
    summary="Full taxonomy tree",
    tags=["taxonomy"],
)
def full_taxonomy() -> list[NodeTree]:
    """Return the complete taxonomy as a nested tree.

    Warning: the full tree is large (~400 nodes). Consider `/categories`
    and drill-down via `/nodes/{id}/subtree` for paginated access.
    """
    return [_node_to_tree(n) for n in taxonomy.roots()]


@app.get(
    "/categories",
    response_model=list[NodeDetail],
    summary="List top-level error categories",
    tags=["categories"],
)
def list_categories() -> list[NodeDetail]:
    """Return all top-level categories (H1 headings) with their direct children."""
    return [_detail(n) for n in taxonomy.roots()]


@app.get(
    "/categories/{category_id}",
    response_model=NodeDetail,
    summary="Get a category",
    tags=["categories"],
)
def get_category(category_id: str) -> NodeDetail:
    """Return a single category node with its immediate children and breadcrumb."""
    node = taxonomy.get(category_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node '{category_id}' not found.")
    return _detail(node)


@app.get(
    "/categories/{category_id}/subtree",
    response_model=NodeTree,
    summary="Get a category's full subtree",
    tags=["categories"],
)
def get_subtree(category_id: str) -> NodeTree:
    """Return a category and all its descendants as a nested tree."""
    node = taxonomy.get(category_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node '{category_id}' not found.")
    return _node_to_tree(node)


@app.get(
    "/nodes",
    response_model=list[NodeSummary],
    summary="List all nodes (flat)",
    tags=["nodes"],
)
def list_nodes(
    level: Annotated[Optional[int], Query(ge=1, le=4, description="Filter by heading level (1–4)")] = None,
    parent_id: Annotated[Optional[str], Query(description="Filter by parent node ID")] = None,
    leaves_only: Annotated[bool, Query(description="Return only leaf nodes (no children)")] = False,
) -> list[NodeSummary]:
    """Return a flat list of all taxonomy nodes, with optional filters."""
    nodes = taxonomy.flat_list()
    if level is not None:
        nodes = [n for n in nodes if n.level == level]
    if parent_id is not None:
        nodes = [n for n in nodes if n.parent_id == parent_id]
    if leaves_only:
        nodes = [n for n in nodes if not n.children]
    return [_summary(n) for n in nodes]


@app.get(
    "/nodes/{node_id}",
    response_model=NodeDetail,
    summary="Get a single node",
    tags=["nodes"],
)
def get_node(node_id: str) -> NodeDetail:
    """Return full detail for any node: description, children, and breadcrumb path."""
    node = taxonomy.get(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
    return _detail(node)


@app.post(
    "/nodes",
    response_model=NodeDetail,
    status_code=201,
    summary="Add a new node",
    tags=["nodes"],
)
def create_node(body: CreateNodeRequest, _: None = Security(require_api_key)) -> NodeDetail:
    """Add a new error or category to the taxonomy.

    - Supply a `parent_id` to nest the node under an existing one; its level
      is derived automatically (parent level + 1).
    - Omit `parent_id` to create a new top-level category (level 1).

    Changes are persisted to `taxonomy_custom.json` and survive restarts.
    """
    if body.parent_id is not None and taxonomy.get(body.parent_id) is None:
        raise HTTPException(status_code=404, detail=f"Parent node '{body.parent_id}' not found.")
    try:
        node = taxonomy.add_node(
            name=body.name,
            description=body.description,
            parent_id=body.parent_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _custom["additions"].append(
        {"name": body.name, "description": body.description, "parent_id": body.parent_id}
    )
    _save_custom(_custom)
    return _detail(node)


@app.patch(
    "/nodes/{node_id}",
    response_model=NodeDetail,
    summary="Edit a node's name or description",
    tags=["nodes"],
)
def update_node(node_id: str, body: UpdateNodeRequest, _: None = Security(require_api_key)) -> NodeDetail:
    """Update the name and/or description of any node.

    At least one of `name` or `description` must be provided.
    Changes are persisted to `taxonomy_custom.json` and survive restarts.
    """
    if body.name is None and body.description is None:
        raise HTTPException(
            status_code=422, detail="Provide at least one of 'name' or 'description'."
        )
    if taxonomy.get(node_id) is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    fields: dict = {}
    if body.name is not None:
        fields["name"] = body.name
    if body.description is not None:
        fields["description"] = body.description

    node = taxonomy.update_node(node_id, **fields)

    existing = _custom["edits"].get(node_id, {})
    existing.update(fields)
    _custom["edits"][node_id] = existing
    _save_custom(_custom)
    return _detail(node)


@app.get(
    "/search",
    response_model=list[SearchResult],
    summary="Search taxonomy nodes",
    tags=["search"],
)
def search(
    q: Annotated[str, Query(min_length=2, description="Search term (case-insensitive, searches name and description)")],
) -> list[SearchResult]:
    """Full-text search across all node names and descriptions.

    Returns nodes where the query string appears in the name or description,
    ordered by level (broader categories first).
    """
    results = sorted(taxonomy.search(q), key=lambda n: (n.level, n.name))
    return [
        SearchResult(
            id=n.id,
            name=n.name,
            level=n.level,
            description_excerpt=_excerpt(n.description),
            parent_id=n.parent_id,
            breadcrumb=[node.name for node in taxonomy.path_to(n.id)[:-1]],
        )
        for n in results
    ]


# ---------------------------------------------------------------------------
# Simulation endpoints
# ---------------------------------------------------------------------------

_async_jobs: dict[str, int] = {}  # job_id -> poll count


@app.get("/flaky", summary="Unreliable hello", tags=["simulation"])
def flaky() -> Response:
    """Return 'Hello world!' two thirds of the time; 503 the other third."""
    if random.random() < 2 / 3:
        return Response(content="Hello world!", media_type="text/plain")
    raise HTTPException(status_code=503, detail="Service temporarily unavailable.")


@app.post(
    "/async",
    response_model=AsyncJobStatus,
    status_code=202,
    summary="Start an async job",
    tags=["simulation"],
)
def start_async_job() -> AsyncJobStatus:
    """Create a new async job and return its ID. Poll GET /async/{job_id} to get the result."""
    job_id = str(uuid.uuid4())
    _async_jobs[job_id] = 0
    return AsyncJobStatus(job_id=job_id, status="pending")


@app.get(
    "/async/{job_id}",
    response_model=AsyncJobStatus,
    summary="Poll an async job",
    tags=["simulation"],
)
def poll_async_job(job_id: str) -> AsyncJobStatus:
    """Poll for job status. Returns 'pending' until the third poll, then 'complete'."""
    if job_id not in _async_jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    _async_jobs[job_id] += 1
    if _async_jobs[job_id] >= 3:
        return AsyncJobStatus(job_id=job_id, status="complete", result=42)
    return AsyncJobStatus(job_id=job_id, status="pending")
