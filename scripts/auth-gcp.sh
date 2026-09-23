#!/usr/bin/env bash
# Authenticate gcloud for CourseCompass Cloud Run deploys.
#
# Preferred (Cloud Agents / CI): service account JSON key
#   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
#   ./scripts/auth-gcp.sh
#
# Interactive (browser):
#   ./scripts/auth-gcp.sh --login
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-}"

if [[ "${1:-}" == "--login" ]]; then
  echo "Opening browser-based gcloud login..."
  gcloud auth login --update-adc
else
  if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" \
        && -f "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
    echo "Activating service account from GOOGLE_APPLICATION_CREDENTIALS"
    gcloud auth activate-service-account \
      --key-file="${GOOGLE_APPLICATION_CREDENTIALS}"
  elif [[ -n "${GCP_SA_KEY_JSON:-}" ]]; then
    KEY_FILE="$(mktemp)"
    printf '%s' "${GCP_SA_KEY_JSON}" > "${KEY_FILE}"
    chmod 600 "${KEY_FILE}"
    echo "Activating service account from GCP_SA_KEY_JSON"
    gcloud auth activate-service-account --key-file="${KEY_FILE}"
    export GOOGLE_APPLICATION_CREDENTIALS="${KEY_FILE}"
  else
    echo "No credentials found."
    echo ""
    echo "Option A — service account (best for Cloud Agents):"
    echo "  1. Create a SA with Cloud Run Admin, Service Account User,"
    echo "     Artifact Registry Writer, and Cloud Build Editor."
    echo "  2. export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json"
    echo "     # or GCP_SA_KEY_JSON='{...}'"
    echo "  3. Re-run: ./scripts/auth-gcp.sh"
    echo ""
    echo "Option B — interactive user login:"
    echo "  ./scripts/auth-gcp.sh --login"
    exit 1
  fi
fi

if [[ -n "${PROJECT_ID}" ]]; then
  gcloud config set project "${PROJECT_ID}"
fi

echo ""
echo "Authenticated as:"
gcloud auth list
echo "Project: $(gcloud config get-value project 2>/dev/null || echo unset)"
