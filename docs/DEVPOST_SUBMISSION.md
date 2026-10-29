# Nebius x NVIDIA Devpost submission — PARALLAX Studio

**Status: DRAFT — NOT SUBMITTED.** Replace all bracketed placeholders with verified links/data and don't claim an untested deployment or API call.

## Title
PARALLAX Studio — The visual inspection agent that knows when it needs another angle

## Tagline
From one uncertain photo to an evidence-linked finding and the next best capture.

## Track
Best Apps and Agents

## Inspiration
A single photo is often ambiguous. A mark can look like a crack, a shadow can look like damage, and a blurry image can lead to a confident but unsupported report. In field inspections, the better answer is often not a definitive diagnosis, but a **specific request for better evidence**.

## What it does
PARALLAX lets inspectors upload asset, property, or equipment photos and describe the question they need answered. It checks basic image quality, uses NVIDIA Nemotron 3.5 Super VL to extract visible observations, and **refuses to display findings that don't cite a supplied photo ID**. It records uncertainty instead of inventing missing details, then makes a second Nebius-powered call to plan the most useful next camera angle. A human can confirm, reject, or request additional evidence, and export a traceable inspection record.

## How we built it
A FastAPI backend normalizes photographs and calculates simple capture-quality signals with Pillow. For the live pipeline we use Nebius Token Factory's OpenAI-compatible `/chat/completions` API with `nvidia/Nemotron-3.5-Super-VL` in two steps: multimodal observation extraction and a grounded next-shot planner. The backend rejects claims with missing or fake image IDs and stores review decisions and inference trace metadata. A custom responsive vanilla JavaScript frontend keeps the capture-to-report workflow focused and fast. Pytest verifies API routing, photo validation, missing-key failure, evidence gates, and the two-call orchestration using mocks.

## Challenges
We deliberately distinguish model observations, interpretations, unresolved uncertainty, and human review. Referencing a valid photo ID does not prove the observation is true; the evidence gate improves traceability rather than claiming zero hallucinations. Another challenge is keeping the interface useful when live inference or credentials are unavailable: the synthetic sample is marked as such and cannot be mistaken for a live result.

## What we're proud of
One narrow, complete workflow: the app doesn't just analyze; it recommends the **next action that could change the conclusion**. Every visible finding points to an evidence photo. Uncertainty appears as a design input, not a confidence theater number.

## What's next
Coordinate-guided regions of interest, multi-angle comparisons, human-annotated verification, calibrated capture quality, benchmark datasets, and privacy-aware team workspaces. These are future ideas, not features in this build.

## Built with
Python, FastAPI, Pydantic, Pillow, HTTPX, Vanilla JavaScript, Docker, pytest, NVIDIA Nemotron 3.5 Super VL, Nebius Token Factory.

## Submission fields needing real validation
- Public repository URL: `https://github.com/bhagyashrimeena/parallex-nebius` **[SOURCE PUSHED AT f1cb4e0; REPOSITORY STILL PRIVATE]**
- Deployed functional URL: **[DEPLOY & TEST LIVE]**
- Public YouTube demo (duration strictly less than 3:00): **[UPLOAD]**
- Working Nebius request with account credits and vision model: **[VERIFY]**
- Teammates added + accepted: **[CHECK DEVPOST FORM]**
- Technical feedback: use `docs/TECH_FEEDBACK.md`, based on real runs.
- Significant updates during submission period: explain only changes accurately dated after Aug 26.
- Public repo license detection: MIT detected in the private repository; **[RECHECK AFTER PUBLIC VISIBILITY]**
- Final human approval and Devpost submit confirmation: **[NOT YET DONE]**

**Personal cutoff target:** Oct 30, 2026 at **3 PM IST**, before the 8:30 PM Halloween event. Official deadline: Oct 30, **10:30 PM IST** (10:00 AM PT). Do not edit submitted materials after the official deadline.
