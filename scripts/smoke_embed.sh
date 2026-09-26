#!/usr/bin/env bash
# Live smoke test: gemini-embedding-001 at 768 dims (needs gcloud ADC).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}/backend"

export LLM_PROVIDER="${LLM_PROVIDER:-vertex}"
export GCP_PROJECT_ID="${GCP_PROJECT_ID:-coursecompass-509519}"
export GCP_LOCATION="${GCP_LOCATION:-us-central1}"
export EMBEDDING_MODEL="${EMBEDDING_MODEL:-gemini-embedding-001}"
export EMBEDDING_DIMENSIONS="${EMBEDDING_DIMENSIONS:-768}"
export GOOGLE_CLOUD_PROJECT="${GCP_PROJECT_ID}"

python3 <<'PY'
from app.config import load_settings
from app.embeddings.embedding_provider import TASK_DOCUMENT
from app.orchestration.provider_factory import create_embedding_provider

settings = load_settings()
provider = create_embedding_provider(settings)
print('model:', settings.embedding_model)
print('dimensions:', settings.embedding_dimensions)
print('project:', settings.gcp_project, settings.gcp_location)

query = provider.embed('cloud computing')
doc = provider.embed(
    'Design and implementation of software systems.',
    task=TASK_DOCUMENT,
)
print('query_len:', len(query))
print('doc_len:', len(doc))
print('query_head:', [round(x, 5) for x in query[:4]])
PY
