"""In-process API integration tests.

These exercise HTTP → orchestration → tools → services together.
External Gemini and Cloud SQL are not called; repositories and the
LLM are replaced with in-memory doubles.
"""
