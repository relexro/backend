"""
Unit Tests for Agent Tools Module
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from functions.src.agent_tools import (
    check_quota,
    get_case_details,
    update_case_details,
    get_party_id_by_name,
    query_bigquery,
    generate_draft_pdf,
    create_support_ticket,
    consult_grok,
    verify_payment,
    search_legal_database,
    get_relevant_legislation,
    update_quota_usage,
    QuotaError,
    PaymentError,
    DatabaseError,
    GrokAPIError,
    PDFGenerationError
)

# Test Data Fixtures
@pytest.fixture
def sample_case_data():
    return {
        "case_id": "case_123",
        "user_id": "user_456",
        "organization_id": "org_789",
        "case_type": "civil",
        "parties": [
            {"name": "Reclamant SA", "role": "plaintiff"},
            {"name": "Pârât SRL", "role": "defendant"}
        ],
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

@pytest.fixture
def sample_user_data():
    return {
        "user_id": "user_456",
        "organization_id": "org_789",
        "quota": {
            "monthly_limit": 100,
            "used_this_month": 45,
            "reset_date": (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()
        },
        "subscription": {
            "status": "active",
            "plan": "professional"
        }
    }

@pytest.fixture
def sample_org_data():
    return {
        "organization_id": "org_789",
        "name": "Law Firm SRL",
        "quota": {
            "monthly_limit": 1000,
            "used_this_month": 450,
            "reset_date": (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()
        },
        "subscription": {
            "status": "active",
            "plan": "enterprise"
        }
    }

# Quota Check Tests
@pytest.mark.asyncio
async def test_check_quota_success(sample_user_data, sample_org_data):
    """Test successful quota check."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_user_data)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        result = await check_quota("user_456", "org_789")
        assert result["has_quota"] is True
        assert result["remaining_quota"] == 55

@pytest.mark.asyncio
async def test_check_quota_exceeded():
    """Test quota exceeded scenario."""
    exceeded_quota = {
        "quota": {
            "monthly_limit": 100,
            "used_this_month": 100
        },
        "subscription": {"status": "active"}
    }

    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: exceeded_quota)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        with pytest.raises(QuotaError) as exc_info:
            await check_quota("user_456", "org_789")
        assert "Quota exceeded" in str(exc_info.value)

# Case Details Tests
@pytest.mark.asyncio
async def test_get_case_details_success(sample_case_data):
    """Test successful case details retrieval."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_case_data)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        result = await get_case_details("case_123")
        assert result["case_id"] == "case_123"
        assert result["case_type"] == "civil"
        assert len(result["parties"]) == 2

@pytest.mark.asyncio
async def test_get_case_details_not_found():
    """Test case not found scenario."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=False)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        with pytest.raises(DatabaseError) as exc_info:
            await get_case_details("nonexistent_case")
        assert "Case not found" in str(exc_info.value)

# Update Case Details Tests
@pytest.mark.asyncio
async def test_update_case_details_success(sample_case_data):
    """Test successful case details update."""
    update_data = {
        "status": "in_progress",
        "last_activity": datetime.now().isoformat()
    }

    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_case_data)
        mock_doc.update = AsyncMock()
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        result = await update_case_details("case_123", update_data)
        assert result["status"] == "success"
        mock_doc.update.assert_called_once()

