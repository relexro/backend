"""
Unit tests for draft templates and validation
"""
import pytest
from datetime import datetime
from functions.src.draft_templates import DraftGenerator
from functions.src.template_validation import TemplateValidator, ValidationError

@pytest.fixture
def validator():
    """Fixture for template validator."""
    return TemplateValidator()

@pytest.fixture
def valid_person():
    """Fixture for valid person data."""
    return {
        "name": "Ion Popescu",
        "address": "Str. Exemplu nr. 1, București, Sector 1",
        "id_series": "RX",
        "id_number": "123456",
        "cnp": "1234567890123"
    }

@pytest.fixture
def valid_company():
    """Fixture for valid company data."""
    return {
        "name": "Test Company SRL",
        "registration_number": "J40/123/2020",
        "cui": "12345678",
        "address": "Str. Exemplu nr. 1, București, Sector 1",
        "email": "contact@example.com"
    }

@pytest.fixture
def generator():
    """Fixture for draft generator."""
    return DraftGenerator()

# Template Validation Tests

def test_power_of_attorney_validation(validator, valid_person):
    """Test power of attorney template validation."""
    # Test valid data
    context = {
        **valid_person,
        "authority": "Primăria Sector 1",
        "purpose": "reprezentare în vederea obținerii certificatului fiscal",
        "validity_period": "31.12.2024"
    }
    errors = validator.validate_template_fields("power_of_attorney", context)
    assert len(errors) == 0

    # Test missing required field
    context_missing = context.copy()
    del context_missing["authority"]
    errors = validator.validate_template_fields("power_of_attorney", context_missing)
    assert len(errors) == 1
    assert errors[0].field == "authority"

def test_employment_contract_validation(validator, valid_person, valid_company):
    """Test employment contract template validation."""
    context = {
        **valid_company,  # Employer details
        **valid_person,   # Employee details
        "job_title": "Software Developer",
        "cor_code": "251401",
        "salary_details": "5000 RON brut lunar",
        "work_time": "8 ore/zi, 40 ore/săptămână"
    }
    errors = validator.validate_template_fields("employment_contract", context)
    assert len(errors) == 0

    # Test invalid COR code
    context_invalid = context.copy()
    context_invalid["cor_code"] = "12345"  # Should be 6 digits
    errors = validator.validate_template_fields("employment_contract", context_invalid)
    assert len(errors) == 1
    assert "COR code" in errors[0].message

def test_rental_agreement_validation(validator, valid_person):
    """Test rental agreement template validation."""
    context = {
        **valid_person,  # Landlord details
        "property_address": "Str. Exemplu nr. 10, București, Sector 2",
        "property_description": "Apartament cu 2 camere, suprafață 55mp",
        "rental_period": "12 luni",
        "monthly_rent": "2000.00",
        "payment_method": "Transfer bancar",
        "security_deposit": "2000 RON"
    }
    errors = validator.validate_template_fields("rental_agreement", context)
    assert len(errors) == 0

    # Test invalid rent format
    context_invalid = context.copy()
    context_invalid["monthly_rent"] = "2000,00"  # Should use decimal point
    errors = validator.validate_template_fields("rental_agreement", context_invalid)
    assert len(errors) == 1
    assert "rent amount" in errors[0].message.lower()

# Draft Generator Tests

def test_power_of_attorney_generation(generator, valid_person):
    """Test power of attorney document generation."""
    context = {
        **valid_person,
        "authority": "Primăria Sector 1",
        "purpose": "reprezentare în vederea obținerii certificatului fiscal",
        "validity_period": "31.12.2024"
    }
    result = generator.generate_draft("power_of_attorney", context)

    assert result["status"] == "success"
    assert "PROCURĂ SPECIALĂ" in result["content"]
    assert context["name"] in result["content"]
    assert context["authority"] in result["content"]
    assert context["purpose"] in result["content"]

def test_complaint_generation(generator, valid_person):
    """Test complaint document generation."""
    context = {
        **valid_person,
        "recipient_authority": "Protecția Consumatorului",
        "factual_situation": "În data de 01.01.2024 am achiziționat produsul X...",
        "complaint_reasons": "Produsul prezintă defecte de fabricație...",
        "requests": "Solicit înlocuirea produsului și despăgubiri..."
    }
    result = generator.generate_draft("complaint", context)

    assert result["status"] == "success"
    assert "PLÂNGERE" in result["content"]
    assert context["recipient_authority"] in result["content"]
    assert "SITUAȚIA DE FAPT" in result["content"]
    assert context["factual_situation"] in result["content"]

def test_invalid_template_type(generator):
    """Test handling of invalid template type."""
    with pytest.raises(ValueError):
        generator.generate_draft("nonexistent_template", {})

def test_metadata_generation(generator, valid_person):
    """Test metadata generation for drafts."""
    result = generator.generate_draft("power_of_attorney", valid_person)

    assert "metadata" in result
    assert result["metadata"]["type"] == "power_of_attorney"
    assert "generated_at" in result["metadata"]
    assert result["metadata"]["version"] == "1.0"