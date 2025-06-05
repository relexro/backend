"""
Unit tests for draft templates and validation
"""
import pytest
from datetime import datetime
from functions.src import template_validation, draft_templates
from functions.src.template_validation import TemplateValidator, ValidationError

@pytest.fixture
def validator():
    """Create a template validator instance."""
    return template_validation.TemplateValidator()

@pytest.fixture
def generator():
    """Create a draft templates generator instance."""
    return draft_templates.DraftTemplates()

@pytest.fixture
def valid_person():
    """Create valid person data."""
    return {
        "name": "John Doe",
        "address": "Str. Exemplu nr. 1, București, Sector 1",
        "id_series": "RX",
        "id_number": "123456",
        "cnp": "1234567890123",
        "email": "john@example.com",
        "phone": "0712345678"
    }

@pytest.fixture
def valid_company():
    """Create valid company data."""
    return {
        "name": "Test Company SRL",
        "cui": "12345678",
        "reg_com": "J40/123/2024",
        "address": "Str. Exemplu nr. 1, București, Sector 1",
        "email": "contact@example.com",
        "phone": "0212345678"
    }

# Template Validation Tests

def test_power_of_attorney_validation(validator, valid_person):
    """Test power of attorney template validation."""
    # Test valid data
    context = {
        **valid_person,
        "principal_name": valid_person["name"],
        "principal_address": valid_person["address"],
        "principal_id_series": valid_person["id_series"],
        "principal_id_number": valid_person["id_number"],
        "principal_cnp": valid_person["cnp"],
        "agent_name": "Jane Smith",
        "agent_address": "Str. Exemplu nr. 2, București, Sector 2",
        "agent_id_series": "RX",
        "agent_id_number": "654321",
        "agent_cnp": "9876543210987",
        "powers_description": "reprezentare în vederea obținerii certificatului fiscal",
        "valid_from": "01.01.2024",
        "valid_until": "31.12.2024"
    }
    errors = validator.validate_template_fields("power_of_attorney", context)
    assert len(errors) == 0

    # Test missing required field
    context_missing = context.copy()
    del context_missing["agent_name"]
    errors = validator.validate_template_fields("power_of_attorney", context_missing)
    assert len(errors) == 1
    assert errors[0].field == "agent_name"

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
        "principal_name": valid_person["name"],
        "principal_address": valid_person["address"],
        "principal_id_series": valid_person["id_series"],
        "principal_id_number": valid_person["id_number"],
        "principal_cnp": valid_person["cnp"],
        "agent_name": "Jane Smith",
        "agent_address": "Str. Exemplu nr. 2, București, Sector 2",
        "agent_id_series": "RX",
        "agent_id_number": "654321",
        "agent_cnp": "9876543210987",
        "powers_description": "reprezentare în vederea obținerii certificatului fiscal",
        "valid_from": "01.01.2024",
        "valid_until": "31.12.2024"
    }
    result = generator.generate_draft("power_of_attorney", context)
    assert isinstance(result, str)
    assert "PROCURĂ" in result
    assert context["principal_name"] in result
    assert context["agent_name"] in result
    assert context["powers_description"] in result

def test_complaint_generation(generator, valid_person):
    """Test complaint document generation."""
    context = {
        "recipient_authority": "Protecția Consumatorului",
        "complainant_name": valid_person["name"],
        "complainant_address": valid_person["address"],
        "complainant_phone": valid_person["phone"],
        "complainant_email": valid_person["email"],
        "respondent_name": "Test Company SRL",
        "respondent_address": "Str. Exemplu nr. 1, București, Sector 1",
        "factual_situation": "În data de 01.01.2024 am achiziționat produsul X...",
        "complaint_reasons": "Produsul prezintă defecte de fabricație...",
        "requests": "Solicit înlocuirea produsului și despăgubiri..."
    }
    result = generator.generate_draft("complaint", context)
    assert isinstance(result, str)
    assert "PLÂNGERE" in result
    assert context["complainant_name"] in result
    assert context["recipient_authority"] in result
    assert context["factual_situation"] in result

def test_invalid_template_type(validator):
    """Test validation with invalid template type."""
    with pytest.raises(ValueError, match="Tip de șablon nesuportat"):
        validator.validate_template_fields("invalid_type", {})

def test_metadata_generation(generator, valid_person):
    """Test metadata generation for drafts."""
    context = {
        "principal_name": valid_person["name"],
        "principal_address": valid_person["address"],
        "principal_id_series": valid_person["id_series"],
        "principal_id_number": valid_person["id_number"],
        "principal_cnp": valid_person["cnp"],
        "agent_name": "Jane Smith",
        "agent_address": "Str. Exemplu nr. 2, București, Sector 2",
        "agent_id_series": "RX",
        "agent_id_number": "654321",
        "agent_cnp": "9876543210987",
        "powers_description": "reprezentare în vederea obținerii certificatului fiscal",
        "valid_from": "01.01.2024",
        "valid_until": "31.12.2024"
    }
    result = generator.generate_draft("power_of_attorney", context)
    assert isinstance(result, str)
    assert "PROCURĂ" in result
    assert context["principal_name"] in result
    assert context["agent_name"] in result
