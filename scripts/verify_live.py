"""Run a real, temporary Nebius inspection without printing credentials or images."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

def main() -> int:
    if not os.getenv("NEBIUS_API_KEY", "").strip():
        print("NEBIUS_API_KEY is missing; no live call was made.")
        return 2

    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="parallax-live-") as data_dir:
        os.environ["PARALLAX_DATA_DIR"] = data_dir
        from fastapi.testclient import TestClient
        from app.main import app

        photo = (root / "app" / "static" / "demo-equipment.jpg").read_bytes()
        with TestClient(app) as client:
            created = client.post(
                "/api/sessions",
                data={"category": "Equipment & assets", "objective": "Describe only visible condition and uncertainty"},
                files=[("files", ("synthetic-equipment.jpg", photo, "image/jpeg"))],
            )
            if created.status_code != 201:
                print(f"Upload failed: HTTP {created.status_code}")
                return 1
            sid = created.json()["id"]
            analyzed = client.post(f"/api/sessions/{sid}/analyze")
            if analyzed.status_code != 200:
                print(f"Live inspection failed: HTTP {analyzed.status_code}; {analyzed.json().get('detail', 'unknown error')}")
                return 1
            result = analyzed.json()["result"]
            trace = result.get("trace", [])
            if result.get("mode") != "live" or len(trace) != 2 or not all(item.get("response_id") for item in trace):
                print("Response lacked two verifiable live Nebius traces.")
                return 1
            review_status = "skipped: no evidence-linked finding"
            if result.get("findings"):
                reviewed = client.post(
                    f"/api/sessions/{sid}/review",
                    json={"finding_id": result["findings"][0]["id"], "status": "needs_more_evidence"},
                )
                if reviewed.status_code != 200:
                    print(f"Human review failed: HTTP {reviewed.status_code}")
                    return 1
                review_status = "passed"
            exported = client.get(f"/api/sessions/{sid}/export")
            if exported.status_code != 200 or exported.json()["id"] != sid:
                print("JSON export failed.")
                return 1
            print(json.dumps({
                "live_inference": "passed",
                "model": result.get("model"),
                "call_count": len(trace),
                "response_ids_present": True,
                "seconds_per_call": [item.get("seconds") for item in trace],
                "finding_count": len(result.get("findings", [])),
                "human_review": review_status,
                "json_export": "passed",
                "sample_image": "synthetic local fixture",
            }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
