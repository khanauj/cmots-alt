"""Run the API with uvicorn:  python -m cmots_alt.api   (or `cmots-api`)."""

from __future__ import annotations

import uvicorn

from .config import get_api_settings


def main() -> None:
    s = get_api_settings()
    uvicorn.run(
        "cmots_alt.api.main:app",
        host=s.host,
        port=s.port,
        reload=s.reload,
        factory=False,
    )


if __name__ == "__main__":
    main()
