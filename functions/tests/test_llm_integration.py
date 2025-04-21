"""
Tests for LLM Integration Module
"""
import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import time

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
def complex_commercial_context():
    return {
        "case_type": "commercial",
        "parties": ["SC Tehnologie SRL", "SC Inovație SA"],
        "legal_basis": [
            "Art. 1270 Cod Civil",  # Contract binding force
            "Art. 1516 Cod Civil",  # Contract breach
            "Art. 243 Legea 31/1990"  # Company law
        ],
        "claim_value": 2500000.0,
        "contract_details": {
            "type": "software_development",
            "duration": "24 months",
            "milestones": ["Phase 1", "Phase 2", "Phase 3"],
            "payment_schedule": "quarterly"
        },
        "international_elements": True,
        "arbitration_clause": True
    }

@pytest.fixture
def labor_dispute_context():
    return {
        "case_type": "labor",
        "parties": ["Ion Popescu", "Angajator Plus SRL"],
        "legal_basis": [
            "Art. 55 Codul Muncii",  # Termination
            "Art. 76 Codul Muncii"   # Notice period
        ],
        "claim_value": 75000.0,
        "employment_details": {
            "position": "Senior Developer",
            "contract_type": "unlimited",
            "duration": "3 years",
            "termination_reason": "restructuring"
        },
        "discrimination_claim": True,
        "collective_agreement": True
    }

