"""Export the FastAPI OpenAPI spec to openapi.json."""
import json
from pathlib import Path

from main import app

spec = app.openapi()
out = Path(__file__).parent / "openapi.json"
out.write_text(json.dumps(spec, indent=2))
print(f"OpenAPI spec written to {out}")
