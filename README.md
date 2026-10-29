# PARALLAX Studio

**See what matters. Question the rest.**

PARALLAX is an evidence-first visual inspection copilot. Upload up to six photos of an asset or property, inspect the image quality, ask **NVIDIA Nemotron 3.5 Super VL** for visible observations, discard claims that are not linked to uploaded photo IDs, and use a second model call to plan the most useful missing camera angle. A person then confirms, rejects, or requests more evidence before the case is exported.

Interface screenshots are included in the downloadable submission kit.

> **Hackathon target:** Nebius x NVIDIA Global AI Hackathon (Best Apps and Agents). The application makes **two runtime calls to Nebius Token Factory** in live mode using NVIDIA's open vision-language model. An API key is mandatory for live inference. **Offline sample** is synthetic, prominently labeled, and never passed off as an NVIDIA model result. Live Token Factory connectivity and hosted deployment require verification using your own key; local mocked tests do not prove live connectivity.

## What it does

1. **Capture:** Upload 1–6 JPEG, PNG or WebP evidence photos, with an inspection category and goal.
2. **Evidence screening:** Normalize orientation; strip source metadata; compute basic resolution, brightness, contrast, and edge-detail warnings using Pillow. These checks are heuristic and are **not** defect detection.
3. **Visual analysis (live):** Nemotron 3.5 Super VL receives the images with strict evidence IDs (e.g., `P-01`) and separates observable facts from tentative interpretations.
4. **Evidence gate:** The backend rejects findings that do not cite an uploaded photo, normalizes unknown priorities, and records excluded claims. This checks *reference existence*, not whether a model observation is true.
5. **Gap planning (live):** A second Nemotron call uses the findings, uncertainty list, and photo-quality diagnostics to produce one specific next capture instruction.
6. **Follow-up loop:** Add the recommended new angle to the same case, archive the prior analysis, and rerun the two-call model workflow.
7. **Human review & export:** Confirm, reject, or mark findings as requiring more evidence; export a machine-readable JSON case and print the case summary to PDF with your browser.

The point is not to make AI more confident. It's to **make its uncertainty useful**.

## Tech stack

