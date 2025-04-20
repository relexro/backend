"""
Tests for LLM Integration Module
"""
import pytest
from datetime import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm_integration import (
    GeminiProcessor,
    GrokProcessor,
    LLMError,
    prepare_context,
    format_llm_response,
    process_with_gemini,
    process_with_grok,
    process_legal_query,
    maintain_conversation_history
)

# Test Data
@pytest.fixture
def sample_context():
    return {
        "case_type": "civil",
        "parties": ["Reclamant SA", "Pârât SRL"],
        "legal_basis": ["Art. 1350 Cod Civil", "Art. 1357 Cod Civil"],
        "precedents": ["Decizia 123/2023 ICCJ"],
        "claim_value": 50000.0
    }

@pytest.fixture
def sample_response():
    return {
        "analysis": "Analiza detaliată a cazului...",
        "recommendations": [
            "Recomandare 1",
            "Recomandare 2"
        ],
        "risk_factors": {
            "ridicat": ["Risc 1", "Risc 2"],
            "mediu": ["Risc 3"]
        }
    }

# Processor Tests
@pytest.mark.asyncio
async def test_gemini_processor_initialization():
    processor = GeminiProcessor(
        model_name="gemini-pro",
        temperature=0.7,
        max_tokens=2048
    )
    
    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini:
        await processor.initialize()
        mock_gemini.assert_called_once_with(
            model="gemini-pro",
            temperature=0.7,
            max_output_tokens=2048
        )

@pytest.mark.asyncio
async def test_grok_processor_initialization():
    processor = GrokProcessor(
        model_name="grok-1",
        temperature=0.8,
        max_tokens=4096
    )
    
    with patch("custom_grok_client.GrokClient") as mock_grok:
        await processor.initialize()
        mock_grok.assert_called_once_with(
            model="grok-1",
            temperature=0.8,
            max_tokens=4096
        )

# Context Preparation Tests
def test_prepare_context_complete(sample_context):
    prepared = prepare_context(sample_context)
    
    assert prepared["language"] == "ro"
    assert prepared["case_type"] == "civil"
    assert len(prepared["parties"]) == 2
    assert len(prepared["legal_basis"]) == 2
    assert prepared["claim_value"] == 50000.0
    assert "timestamp" in prepared

def test_prepare_context_partial():
    partial_context = {"case_type": "penal"}
    prepared = prepare_context(partial_context)
    
    assert prepared["language"] == "ro"
    assert prepared["case_type"] == "penal"
    assert "parties" not in prepared
    assert "timestamp" in prepared

# Response Formatting Tests
def test_format_llm_response_success(sample_response):
    formatted = format_llm_response(sample_response)
    
    assert "Analiză Juridică" in formatted
    assert "Recomandări" in formatted
    assert "Factori de Risc" in formatted
    assert "RIDICAT" in formatted
    assert "MEDIU" in formatted

def test_format_llm_response_error():
    error_response = {
        "error": "Eroare de procesare",
        "error_type": "ProcessingError"
    }
    formatted = format_llm_response(error_response)
    
    assert "Eroare:" in formatted
    assert "Tip eroare:" in formatted
    assert "ProcessingError" in formatted

# Processing Tests
@pytest.mark.asyncio
async def test_process_with_gemini(sample_context):
    processor = GeminiProcessor(
        model_name="gemini-pro",
        temperature=0.7,
        max_tokens=2048
    )
    
    mock_response = MagicMock()
    mock_response.content = "Răspuns de test de la Gemini"
    
    with patch.object(processor, "initialize"), \
         patch.object(processor, "model", new_callable=AsyncMock) as mock_model:
        mock_model.agenerate.return_value = [mock_response]
        
        result = await process_with_gemini(
            processor,
            sample_context,
            "Test prompt"
        )
        
        assert result == "Răspuns de test de la Gemini"
        assert mock_model.agenerate.called

@pytest.mark.asyncio
async def test_process_with_grok(sample_context):
    processor = GrokProcessor(
        model_name="grok-1",
        temperature=0.8,
        max_tokens=4096
    )
    
    mock_response = MagicMock()
    mock_response.content = "Răspuns de test de la Grok"
    
    with patch.object(processor, "initialize"), \
         patch.object(processor, "model", new_callable=AsyncMock) as mock_model:
        mock_model.generate.return_value = mock_response
        
        result = await process_with_grok(
            processor,
            sample_context,
            "Test prompt"
        )
        
        assert result == "Răspuns de test de la Grok"
        assert mock_model.generate.called

# Integration Tests
@pytest.mark.asyncio
async def test_process_legal_query(sample_context):
    with patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.return_value = "Analiză inițială"
        mock_grok.return_value = "Recomandări expert"
        
        result = await process_legal_query(
            sample_context,
            "Test query"
        )
        
        assert "initial_analysis" in result
        assert "expert_recommendations" in result
        assert "timestamp" in result
        assert mock_gemini.called
        assert mock_grok.called

@pytest.mark.asyncio
async def test_process_legal_query_error(sample_context):
    with patch("src.llm_integration.process_with_gemini") as mock_gemini:
        mock_gemini.side_effect = LLMError("Test error")
        
        result = await process_legal_query(
            sample_context,
            "Test query"
        )
        
        assert "error" in result
        assert "error_type" in result
        assert result["error_type"] == "LLMError"

# Session Management Tests
@pytest.mark.asyncio
async def test_maintain_conversation_history():
    history = []
    session_id = "test_session"
    
    # Add messages
    history = await maintain_conversation_history(
        session_id,
        "user",
        "Test message 1",
        history
    )
    assert len(history) == 1
    
    # Add more messages
    for i in range(15):
        history = await maintain_conversation_history(
            session_id,
            "assistant",
            f"Test message {i+2}",
            history
        )
    
    # Check window size
    assert len(history) == 10
    assert history[-1]["content"] == "Test message 16"
    assert all("timestamp" in msg for msg in history)

@pytest.mark.asyncio
async def test_error_handling():
    processor = GeminiProcessor(
        model_name="gemini-pro",
        temperature=0.7,
        max_tokens=2048
    )
    
    with patch.object(processor, "initialize") as mock_init:
        mock_init.side_effect = Exception("Test error")
        
        with pytest.raises(LLMError) as exc_info:
            await processor.initialize()
        
        assert "Eroare la inițializarea Gemini" in str(exc_info.value) 