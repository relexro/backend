import os
# Ensure direct Gemini usage is enabled early so pytest sees env var before importing modules.
os.environ["USE_DIRECT_GEMINI"] = os.environ.get("USE_DIRECT_GEMINI", "1") 