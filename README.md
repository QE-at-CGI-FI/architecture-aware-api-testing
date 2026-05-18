# architecture-aware-api-testing

[![API Docs](https://img.shields.io/badge/API%20docs-GitHub%20Pages-blue)](https://QE-at-CGI-FI.github.io/architecture-aware-api-testing/)

This repo holds materials for the architecture-aware API testing course, first delivered in the current format at Test Coast 2026 in Gothenburg.

---

## Kaner Common Software Errors Taxonomy API

A REST API that exposes the bug taxonomy from *Testing Computer Software* (Kaner, Falk & Nguyen, 1999) — 394 error types across 11 top-level categories, each with full descriptions and a navigable hierarchy.

### Running locally

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open the interactive docs in your browser:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Raw OpenAPI spec: http://localhost:8000/openapi.json

A static copy of the spec is also committed at [`openapi.json`](./openapi.json).

### API reference

| Endpoint | Description |
|---|---|
| `GET /` | Taxonomy statistics (node count, depth, counts by level) |
| `GET /taxonomy` | Full tree — all 394 nodes nested (large payload) |
| `GET /categories` | 11 top-level error categories with their direct children |
| `GET /categories/{id}` | One category with its direct children and breadcrumb |
| `GET /categories/{id}/subtree` | A category and all its descendants, nested |
| `GET /nodes` | Flat list of all nodes; filter by `level`, `parent_id`, `leaves_only` |
| `GET /nodes/{id}` | Full detail for any node: description, children, breadcrumb |
| `POST /nodes` | Add a new node; requires `X-API-Key` header |
| `PATCH /nodes/{id}` | Edit the name and/or description of a node; requires `X-API-Key` header |
| `GET /search?q=` | Case-insensitive search across names and descriptions |

#### Example requests

```bash
# List all top-level categories
curl http://localhost:8000/categories

# Explore the User Interface Errors subtree
curl http://localhost:8000/categories/user-interface-errors/subtree

# Get all leaf-level error nodes
curl "http://localhost:8000/nodes?leaves_only=true"

# Search for boundary-related errors
curl "http://localhost:8000/search?q=boundary"

# Get a single node with its breadcrumb and children
curl http://localhost:8000/nodes/race-conditions

# Add a new child node (requires API key)
curl -X POST http://localhost:8000/nodes \
  -H "X-API-Key: aaa" \
  -H "Content-Type: application/json" \
  -d '{"name":"My new error type","parent_id":"calculation-errors","description":"..."}'

# Add a new top-level category (omit parent_id)
curl -X POST http://localhost:8000/nodes \
  -H "X-API-Key: aaa" \
  -H "Content-Type: application/json" \
  -d '{"name":"AI-Specific Errors","description":"Errors unique to ML systems."}'

# Edit an existing node's description (requires API key)
curl -X PATCH http://localhost:8000/nodes/spelling-errors \
  -H "X-API-Key: aaa" \
  -H "Content-Type: application/json" \
  -d '{"description":"Updated description."}'
```

The default API key is `aaa`. Override it at startup with the `API_SECRET` environment variable:

```bash
API_SECRET=my-secret uvicorn main:app
```

#### Node levels

The taxonomy has four heading levels:

| Level | Meaning | Example |
|---|---|---|
| 1 | Top-level category | User Interface Errors |
| 2 | Sub-category | Functionality, Communication |
| 3 | Error group | Missing information, Display bugs |
| 4 | Specific error | No cursor, Spelling errors |

### GitHub Pages (API documentation site)

The workflow at `.github/workflows/publish-docs.yml` regenerates `openapi.json` from the live app and deploys a Swagger UI page automatically on every push to `main`.

**One-time setup** — enable GitHub Pages in the repository settings:

1. Go to **Settings → Pages**.
2. Under *Source*, select **GitHub Actions**.
3. Save. The next push to `main` will trigger the deployment.

The published site will be at `https://<org>.github.io/<repo>/`.

### Updating the OpenAPI spec

The committed `openapi.json` is generated from the live app. To regenerate it:

```bash
source .venv/bin/activate
python export_openapi.py
```

### Project files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies |
| `main.py` | FastAPI application |
| `parser.py` | Markdown-to-taxonomy parser |
| `export_openapi.py` | Script to regenerate `openapi.json` |
| `openapi.json` | Static OpenAPI 3.1.0 spec |
| `Kaner_CommonSoftwareErrors.md` | Source taxonomy (Appendix A, Kaner et al. 1999) |

