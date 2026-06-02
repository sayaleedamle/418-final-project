#!/usr/bin/env bash
# Deploy TruthCheck to Google Cloud Run.
#
# Prerequisites
# -------------
# 1. Install gcloud CLI:  https://cloud.google.com/sdk/docs/install
# 2. Authenticate:        gcloud auth login && gcloud auth configure-docker
# 3. Install Docker (must be running)
# 4. Set your API key:    export GEMINI_API_KEY=AIza...
#
# Usage
# -----
#   cd final_project/final_project
#   ./deploy.sh <GCP_PROJECT_ID>          # e.g. ./deploy.sh my-project-123
#
# After the script finishes it prints the live URLs for both services.

set -euo pipefail

# ── Config (edit these if you want a different region or service names) ───────

PROJECT="${1:?"Usage: ./deploy.sh <GCP_PROJECT_ID>"}"
REGION="us-central1"
REPO="truthcheck"
API_SERVICE="truthcheck-api"
APP_SERVICE="truthcheck-app"

# ── Validate required env vars ────────────────────────────────────────────────

: "${GEMINI_API_KEY:?GEMINI_API_KEY is not set. Run: export GEMINI_API_KEY=AIza...}"
: "${WEBSHARE_USER:?WEBSHARE_USER is not set. Run: export WEBSHARE_USER=...}"
: "${WEBSHARE_PASS:?WEBSHARE_PASS is not set. Run: export WEBSHARE_PASS=...}"

# ── GCloud project ────────────────────────────────────────────────────────────

echo "▶ Setting project: $PROJECT"
gcloud config set project "$PROJECT"

echo "▶ Enabling Cloud Run, Artifact Registry, and Cloud Build APIs…"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --quiet

# ── Artifact Registry repository ─────────────────────────────────────────────

echo "▶ Creating Artifact Registry repository '$REPO' (skips if already exists)…"
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --quiet 2>/dev/null || true

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}"

echo "▶ Configuring Docker auth for ${REGISTRY}..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ── Build & deploy API ────────────────────────────────────────────────────────

API_IMAGE="${REGISTRY}/${API_SERVICE}:latest"
echo ""
echo "── API ──────────────────────────────────────────────────────────────────"
echo "▶ Building API image..."
docker build --platform linux/amd64 -f api/Dockerfile -t "$API_IMAGE" .

echo "▶ Pushing API image…"
docker push "$API_IMAGE"

echo "▶ Deploying API to Cloud Run…"
gcloud run deploy "$API_SERVICE" \
  --image "$API_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY},WEBSHARE_USER=${WEBSHARE_USER},WEBSHARE_PASS=${WEBSHARE_PASS}" \
  --quiet

API_URL=$(gcloud run services describe "$API_SERVICE" \
  --region "$REGION" \
  --format "value(status.url)")
echo "✔ API live at: $API_URL"

# ── Build & deploy Streamlit app ──────────────────────────────────────────────

APP_IMAGE="${REGISTRY}/${APP_SERVICE}:latest"
echo ""
echo "── Streamlit app ────────────────────────────────────────────────────────"
echo "▶ Building Streamlit image..."
docker build --platform linux/amd64 -f streamlit_app/Dockerfile -t "$APP_IMAGE" .

echo "▶ Pushing Streamlit image…"
docker push "$APP_IMAGE"

echo "▶ Deploying Streamlit app to Cloud Run…"
gcloud run deploy "$APP_SERVICE" \
  --image "$APP_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8501 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 360 \
  --set-env-vars "API_URL=${API_URL}" \
  --quiet

APP_URL=$(gcloud run services describe "$APP_SERVICE" \
  --region "$REGION" \
  --format "value(status.url)")

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════"
echo "  Deployment complete!"
echo ""
echo "  App (Streamlit):  $APP_URL"
echo "  API (Flask):      $API_URL"
echo "  Swagger docs:     $API_URL/apidocs"
echo "════════════════════════════════════════════════════"