- **Inference:** NVIDIA `nvidia/Nemotron-3.5-Super-VL` served on [Nebius Token Factory](https://tokenfactory.nebius.com/) via the OpenAI-compatible chat-completions REST API.
- **Backend:** Python, FastAPI, HTTPX, Pillow, Pydantic.
- **Frontend:** Responsive vanilla HTML, CSS, and JavaScript (no frontend build step); dark editorial UI with lime accents.
- **Records:** Local JSON files and normalized JPEG evidence images in `data/sessions/<random-id>/` (ignored by Git).
- **Testing:** pytest and FastAPI TestClient; Docker image and GitHub Actions workflow included.

### Prerequisites

- Python **3.11+** (3.12 recommended)
- A Nebius Token Factory account, credits, and an API key with access to `nvidia/Nemotron-3.5-Super-VL`
- Internet access for live inference; none needed for the offline sample

### Quick start (Windows PowerShell)

```powershell
cd "C:\Users\bhagy\OneDrive\Desktop\parallex\parallex-nebius"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
# Set NEBIUS_API_KEY in .env without quotes or exposing it publicly.
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. If you haven't received your API key, open the synthetic sample case. Actual AI analysis remains disabled until the key is available. Windows setup can also be started via `powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1`.

### Quick start (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set NEBIUS_API_KEY (never commit the file).
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Docker

```bash
docker build -t parallax-studio .
docker run --rm -p 8000:8000 --env-file .env parallax-studio
```

The default Docker container stores case files in an ephemeral directory. For a durable environment mount a volume at `/workspace/data`.

### Environment

| Variable | Purpose | Default |
| --- | --- | --- |
| `NEBIUS_API_KEY` | Secret key; required for **real** AI inspection | unset |
| `NEBIUS_BASE_URL` | OpenAI-compatible Token Factory base URL | `https://api.tokenfactory.nebius.com/v1` |
| `NEBIUS_MODEL` | Vision-capable NVIDIA model you can access | `nvidia/Nemotron-3.5-Super-VL` |
| `PARALLAX_DATA_DIR` | Inspection storage directory | `./data` (relative to source root) |

Keep the API key **server-side**. Never put it in frontend JS, screenshots, commits, or the Devpost writeup. A change to the model name requires confirmation in your Token Factory catalog.

## API endpoints

| Method / route | Purpose |
| --- | --- |
| `GET /` | Responsive UI |
| `GET /api/health` | Health and *boolean* key readiness, never the key |
| `GET /api/demo` | Explicitly marked synthetic sample (no model request) |
| `POST /api/sessions` | Multipart `files`, `category`, `objective` |
| `GET /api/sessions/{id}` | Load a case |
| `GET /api/sessions/{id}/photos/{photo_id}` | View an uploaded image |
| `POST /api/sessions/{id}/analyze` | Perform **two live Token Factory requests** |
| `POST /api/sessions/{id}/photos` | Append follow-up evidence and archive prior analysis |
| `POST /api/sessions/{id}/review` | Human review: `finding_id`, `status`, `note` |
| `GET /api/sessions/{id}/export` | Download the evidence and review JSON record |
| `GET /api/docs` | OpenAPI interactive backend documentation |

### Run tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The test suite stubs `app.engine._call_nebius` for the two-call integration test. **It is not a substitute for a live end-to-end test.**

### Validate real integration

1. Confirm key and credits in the Token Factory console, then set `NEBIUS_API_KEY` in `.env`.
2. Run the server and confirm `/api/health` says `nebius_configured: true`. This only validates environment configuration.
3. Use **your own authorized, non-sensitive** asset photo. Set an inspection objective and click **Analyze evidence**.
4. Confirm the UI says `LIVE NVIDIA ANALYSIS`, shows specific evidence-linked observations, and counts **2 live model calls**.
5. View case JSON and confirm `result.trace[0].model`, `result.trace[1].model`, and response IDs from actual Token Factory requests. Record latency and tokens from the real run for Devpost feedback.
6. Confirm each `P-01` image reference opens the right photo, and test a human review change.
7. Record the **real** working app for the public demo video. Don't use the synthetic fixture as evidence of NVIDIA integration.

Failure is explicit: the server returns a non-2xx error for missing keys, model access errors, invalid JSON, or unavailable upstream. It never labels a fixture or failed inference as live analysis.

## Deploy for judges

A `render.yaml` and `Dockerfile` are provided. Create a web service from the **public** GitHub repository, set `NEBIUS_API_KEY` in the host's secret environment variables, select the Docker deploy, and set `/api/health` as the health check. Alternative Docker-capable hosts work. The default Render config specifies the free plan, which may sleep and has ephemeral disk; use persistent storage or a reliable paid service if sustained testing and retained cases matter. **A deployment URL is not yet verified.**

The hackathon requires free access for judges until judging ends in December 2026. Only use images you are entitled to share. The app is a demonstration, not a production multi-tenant evidence platform: there is no account system, encryption at rest, permanent storage SLA, or robust user-specific rate limit. Uploaded case URLs are unguessable but shareable; do not upload confidential imagery on a public deployment. Add abuse controls before broadly exposing a service with billable AI credits.

## Architecture

```
Browser (capture / evidence review / export)
    | HTTPS, multipart upload
FastAPI (/api/sessions)
    |--- Pillow: normalize photo & basic capture-quality diagnostics
    |--- save random-ID JSON case + sanitized JPEGs
    |--- call #1: Nebius Token Factory / chat/completions
    |       NVIDIA Nemotron 3.5 Super VL, with image data URIs
    |--- evidence reference gate (only actual uploaded photo IDs)
    |--- call #2: Nebius Token Factory / chat/completions
    |       NVIDIA Nemotron 3.5 Super VL, grounded gap planner
    |--- human review labels (confirm / reject / needs more evidence)
    `--- JSON export / browser print
```

### Safety and accuracy limitations

- Photos alone cannot verify hidden defects, safety, material strength, or causal attribution. Findings are **suggestions**, not diagnoses or certifications.
- The JSON evidence gate ensures IDs are valid; it cannot prove that descriptions match pixels.
- Simple brightness / contrast / edge-detail heuristics are not camera-calibrated blur scores.
- Uploaded images are resized to 1600 px on the longest edge. Very subtle defects may be lost.
- No conversational memory, geolocation, image segmentation, object tracking, real-world calibration, confidence score calibration, video input, or autonomous actuation.
- Data is stored locally. Public cloud filesystems may be ephemeral. Manual human review is mandatory.

## Originality and change log

The project evolves from an earlier offline PARALLAX idea with image checks and next-angle planning. This deliverable packages a dedicated standalone FastAPI visual studio, a designed end-user interface, structured evidence IDs, live multimodal inference and gap planning **implementation**, review/export workflows, sample-case separation, tests, deployment configuration, and submission materials. **Do not claim live runtime validation until an actual Nebius request succeeds.** Describe only changes you actually made after August 26, 2026 when submitting.

## Submission material

- `docs/DEVPOST_SUBMISSION.md` — project description, prerequisites, placeholders, and acceptance checklist.
- `docs/VIDEO_SCRIPT.md` — under-3-minute recording outline.
- `docs/TECH_FEEDBACK.md` — feedback worksheet; fill using real inference results.
- `docs/PUBLISH_TO_GITHUB.md` — safe publishing workflow without overwriting existing local PARALLAX files.

## License

MIT. See [LICENSE](LICENSE). NVIDIA models and Nebius services retain their own licenses and terms. The included sample image was generated specifically for this project and is synthetic.