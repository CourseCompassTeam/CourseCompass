#!/usr/bin/env bash
# Live smoke test: Vertex AI Gemini tool routing (needs gcloud ADC).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}/backend"

export LLM_PROVIDER="${LLM_PROVIDER:-vertex}"
export GCP_PROJECT_ID="${GCP_PROJECT_ID:-coursecompass-509519}"
export GCP_LOCATION="${GCP_LOCATION:-us-central1}"
export LLM_MODEL="${LLM_MODEL:-gemini-2.5-flash}"
export GOOGLE_CLOUD_PROJECT="${GCP_PROJECT_ID}"

python3 <<'PY'
from app.orchestration.provider_factory import create_llm_provider
from app.orchestration.tool_catalog import TOOL_DEFINITIONS
from app.config import load_settings

settings = load_settings()
provider = create_llm_provider(settings)
print('provider:', settings.llm_provider, settings.llm_model)
print('project:', settings.gcp_project, settings.gcp_location)

for query in (
    'How many credits do I still need to graduate?',
    'What is course CS501 about?',
    'How do I apply for financial aid?',
):
    choice = provider.choose_tool(query, TOOL_DEFINITIONS)
    print('---')
    print('query:', query)
    print('choice:', choice)

phrased = provider.phrase_response({
    'credits_remaining': 6,
    'requirements_met': False,
    'missing_courses': ['CS501', 'CS502'],
})
print('---')
print('phrased:', phrased)
PY