# Party ID Tests
@pytest.mark.asyncio
async def test_get_party_id_by_name_success(sample_case_data):
    """Test successful party ID retrieval."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_case_data)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        result = await get_party_id_by_name("case_123", "Reclamant SA")
        assert result["party_role"] == "plaintiff"

# BigQuery Tests
@pytest.mark.asyncio
async def test_query_bigquery_success():
    """Test successful BigQuery query execution."""
    mock_results = [
        {"case_number": "123/2023", "court": "Tribunal București", "summary": "Test case"}
    ]

    with patch("google.cloud.bigquery.Client") as mock_bq:
        mock_bq.return_value.query.return_value.result.return_value = mock_results

        result = await query_bigquery("SELECT * FROM cases LIMIT 1")
        assert len(result) == 1
        assert result[0]["case_number"] == "123/2023"

# PDF Generation Tests
@pytest.mark.asyncio
async def test_generate_draft_pdf_success(sample_case_data):
    """Test successful PDF generation."""
    with patch("weasyprint.HTML") as mock_weasyprint, \
         patch("google.cloud.storage.Client") as mock_storage, \
         patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:

        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_case_data)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test.pdf"
        mock_storage.return_value.bucket().blob.return_value = mock_blob

        result = await generate_draft_pdf(
            case_id="case_123",
            content="# Test Content",
            draft_name="test_draft"
        )

        assert result["status"] == "success"
        assert "url" in result
        assert "storage_path" in result

@pytest.mark.asyncio
async def test_generate_draft_pdf_error():
    """Test PDF generation error handling."""
    with patch("weasyprint.HTML") as mock_weasyprint:
        mock_weasyprint.side_effect = Exception("PDF generation failed")

        with pytest.raises(PDFGenerationError) as exc_info:
            await generate_draft_pdf(
                case_id="case_123",
                content="# Test Content",
                draft_name="test_draft"
            )
        assert "PDF generation failed" in str(exc_info.value)

# Support Ticket Tests
@pytest.mark.asyncio
async def test_create_support_ticket_success():
    """Test successful support ticket creation."""
    ticket_data = {
        "title": "Test Issue",
        "description": "Test description",
        "priority": "high"
    }

    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.set = AsyncMock()
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        result = await create_support_ticket(ticket_data)
        assert result["status"] == "success"
        assert "ticket_id" in result

# Grok Integration Tests
@pytest.mark.asyncio
async def test_consult_grok_success():
    """Test successful Grok consultation."""
    with patch("custom_grok_client.GrokClient") as mock_grok:
        mock_grok.return_value.generate.return_value = "Expert legal analysis"

        result = await consult_grok("Test query", {"context": "test"})
        assert result["status"] == "success"
        assert "response" in result

@pytest.mark.asyncio
async def test_consult_grok_error():
    """Test Grok API error handling."""
    with patch("custom_grok_client.GrokClient") as mock_grok:
        mock_grok.return_value.generate.side_effect = Exception("API error")

        with pytest.raises(GrokAPIError) as exc_info:
            await consult_grok("Test query", {"context": "test"})
        assert "API error" in str(exc_info.value)

# Payment Verification Tests
@pytest.mark.asyncio
async def test_verify_payment_success():
    """Test successful payment verification."""
    payment_data = {
        "status": "completed",
        "amount": 1000,
        "currency": "RON",
        "timestamp": datetime.now().isoformat()
    }

    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: payment_data)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        result = await verify_payment("payment_123")
        assert result["is_verified"] is True

@pytest.mark.asyncio
async def test_verify_payment_incomplete():
    """Test incomplete payment verification."""
    payment_data = {
        "status": "pending",
        "amount": 1000,
        "currency": "RON"
    }

    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_doc = AsyncMock()
        mock_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: payment_data)
        mock_firestore.return_value.collection().document = MagicMock(return_value=mock_doc)

        with pytest.raises(PaymentError) as exc_info:
            await verify_payment("payment_123")
        assert "Payment not completed" in str(exc_info.value)

# Legal Database Search Tests
@pytest.mark.asyncio
async def test_search_legal_database_success():
    """Test successful legal database search."""
    mock_results = [
        {
            "case_number": "123/2023",
            "court": "ICCJ",
            "summary": "Test case",
            "relevance_score": 0.85
        }
    ]

    with patch("google.cloud.bigquery.Client") as mock_bq:
        mock_bq.return_value.query.return_value.result.return_value = mock_results

        result = await search_legal_database(
            query="contract breach",
            filters={"court": "ICCJ", "year": 2023}
        )
        assert len(result["results"]) == 1
        assert result["results"][0]["relevance_score"] > 0.8

# Legislation Retrieval Tests
@pytest.mark.asyncio
async def test_get_relevant_legislation_success():
    """Test successful legislation retrieval."""
    mock_legislation = [
        {
            "article": "Art. 1350",
            "code": "Civil Code",
            "content": "Test content",
            "relevance": "high"
        }
    ]

    with patch("google.cloud.bigquery.Client") as mock_bq:
        mock_bq.return_value.query.return_value.result.return_value = mock_legislation

        result = await get_relevant_legislation("civil", ["contract", "damages"])
        assert len(result["legislation"]) == 1
        assert result["legislation"][0]["code"] == "Civil Code"

# Quota Usage Update Tests
@pytest.mark.asyncio
async def test_update_quota_usage_success(sample_user_data, sample_org_data):
    """Test successful quota usage update."""
    with patch("google.cloud.firestore_v1.AsyncClient") as mock_firestore:
        mock_user_doc = AsyncMock()
        mock_user_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_user_data)
        mock_user_doc.update = AsyncMock()

        mock_org_doc = AsyncMock()
        mock_org_doc.get.return_value = AsyncMock(exists=True, to_dict=lambda: sample_org_data)
        mock_org_doc.update = AsyncMock()

        mock_firestore.return_value.collection().document = MagicMock(side_effect=[
            mock_user_doc, mock_org_doc
        ])

        result = await update_quota_usage("user_456", "org_789", 5)
        assert result["status"] == "success"
        assert result["updated_quota"]["user"] == 50  # 45 + 5
        assert result["updated_quota"]["organization"] == 455  # 450 + 5