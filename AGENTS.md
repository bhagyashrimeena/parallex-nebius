# PARALLAX Studio — Codex Instructions

## Mission
Ship the existing PARALLAX Studio app as a compliant submission for the Nebius x NVIDIA Global AI Hackathon. Do not substitute a mocked demo for real inference. Deadline: Friday, 30 October 2026, 10:00 AM Pacific / 10:30 PM IST. Personal submission cutoff: 3:00 PM IST, before the user's separately booked outing.

## First action: source audit
The README was initialized before the complete app was uploaded. Confirm that app/main.py, app/engine.py, app/static/index.html, app/static/app.js, app/static/styles.css, requirements.txt, Dockerfile, and tests/ exist on this branch. If missing, do not claim the app is implemented. Have the user run the provided local ZIP publication script or upload the PARALLAX Studio submission kit from the preceding ChatGPT handoff; do not guess that files exist.

## Existing implementation, once present
- FastAPI / Pydantic / Pillow / HTTPX backend, no frontend build tool; frontend vanilla JS/CSS/HTML.
- Image upload and quality screening, up to six photographs per inspection.
- Nebius Token Factory OpenAI-compatible vision call with NVIDIA Nemotron 3.5 Super VL, followed by a second model call to suggest a more informative photo angle.
- Structured observations referencing photo IDs, uncertainty and rejected ungrounded citations, human review actions, JSON export.
- Synthetic offline demo clearly marked as fixture. Never present it as live model evidence.
- Unit and integration tests (previously 18 passed, re-run at current HEAD).

## Acceptance gates
1. Source is present and clean; review all differences; no .env, tokens, data/sessions, sensitive images, caches, or credential leakage in git or logs.
2. Install pinned/compatible dependencies and run python -m pytest -q; check JavaScript parsing.
3. Obtain the Nebius API key from an environment secret, never from chat, repository, screenshots, or a client bundle. Confirm exact model ID from current Nebius catalog and a LIVE image-based call returning structured observations. Record redacted timings, model, and status, not keys or images.
4. Audit exposure: unauthenticated upload, persistent local photos, public viewing/analysis links, open endpoints and unbounded inference could be abused. Introduce realistic rate limiting or controlled demo access before public deployment; disable or bound high-cost endpoints as necessary.
5. Deploy FastAPI + frontend to a publicly reachable HTTPS URL; configure NEBIUS_API_KEY as server secret. Health endpoint alone is not sufficient. Verify upload -> inspect -> next shot -> human review -> export using non-sensitive sample images over deployed HTTPS.
6. Update README with current reproducible setup, architecture, actual test evidence, known limitations, privacy notes, and REAL deployment link. Keep visible OSI-approved license (MIT), include .env.example, .gitignore and deployment config. No unsubstantiated performance claims.
7. Make repository PUBLIC only after secrets and sensitive files have been audited. GitHub connector may not expose repo visibility editing; a human can use GitHub Settings -> General -> Danger Zone -> Change repository visibility.
8. Produce an actual PUBLIC YouTube demo less than 3 minutes: first 30s showing the product's aha moment, then evidence capture, actual Nebius/NVIDIA model inference, next shot, review/export, limitations. Capture a screen recording of working software; a script alone is not a video.
9. Complete the official Devpost project fields: title, problem, track (Best Apps and Agents), what was built, how it works, genuinely used Nebius/NVIDIA resources, public repo, running URL, public YouTube URL, specific technology feedback, and accepted teammate invitations. Keep working draft until links pass. User submits/approves.
10. Confirm Devpost success page/time BEFORE personal cutoff (3 PM IST, Oct 30). Do not modify any materials after official deadline.

## Commands
- Windows: `powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1` then `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- CI: `python -m pip install -r requirements.txt -r requirements-dev.txt && python -m pytest -q`
- Run server: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Rules of evidence
Distinguish local tests, mocked inference, actual live inference, public deployment, video upload and Devpost submission. Never mark an unchecked gate as complete. Avoid made-up dates, URLs, teammate statuses, or credentials. No fabricated damage diagnosis. Use synthetic/public-domain images only in public demonstrations. Preserve the original app when it arrives; make focused safe changes, and prioritize getting a real submission in before the cutoff.
