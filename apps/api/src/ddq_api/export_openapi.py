"""Write the OpenAPI schema to disk. CI regenerates it to detect contract drift."""

import json
import sys
from pathlib import Path

from ddq_api.core.config import Settings
from ddq_api.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.json"  # apps/api/openapi.json


class _NoDatabase:
    async def ping(self) -> None:
        return None


def render_openapi() -> str:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="postgresql://x:x@localhost:5432/x",
        allowed_origins="http://localhost:5173",
    )
    schema = create_app(settings, db_health=_NoDatabase()).openapi()
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    target = Path(argv[0]) if argv else OPENAPI_PATH
    target.write_text(render_openapi(), encoding="utf-8", newline="\n")
    sys.stdout.write(f"wrote {target}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