@pytest.fixture
def administrative_context():
    return {
        "case_type": "administrative",
        "parties": ["Petent SRL", "Primăria Sector 1"],
        "legal_basis": [
            "Art. 7 Legea 554/2004",  # Administrative litigation
            "Art. 2 OG 27/2002"       # Petitions
        ],
        "claim_value": 0,  # Non-monetary claim
        "administrative_act": {
            "type": "building_permit",
            "number": "123/2024",
            "date_issued": "2024-01-15",
            "challenged_aspects": ["procedural_errors", "excess_of_power"]
        },
        "urgency": True,
        "public_interest": True
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

# State Management Tests
@pytest.fixture
def firestore_case_state():
    return {
        "case_id": "case_123",
        "processing_state": {
            "current_node": "legal_analysis",
            "completed_nodes": ["input_analysis", "quota_check"],
            "conversation_history": [
                {
                    "role": "user",
                    "content": "Initial query about contract dispute",
                    "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat()
                },
                {
                    "role": "assistant",
                    "content": "Initial analysis completed",
                    "timestamp": (datetime.now() - timedelta(minutes=4)).isoformat()
                }
            ],
            "last_update": datetime.now().isoformat(),
            "pending_operations": ["research_query", "draft_generation"]
        },
        "user_id": "user_456",
        "organization_id": "org_789"
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

# Domain-Specific Processing Tests
@pytest.mark.asyncio
async def test_process_commercial_dispute(complex_commercial_context):
    processor = GeminiProcessor(
        model_name="gemini-pro",
        temperature=0.7,
        max_tokens=2048
    )
    
    mock_response = MagicMock()
    mock_response.content = """
Analiză Contract Software:
1. Clauze esențiale identificate
2. Riscuri de implementare
3. Implicații transfrontaliere
4. Procedură arbitrală aplicabilă
"""
    
    with patch.object(processor, "initialize"), \
         patch.object(processor, "model", new_callable=AsyncMock) as mock_model:
        mock_model.agenerate.return_value = [mock_response]
        
        result = await process_with_gemini(
            processor,
            complex_commercial_context,
            "Analizează implicațiile juridice ale contractului de dezvoltare software"
        )
        
        assert "Contract Software" in result
        assert "Riscuri de implementare" in result
        assert "Implicații transfrontaliere" in result
        mock_model.agenerate.assert_called_once()

@pytest.mark.asyncio
async def test_process_labor_discrimination(labor_dispute_context):
    processor = GrokProcessor(
        model_name="grok-1",
        temperature=0.8,
        max_tokens=4096
    )
    
    mock_response = MagicMock()
    mock_response.content = """
Analiză Discriminare:
1. Elemente constitutive
2. Jurisprudență relevantă
3. Sarcina probei
4. Măsuri reparatorii
"""
    
    with patch.object(processor, "initialize"), \
         patch.object(processor, "model", new_callable=AsyncMock) as mock_model:
        mock_model.generate.return_value = mock_response
        
        result = await process_with_grok(
            processor,
            labor_dispute_context,
            "Evaluează elementele de discriminare și recomandă strategia juridică"
        )
        
        assert "Analiză Discriminare" in result
        assert "Jurisprudență relevantă" in result
        assert "Sarcina probei" in result
        mock_model.generate.assert_called_once()

@pytest.mark.asyncio
async def test_process_urgent_administrative(administrative_context):
    """Test processing of urgent administrative case with public interest."""
    with patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.return_value = """
Analiza preliminară indică necesitatea procedurii de urgență conform Art. 14-15 din Legea 554/2004.
Elementele de interes public identificate: impact asupra dezvoltării urbane, siguranță publică.
"""
        mock_grok.return_value = """
Recomandări pentru procedura de urgență:
1. Cerere de suspendare act administrativ
2. Dovezi pentru prejudiciul iminent
3. Argumentare interes public
"""
        
        result = await process_legal_query(
            administrative_context,
            "Analizează condițiile suspendării actului administrativ"
        )
        
        assert "procedura de urgență" in result["initial_analysis"].lower()
        assert "interes public" in result["initial_analysis"].lower()
        assert "cerere de suspendare" in result["expert_recommendations"].lower()
        assert mock_gemini.called
        assert mock_grok.called

# Edge Cases and Error Handling
@pytest.mark.asyncio
async def test_process_with_empty_context():
    """Test processing with empty context."""
    empty_context = {}
    
    with pytest.raises(LLMError) as exc_info:
        await process_legal_query(empty_context, "Analizează cazul")
    
    assert "context" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_process_with_invalid_claim_value():
    """Test processing with invalid claim value."""
    invalid_context = {
        "case_type": "civil",
        "claim_value": "invalid"
    }
    
    prepared = prepare_context(invalid_context)
    assert "claim_value" not in prepared

@pytest.mark.asyncio
async def test_process_with_special_characters():
    """Test processing with special characters in context."""
    special_context = {
        "case_type": "civil",
        "parties": ["SC Test & Co. SRL", "John's Company Ltd."],
        "legal_basis": ["Art. 1350 § 2 Cod Civil"]
    }
    
    processor = GeminiProcessor(
        model_name="gemini-pro",
        temperature=0.7,
        max_tokens=2048
    )
    
    mock_response = MagicMock()
    mock_response.content = "Răspuns formatat corect"
    
    with patch.object(processor, "initialize"), \
         patch.object(processor, "model", new_callable=AsyncMock) as mock_model:
        mock_model.agenerate.return_value = [mock_response]
        
        result = await process_with_gemini(
            processor,
            special_context,
            "Test prompt"
        )
        
        assert result == "Răspuns formatat corect"

@pytest.mark.asyncio
async def test_process_with_long_history():
    """Test processing with long conversation history."""
    history = []
    session_id = "test_session"
    
    # Add 20 messages (beyond the 10 message limit)
    for i in range(20):
        history = await maintain_conversation_history(
            session_id,
            "user" if i % 2 == 0 else "assistant",
            f"Message {i+1} with some detailed legal analysis...",
            history
        )
    
    assert len(history) == 10  # Should maintain only last 10 messages
    assert history[0]["content"].startswith("Message 11")  # Should start from 11th message
    assert history[-1]["content"].startswith("Message 20")  # Should end with 20th message

@pytest.mark.asyncio
async def test_state_recovery(firestore_case_state):
    """Test recovery of processing state from Firestore."""
    with patch("src.llm_integration.get_case_details") as mock_get_case, \
         patch("src.llm_integration.process_with_gemini") as mock_gemini:
        
        mock_get_case.return_value = firestore_case_state
        mock_gemini.return_value = "Continuing analysis from previous state..."
        
        # Simulate processing with recovered state
        processor = GeminiProcessor(
            model_name="gemini-pro",
            temperature=0.7,
            max_tokens=2048
        )
        
        context = {
            **firestore_case_state["processing_state"],
            "case_type": "commercial",
            "resume_from": "legal_analysis"
        }
        
        result = await process_with_gemini(
            processor,
            context,
            "Continue analysis from previous state"
        )
        
        assert "Continuing analysis" in result
        mock_get_case.assert_called_once_with(firestore_case_state["case_id"])
        
@pytest.mark.asyncio
async def test_state_persistence():
    """Test persistence of processing state to Firestore."""
    case_id = "case_123"
    current_state = {
        "current_node": "expert_consultation",
        "completed_nodes": ["input_analysis", "legal_analysis"],
        "conversation_history": [
            {
                "role": "user",
                "content": "Query about employment contract",
                "timestamp": datetime.now().isoformat()
            }
        ]
    }
    
    with patch("src.llm_integration.update_case_details") as mock_update_case:
        # Simulate processing that needs to save state
        processor = GrokProcessor(
            model_name="grok-1",
            temperature=0.8,
            max_tokens=4096
        )
        
        mock_response = MagicMock()
        mock_response.content = "Expert analysis in progress..."
        
        with patch.object(processor, "initialize"), \
             patch.object(processor, "model", new_callable=AsyncMock) as mock_model:
            mock_model.generate.return_value = mock_response
            
            await process_with_grok(
                processor,
                {"case_id": case_id, **current_state},
                "Provide expert consultation"
            )
            
            mock_update_case.assert_called_once()
            call_args = mock_update_case.call_args[0][1]
            assert "processing_state" in call_args
            assert call_args["processing_state"]["current_node"] == "expert_consultation"

@pytest.mark.asyncio
async def test_timeout_handling():
    """Test handling of processing timeout."""
    with patch("src.llm_integration.update_case_details") as mock_update_case, \
         patch("src.llm_integration.process_with_gemini") as mock_gemini:
        
        mock_gemini.side_effect = asyncio.TimeoutError("Processing timeout")
        
        case_id = "case_123"
        current_state = {
            "current_node": "legal_analysis",
            "retry_count": 0
        }
        
        with pytest.raises(LLMError) as exc_info:
            await process_legal_query(
                {"case_id": case_id, **current_state},
                "Analyze contract terms"
            )
        
        assert "timeout" in str(exc_info.value).lower()
        mock_update_case.assert_called_once()
        call_args = mock_update_case.call_args[0][1]
        assert call_args["processing_state"]["timeout_occurred"] is True

@pytest.mark.asyncio
async def test_concurrent_processing():
    """Test handling of concurrent processing requests."""
    case_id = "case_123"
    
    with patch("src.llm_integration.get_case_details") as mock_get_case, \
         patch("src.llm_integration.update_case_details") as mock_update_case:
        
        mock_get_case.return_value = {
            "processing_state": {
                "is_processing": True,
                "started_at": (datetime.now() - timedelta(minutes=1)).isoformat()
            }
        }
        
        with pytest.raises(LLMError) as exc_info:
            await process_legal_query(
                {"case_id": case_id},
                "New analysis request"
            )
        
        assert "already processing" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_state_cleanup():
    """Test cleanup of processing state after completion."""
    case_id = "case_123"
    
    with patch("src.llm_integration.update_case_details") as mock_update_case, \
         patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.return_value = "Initial analysis complete"
        mock_grok.return_value = "Expert recommendations provided"
        
        result = await process_legal_query(
            {"case_id": case_id},
            "Analyze case"
        )
        
        # Verify final state update
        final_call_args = mock_update_case.call_args_list[-1][0][1]
        assert "processing_state" in final_call_args
        assert final_call_args["processing_state"]["completed"] is True
        assert "completion_time" in final_call_args["processing_state"]

@pytest.mark.asyncio
async def test_draft_generation_state():
    """Test state management during draft generation."""
    case_id = "case_123"
    
    with patch("src.llm_integration.update_case_details") as mock_update_case, \
         patch("src.llm_integration.process_legal_query") as mock_process:
        
        mock_process.return_value = {
            "initial_analysis": "Analysis complete",
            "expert_recommendations": "Recommendations provided",
            "drafts_generated": True
        }
        
        result = await process_legal_query(
            {
                "case_id": case_id,
                "generate_drafts": True
            },
            "Analyze and prepare drafts"
        )
        
        assert result["drafts_generated"] is True
        final_call_args = mock_update_case.call_args_list[-1][0][1]
        assert final_call_args["drafts_ready"] is True

# LangGraph Node Transition Tests
@pytest.mark.asyncio
async def test_node_transition_success():
    """Test successful transition between LangGraph nodes."""
    with patch("src.llm_integration.update_case_details") as mock_update:
        initial_state = {
            "case_id": "case_123",
            "current_node": "input_analysis",
            "completed_nodes": [],
            "node_results": {}
        }
        
        # Simulate node execution
        result = await process_legal_query(
            initial_state,
            "Analyze contract dispute"
        )
        
        # Verify state updates
        final_call_args = mock_update.call_args_list[-1][0][1]
        assert "current_node" in final_call_args
        assert len(final_call_args["completed_nodes"]) > 0
        assert "node_results" in final_call_args

@pytest.mark.asyncio
async def test_node_error_recovery():
    """Test recovery from node execution errors."""
    with patch("src.llm_integration.update_case_details") as mock_update, \
         patch("src.llm_integration.process_with_gemini") as mock_gemini:
        
        mock_gemini.side_effect = [
            LLMError("First attempt failed"),  # First attempt fails
            "Successful analysis"  # Retry succeeds
        ]
        
        initial_state = {
            "case_id": "case_123",
            "current_node": "legal_analysis",
            "retry_count": 0,
            "error_nodes": []
        }
        
        result = await process_legal_query(
            initial_state,
            "Analyze case"
        )
        
        # Verify retry logic
        assert mock_gemini.call_count == 2
        final_state = mock_update.call_args_list[-1][0][1]
        assert "retry_count" in final_state
        assert final_state["retry_count"] == 1

@pytest.mark.asyncio
async def test_complex_state_recovery():
    """Test recovery of complex processing state with multiple nodes."""
    complex_state = {
        "case_id": "case_123",
        "current_node": "expert_consultation",
        "completed_nodes": ["input_analysis", "legal_analysis"],
        "node_results": {
            "input_analysis": {"classification": "commercial", "priority": "high"},
            "legal_analysis": {"relevant_articles": ["Art. 1350", "Art. 1357"]}
        },
        "conversation_history": [
            {
                "role": "user",
                "content": "Complex commercial dispute analysis",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": "Initial legal framework identified",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "metadata": {
            "started_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "processing_time": 120.5
        }
    }
    
    with patch("src.llm_integration.get_case_details") as mock_get_case, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_get_case.return_value = complex_state
        mock_grok.return_value = "Resuming expert consultation..."
        
        result = await process_legal_query(
            {"case_id": "case_123", "resume": True},
            "Continue analysis"
        )
        
        assert "expert_consultation" in result
        assert len(result["completed_nodes"]) >= 3
        assert all(key in result["node_results"] for key in ["input_analysis", "legal_analysis", "expert_consultation"])

# Performance Benchmarking Tests
@pytest.mark.asyncio
async def test_processing_performance():
    """Test processing performance metrics."""
    start_time = time.time()
    
    with patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.return_value = "Quick initial analysis"
        mock_grok.return_value = "Fast expert response"
        
        result = await process_legal_query(
            {"case_id": "case_123", "track_performance": True},
            "Performance test query"
        )
        
        processing_time = time.time() - start_time
        
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert "performance_metrics" in result
        assert all(metric in result["performance_metrics"] for metric in [
            "total_processing_time",
            "gemini_processing_time",
            "grok_processing_time"
        ])

@pytest.mark.asyncio
async def test_concurrent_load_handling():
    """Test handling of multiple concurrent requests."""
    num_requests = 5
    tasks = []
    
    with patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.return_value = "Concurrent analysis"
        mock_grok.return_value = "Concurrent expert response"
        
        for i in range(num_requests):
            tasks.append(
                process_legal_query(
                    {"case_id": f"case_{i}", "track_performance": True},
                    f"Concurrent request {i}"
                )
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_requests = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_requests > 0
        assert all("performance_metrics" in r for r in results if not isinstance(r, Exception))

# Error Recovery Strategy Tests
@pytest.mark.asyncio
async def test_gradual_backoff():
    """Test gradual backoff strategy for retries."""
    with patch("src.llm_integration.process_with_gemini") as mock_gemini:
        mock_gemini.side_effect = [
            LLMError("First failure"),
            LLMError("Second failure"),
            "Success on third try"
        ]
        
        start_time = time.time()
        result = await process_legal_query(
            {
                "case_id": "case_123",
                "retry_strategy": "gradual_backoff",
                "max_retries": 3
            },
            "Test query"
        )
        
        total_time = time.time() - start_time
        assert mock_gemini.call_count == 3
        assert total_time >= 0.6  # Should include backoff delays

@pytest.mark.asyncio
async def test_fallback_model():
    """Test fallback to alternative model on failure."""
    with patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.side_effect = LLMError("Primary model failed")
        mock_grok.return_value = "Fallback model response"
        
        result = await process_legal_query(
            {
                "case_id": "case_123",
                "enable_fallback": True
            },
            "Test query"
        )
        
        assert "fallback_model_used" in result
        assert result["fallback_model_used"] is True
        assert mock_grok.called

@pytest.mark.asyncio
async def test_partial_results_recovery():
    """Test recovery and aggregation of partial results."""
    with patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.side_effect = [
            "Partial analysis 1",
            LLMError("Error during part 2"),
            "Partial analysis 3"
        ]
        
        mock_grok.return_value = "Expert insights on partial results"
        
        result = await process_legal_query(
            {
                "case_id": "case_123",
                "allow_partial_results": True
            },
            "Complex analysis request"
        )
        
        assert "partial_results" in result
        assert len(result["partial_results"]) >= 2
        assert "aggregated_analysis" in result

# Specialized Legal Domain Tests
@pytest.mark.asyncio
async def test_constitutional_law_processing():
    """Test processing of constitutional law cases."""
    constitutional_context = {
        "case_type": "constitutional",
        "legal_basis": ["Art. 21 Constituție", "Art. 52 Constituție"],
        "public_interest": True,
        "fundamental_rights": ["access_to_justice", "fair_trial"],
        "precedents": ["Decizia CCR 123/2023"]
    }
    
    with patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.return_value = """
Analiză constituțională:
1. Drepturi fundamentale afectate
2. Jurisprudență CCR relevantă
3. Impact asupra ordinii constituționale
"""
        mock_grok.return_value = "Recomandări pentru argumentare constituțională"
        
        result = await process_legal_query(
            constitutional_context,
            "Analizează aspectele constituționale"
        )
        
        assert "constituțională" in result["initial_analysis"].lower()
        assert "drepturi fundamentale" in result["initial_analysis"].lower()
        assert mock_gemini.called
        assert mock_grok.called

@pytest.mark.asyncio
async def test_eu_law_integration():
    """Test processing of cases with EU law elements."""
    eu_law_context = {
        "case_type": "commercial",
        "eu_law_elements": True,
        "legal_basis": [
            "Art. 101 TFUE",
            "Regulamentul UE 2016/679",
            "Directiva 93/13/CEE"
        ],
        "cjeu_precedents": ["C-434/15", "C-673/16"],
        "cross_border": True
    }
    
    with patch("src.llm_integration.process_with_gemini") as mock_gemini, \
         patch("src.llm_integration.process_with_grok") as mock_grok:
        
        mock_gemini.return_value = """
Analiză drept UE:
1. Aplicabilitate directă norme UE
2. Jurisprudență CJUE relevantă
3. Principii interpretare uniformă
"""
        mock_grok.return_value = "Recomandări pentru aplicarea dreptului UE"
        
        result = await process_legal_query(
            eu_law_context,
            "Analizează elementele de drept UE"
        )
        
        assert "drept ue" in result["initial_analysis"].lower()
        assert "cjue" in result["initial_analysis"].lower()
        assert mock_gemini.called
        assert mock_grok.called 