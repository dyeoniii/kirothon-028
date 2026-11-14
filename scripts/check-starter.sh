#!/usr/bin/env bash
set -euo pipefail
printf 'Checking starter files...\n'
for f in docs/api-contract.md docs/internal-interfaces.md frontend/package.json frontend/src/App.tsx backend/app/main.py backend/requirements.txt prompts/02_session_prompts.md; do
 [[ -f "$f" ]] || { echo "Missing: $f"; exit 1; }
done
python3 -m compileall -q backend/app
python3 -m json.tool frontend/package.json >/dev/null
python3 -m json.tool frontend/public/manifest.webmanifest >/dev/null
echo 'Starter structure OK. This does NOT verify business features.'
