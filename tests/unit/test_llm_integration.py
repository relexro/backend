import sys
from unittest.mock import MagicMock
sys.modules['custom_grok_client'] = MagicMock()

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import os
from datetime import datetime

import functions.src.llm_integration as llm

# --- Fixtures and helpers ---
@pytest.fixture(autouse=True)
def patch_datetime_now(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 1, 1, 12, 0, 0)
    monkeypatch.setattr(llm, 'datetime', FixedDatetime)

@pytest.fixture
def gemini_env(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-key')
    yield
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)

# --- Tests for prepare_context ---
def test_prepare_context_minimal():
    ctx = {}
    result = llm.prepare_context(ctx)
    assert result['language'] == 'ro'
    assert 'timestamp' in result
    assert len(result) == 2

def test_prepare_context_full():
    ctx = {
        'case_type': 'civil',
        'parties': ['A', 'B'],
        'legal_basis': [123, 'art. 45'],
        'precedents': ['case1'],
        'claim_value': '1000.5',
    }
    result = llm.prepare_context(ctx)
    assert result['case_type'] == 'civil'
    assert result['parties'] == ['A', 'B']
    assert result['legal_basis'] == ['123', 'art. 45']
    assert result['precedents'] == ['case1']
    assert result['claim_value'] == 1000.5

# --- Tests for format_llm_response ---
def test_format_llm_response_error():
    resp = {'error': 'fail', 'error_type': 'TestError'}
    out = llm.format_llm_response(resp)
    assert 'Eroare: fail' in out
    assert 'Tip eroare: TestError' in out

def test_format_llm_response_full():
    resp = {
        'analysis': 'Legal analysis',
        'recommendations': ['Do X', 'Do Y'],
        'risk_factors': {'high': ['risk1'], 'low': ['risk2']}
    }
    out = llm.format_llm_response(resp)
    assert 'Analiză Juridică' in out
    assert 'Recomandări' in out
    assert '- Do X' in out
    assert 'Factori de Risc' in out
    assert 'HIGH:' in out and '- risk1' in out
    assert 'LOW:' in out and '- risk2' in out

# --- Tests for GeminiProcessor and GrokProcessor ---
@pytest.mark.asyncio
async def test_gemini_processor_initialize_success(gemini_env):
    with patch('functions.src.llm_integration.ChatGoogleGenerativeAI') as mock_model:
        proc = llm.GeminiProcessor('gemini-pro', 0.7, 2048)
        await proc.initialize()
        mock_model.assert_called_once_with(
            model='gemini-pro', temperature=0.7, max_output_tokens=2048, google_api_key='fake-key'
        )
        assert hasattr(proc, 'model')

@pytest.mark.asyncio
async def test_gemini_processor_initialize_no_key(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    proc = llm.GeminiProcessor('gemini-pro', 0.7, 2048)
    with pytest.raises(llm.LLMError) as exc_info:
        await proc.initialize()
    assert "GEMINI_API_KEY environment variable is required" in str(exc_info.value)

@pytest.mark.asyncio
async def test_grok_processor_initialize_success():
    with patch('functions.src.llm_integration.GrokClient') as mock_client:
        proc = llm.GrokProcessor('grok-1', 0.8, 4096)
        await proc.initialize()
        mock_client.assert_called_once_with(model='grok-1', temperature=0.8, max_tokens=4096)
        assert hasattr(proc, 'model')

# --- Tests for process_with_gemini ---
@pytest.mark.asyncio
async def test_process_with_gemini_success(gemini_env):
    proc = llm.GeminiProcessor('gemini-pro', 0.7, 2048)
    with patch('functions.src.llm_integration.ChatGoogleGenerativeAI') as mock_model:
        mock_instance = mock_model.return_value
        mock_instance.agenerate = AsyncMock(return_value=[MagicMock(content='Gemini response')])
        result = await llm.process_with_gemini(proc, {'case_type': 'civil'}, 'Test prompt')
        assert result == 'Gemini response'

@pytest.mark.asyncio
async def test_process_with_gemini_no_response(gemini_env):
    proc = llm.GeminiProcessor('gemini-pro', 0.7, 2048)
    with patch('functions.src.llm_integration.ChatGoogleGenerativeAI') as mock_model:
        mock_instance = mock_model.return_value
        mock_instance.agenerate = AsyncMock(return_value=[MagicMock(content='')])
        with pytest.raises(llm.LLMError):
            await llm.process_with_gemini(proc, {}, 'Prompt')

@pytest.mark.asyncio
async def test_process_with_gemini_error(gemini_env):
    proc = llm.GeminiProcessor('gemini-pro', 0.7, 2048)
    with patch('functions.src.llm_integration.ChatGoogleGenerativeAI') as mock_model:
        mock_instance = mock_model.return_value
        mock_instance.agenerate = AsyncMock(side_effect=Exception('API fail'))
        with pytest.raises(llm.LLMError):
            await llm.process_with_gemini(proc, {}, 'Prompt')

# --- Tests for process_with_grok ---
@pytest.mark.asyncio
async def test_process_with_grok_success():
    proc = llm.GrokProcessor('grok-1', 0.8, 4096)
    with patch('functions.src.llm_integration.GrokClient') as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.generate = AsyncMock(return_value=MagicMock(content='Grok response'))
        result = await llm.process_with_grok(proc, {'case_type': 'civil'}, 'Prompt')
        assert result == 'Grok response'

@pytest.mark.asyncio
async def test_process_with_grok_no_response():
    proc = llm.GrokProcessor('grok-1', 0.8, 4096)
    with patch('functions.src.llm_integration.GrokClient') as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.generate = AsyncMock(return_value=MagicMock(content=''))
        with pytest.raises(llm.LLMError):
            await llm.process_with_grok(proc, {}, 'Prompt')

@pytest.mark.asyncio
async def test_process_with_grok_error():
    proc = llm.GrokProcessor('grok-1', 0.8, 4096)
    with patch('functions.src.llm_integration.GrokClient') as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.generate = AsyncMock(side_effect=Exception('API fail'))
        with pytest.raises(llm.LLMError):
            await llm.process_with_grok(proc, {}, 'Prompt')

# --- Tests for process_legal_query ---
@pytest.mark.asyncio
async def test_process_legal_query_success():
    with patch('functions.src.llm_integration.process_with_gemini', new=AsyncMock(return_value='Gemini A')):
        with patch('functions.src.llm_integration.process_with_grok', new=AsyncMock(return_value='Grok B')):
            result = await llm.process_legal_query({'case_type': 'civil'}, 'Q?')
            assert result['initial_analysis'] == 'Gemini A'
            assert result['expert_recommendations'] == 'Grok B'
            assert 'timestamp' in result

@pytest.mark.asyncio
async def test_process_legal_query_error():
    with patch('functions.src.llm_integration.process_with_gemini', new=AsyncMock(side_effect=Exception('fail'))):
        result = await llm.process_legal_query({}, 'Q?')
        assert result['error'] == 'fail'
        assert result['error_type'] == 'Exception'
        assert 'timestamp' in result

# --- Tests for maintain_conversation_history ---
@pytest.mark.asyncio
async def test_maintain_conversation_history_trims():
    history = [{'role': 'user', 'content': 'A', 'timestamp': 't'}] * 12
    result = await llm.maintain_conversation_history('sess', 'assistant', 'B', history)
    assert len(result) == 10
    assert result[-1]['role'] == 'assistant'
    assert result[-1]['content'] == 'B' 