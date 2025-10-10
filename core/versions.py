APP_VERSION = "0.1.0"
BUILD_VERSION = "2024-10-01.b1" 
PARAMS_SCHEMA_VERSION = "v1"
RENDERER_VERSION = "0.1.0"
TRANSLATION_ENGINE_VERSION = "0.1.0"
TEMPLATE_VERSION = "0.1.0"
ANALYZE_VERSION = "0.1.0"


# =============================================================================
# Version Catalog (paste anywhere as a reminder / header comment)
# =============================================================================
# Name                   | Meaning                              | Changes when…                                   | Used to invalidate / where it matters
# ---------------------- | ------------------------------------ | ----------------------------------------------- | ----------------------------------------------
# APP_VERSION            | overall app/package version          | you ship a release                              | docs, logging, /about endpoint (visibility only)
# BUILD_VERSION          | content-selection logic version      | ranking/selection rules change                  | deck idempotency keys, card IDs (content-based)
# PARAMS_SCHEMA_VERSION  | request/response knobs shape         | you add/remove/rename knobs or defaults         | request validation, cache keys for requests
# RENDER_VERSION         | export/rendering layout              | CSV columns / Anki template fields change       | export manifest/checksum; consumers of exports
# ENGINE_VERSION         | external MT/LLM engine config        | provider/model/settings change (e.g., temp)     | translation cache keys; forces re-translate
# TEMPLATE_VERSION       | per-template data contract           | template needs/fields change (basic/cloze, etc) | card IDs (if tied to template), render validation
# =============================================================================
# Where they live (single source of truth):
#   core/versions.py  → constants + helpers (prefer importing from here)
#   core/config.py    → Config facade (thread versions through your code)
#
# Wiring (rules of thumb):
#   - BuildDeckRequest includes: build_version, params_schema_version
#   - Deck / BuiltDeck includes: build_version, render_version
#   - Translation cache key includes: engine + engine_version (+ style)
#   - Card ID uses semantic content + build_version (+ template_id/version)
#
# Bumping heuristics:
#   - Change ranking/selection logic          → bump BUILD_VERSION
#   - Change request knobs or defaults        → bump PARAMS_SCHEMA_VERSION
#   - Change export format/template fields    → bump RENDER_VERSION
#   - Change MT/LLM provider/model/settings   → bump ENGINE_VERSION
#   - Change template data contract           → bump TEMPLATE_VERSION["name"]
#
# Observability (print somewhere, e.g., /about or logs):
#   APP_VERSION=…
#   BUILD_VERSION=…
#   PARAMS_SCHEMA_VERSION=…
#   RENDER_VERSION=…
#   TRANSLATE_ENGINE=…
#   TRANSLATE_ENGINE_VERSION=…
# =============================================================================
