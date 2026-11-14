"""Starter only: route implementations belong to the API session."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="악플가드 API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

# TODO [S3 API]: register routers, database lifecycle and error handlers.
# Contract: docs/api-contract.md. Do not add placeholder success responses.
