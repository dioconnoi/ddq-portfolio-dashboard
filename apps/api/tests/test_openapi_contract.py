import json
from pathlib import Path

from ddq_api.export_openapi import OPENAPI_PATH, main, render_openapi


def test_schema_documents_health_and_ready() -> None:
    schema = json.loads(render_openapi())
    assert {"/health", "/ready"} <= set(schema["paths"])
    assert "503" in schema["paths"]["/ready"]["get"]["responses"]


def test_rendering_is_deterministic() -> None:
    assert render_openapi() == render_openapi()


def test_committed_contract_is_up_to_date() -> None:
    assert OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi(), (
        "apps/api/openapi.json is stale: run `uv run python -m ddq_api.export_openapi` "
        "and `pnpm --dir apps/web gen:api`, then commit both."
    )


def test_main_writes_the_requested_file(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    assert main([str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["openapi"].startswith("3.")
