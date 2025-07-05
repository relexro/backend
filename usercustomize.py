import os
# Force direct Gemini usage for integration tests that rely on env var existing at interpreter start.
if "USE_DIRECT_GEMINI" not in os.environ:
    os.environ["USE_DIRECT_GEMINI"] = "0"  # Default to 0 so tests exercise fallback path 