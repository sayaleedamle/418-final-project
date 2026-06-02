"""TruthCheck Flask API.

Endpoints
---------
GET  /          — API info
GET  /health    — liveness check
POST /check     — fact-check a YouTube video
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from flasgger import Swagger
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from truthcheck.agents.orchestrator import TruthCheckAgent
from truthcheck.config import Config
from truthcheck.tools.transcript import TranscriptFetchError

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

Swagger(app, template={
    "info": {
        "title": "TruthCheck API",
        "description": (
            "Fact-check health and nutrition claims in YouTube videos. "
            "Claims are extracted by Claude and evaluated against PubMed, "
            "Cochrane Reviews, CDC, WHO, and NIH evidence."
        ),
        "version": "0.1.0",
        "contact": {"email": "damlesayalee@g.ucla.edu"},
    },
    "consumes": ["application/json"],
    "produces": ["application/json"],
})

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["30 per minute"],
    storage_uri="memory://",
)

# ── Startup — initialise agent once ──────────────────────────────────────────

_agent: TruthCheckAgent | None = None
_config: Config | None = None

try:
    _config = Config.from_env()
    _agent = TruthCheckAgent.from_config(_config)
    log.info("TruthCheckAgent ready — model: %s", _config.model)
except RuntimeError as exc:
    log.error("Agent init failed: %s", exc)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    """API information.
    ---
    responses:
      200:
        description: API metadata
    """
    return jsonify({
        "name": "TruthCheck API",
        "version": "0.1.0",
        "docs": "/apidocs",
        "endpoints": {
            "GET  /health": "Liveness check",
            "POST /check":  "Fact-check a YouTube video",
        },
    })


@app.get("/health")
def health():
    """Liveness check.
    ---
    responses:
      200:
        description: Service is healthy
        schema:
          properties:
            status:
              type: string
              example: ok
            model:
              type: string
              example: claude-opus-4-7
            timestamp:
              type: string
    """
    return jsonify({
        "status":    "ok" if _agent else "degraded",
        "model":     _config.model if _config else "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.post("/check")
@limiter.limit("5 per minute")
def check():
    """Fact-check a YouTube video.
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [video]
          properties:
            video:
              type: string
              description: YouTube URL or 11-character video ID
              example: "https://www.youtube.com/watch?v=E7W4OQfJWdw"
            max_claims:
              type: integer
              description: >
                Maximum number of claims to evaluate. Omit to evaluate all
                claims found. Use a small number (e.g. 5) for quick demos.
              example: 10
    responses:
      200:
        description: Structured fact-check report
        schema:
          properties:
            video_id:     {type: string}
            video_url:    {type: string}
            total_claims: {type: integer}
            claims:
              type: array
              items:
                properties:
                  claim:        {type: string}
                  timestamp_s:  {type: number}
                  context:      {type: string}
                  verdict:      {type: string}
                  explanation:  {type: string}
                  citations:    {type: array}
            summary:
              type: object
              properties:
                supported:    {type: integer}
                contradicted: {type: integer}
                misleading:   {type: integer}
                unverifiable: {type: integer}
            elapsed_s: {type: number}
      400:
        description: Missing or invalid request body
      422:
        description: Could not fetch transcript for the given video
      500:
        description: Internal pipeline error
      503:
        description: Agent not initialised (missing API key)
    """
    if _agent is None:
        return jsonify({"error": "Agent not initialised — check GEMINI_API_KEY"}), 503

    body = request.get_json(silent=True)
    if not body or "video" not in body:
        return jsonify({"error": "Request body must include a 'video' field"}), 400

    video = str(body["video"]).strip()
    if not video:
        return jsonify({"error": "'video' must not be empty"}), 400

    transcript = body.get("transcript") or None  # optional pre-fetched transcript
    max_claims = body.get("max_claims")
    if max_claims is not None:
        if not isinstance(max_claims, int) or max_claims < 1:
            return jsonify({"error": "'max_claims' must be a positive integer"}), 400

    log.info("POST /check  video=%s  max_claims=%s", video, max_claims)
    t0 = time.monotonic()

    try:
        report = asyncio.run(_agent.check(video, max_claims=max_claims, transcript=transcript))
    except TranscriptFetchError as exc:
        log.warning("Transcript fetch failed: %s", exc)
        return jsonify({"error": f"Could not fetch transcript: {exc}"}), 422
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        log.exception("Pipeline error for video=%s", video)
        return jsonify({"error": "Internal pipeline error", "detail": str(exc)}), 500

    elapsed = round(time.monotonic() - t0, 2)
    log.info("Done  video=%s  claims=%d  elapsed=%.1fs", video, report.total_claims, elapsed)

    payload = report.model_dump()
    payload["summary"]   = report.counts
    payload["elapsed_s"] = elapsed
    return jsonify(payload)


@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "Rate limit exceeded — please slow down"}), 429


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
