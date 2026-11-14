"""Starter only: route implementations belong to the API session."""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Catch Trolls API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

# TODO [S3 API]: register routers, database lifecycle and error handlers.
# Contract: docs/api-contract.md. Do not add placeholder success responses.

# Serve the built React app (Docker: STATIC_DIR=/app/static). Must stay after all /api routes.
_static_env = os.getenv("STATIC_DIR")
STATIC_DIR = Path(_static_env).resolve() if _static_env else None

if STATIC_DIR and STATIC_DIR.is_dir():
    if (STATIC_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (STATIC_DIR / full_path).resolve()
        if candidate.is_file() and STATIC_DIR in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
