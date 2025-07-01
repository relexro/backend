import pytest
from functions.src.gemini_direct import gemini_generate_rest

@pytest.mark.asyncio
async def test_gemini_generate_rest_basic():
    """Test direct Gemini REST API returns a non-empty string with a minimal English prompt."""
    prompt = "Hello world"
    result = await gemini_generate_rest(prompt, model_name="gemini-2.5-flash", temperature=1.0, max_tokens=256)
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    print("Gemini REST output:", result[:200]) 