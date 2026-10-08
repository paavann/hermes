# Hermes DB — AI Agent Context

## 1. Architectural Boundary
`hermes-db` is strictly a low-level data access layer.
- **Unidirectional Dependency**: It must NEVER import anything from consumer applications (`apps/hermes-api`, `apps/hermes`). 
- **No Domain Logic**: Business workflows and AI logic belong in the apps. *(Note: `CREDIBILITY_WEIGHTS` and `run_lifecycle_transitions` currently live here, which is recognized technical debt slated for relocation. Do not introduce new domain logic).*

## 2. Inversion of Control (IoC)
To prevent environment configuration drift, host apps (API/Worker) own environment variables. They pass their validated database URL to `init_db(db_url)`, which dynamically rebinds the asynchronous connection pool in-place. Standalone CLI commands (like Alembic migrations) use an internal `Settings` fallback to read `.env.development`.

## 3. Spatial & Vector Precision Rationale
- **HALFVEC(2048)**: Embeddings use 16-bit half-precision floats (`halfvec`) instead of 32-bit floats. This halves memory overhead with zero loss in retrieval quality for the Nemotron embedding model.
- **Cosine Threshold**: Duplicate semantic matching is tuned to `cosine_distance < 0.25`.
- **Geometry Extraction**: Viewport bounding box queries extract coordinate floats directly in PostGIS using `ST_X` and `ST_Y` to bypass expensive client-side WKB deserialization.
