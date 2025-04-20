"""
Unit tests for draft templates and validation
"""
import unittest
from datetime import datetime
from src.draft_templates import DraftGenerator
from src.template_validation import TemplateValidator, ValidationError

class TestTemplateValidation(unittest.TestCase):
    """Test cases for template field validation."""

    def setUp(self):
        """Set up test cases."""
        self.validator = TemplateValidator()
        self.valid_person = {
            "name": "Ion Popescu",
            "address": "Str. Exemplu nr. 1, București, Sector 1",
            "id_series": "RX",
            "id_number": "123456",
            "cnp": "1234567890123"
        }
        self.valid_company = {
            "name": "Test Company SRL",
            "registration_number": "J40/123/2020",
            "cui": "12345678",
            "address": "Str. Exemplu nr. 1, București, Sector 1",
            "email": "contact@example.com"
        }

    def test_power_of_attorney_validation(self):
        """Test power of attorney template validation."""
        # Test valid data
        context = {
            **self.valid_person,
            "authority": "Primăria Sector 1",
            "purpose": "reprezentare în vederea obținerii certificatului fiscal",
            "validity_period": "31.12.2024"
        }
        errors = self.validator.validate_template_fields("power_of_attorney", context)
        self.assertEqual(len(errors), 0)

        # Test missing required field
        del context["authority"]
        errors = self.validator.validate_template_fields("power_of_attorney", context)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].field, "authority")

    def test_employment_contract_validation(self):
        """Test employment contract template validation."""
        context = {
            **self.valid_company,  # Employer details
            **self.valid_person,   # Employee details
            "job_title": "Software Developer",
            "cor_code": "251401",
            "salary_details": "5000 RON brut lunar",
            "work_time": "8 ore/zi, 40 ore/săptămână"
        }
        errors = self.validator.validate_template_fields("employment_contract", context)
        self.assertEqual(len(errors), 0)

        # Test invalid COR code
        context["cor_code"] = "12345"  # Should be 6 digits
        errors = self.validator.validate_template_fields("employment_contract", context)
        self.assertEqual(len(errors), 1)
        self.assertTrue("COR code" in errors[0].message)

    def test_rental_agreement_validation(self):
        """Test rental agreement template validation."""
        context = {
            **self.valid_person,  # Landlord details
            "property_address": "Str. Exemplu nr. 10, București, Sector 2",
            "property_description": "Apartament cu 2 camere, suprafață 55mp",
            "rental_period": "12 luni",
            "monthly_rent": "2000.00",
            "payment_method": "Transfer bancar",
            "security_deposit": "2000 RON"
        }
        errors = self.validator.validate_template_fields("rental_agreement", context)
        self.assertEqual(len(errors), 0)

        # Test invalid rent format
        context["monthly_rent"] = "2000,00"  # Should use decimal point
        errors = self.validator.validate_template_fields("rental_agreement", context)
        self.assertEqual(len(errors), 1)
        self.assertTrue("rent amount" in errors[0].message.lower())

class TestDraftGenerator(unittest.TestCase):
    """Test cases for draft document generation."""

    def setUp(self):
        """Set up test cases."""
        self.generator = DraftGenerator()
        self.valid_person = {
            "name": "Ion Popescu",
            "address": "Str. Exemplu nr. 1, București, Sector 1",
            "id_series": "RX",
            "id_number": "123456",
            "cnp": "1234567890123"
        }

    def test_power_of_attorney_generation(self):
        """Test power of attorney document generation."""
        context = {
            **self.valid_person,
            "authority": "Primăria Sector 1",
            "purpose": "reprezentare în vederea obținerii certificatului fiscal",
            "validity_period": "31.12.2024"
        }
        result = self.generator.generate_draft("power_of_attorney", context)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("PROCURĂ SPECIALĂ", result["content"])
        self.assertIn(context["name"], result["content"])
        self.assertIn(context["authority"], result["content"])
        self.assertIn(context["purpose"], result["content"])

    def test_complaint_generation(self):
        """Test complaint document generation."""
        context = {
            **self.valid_person,
            "recipient_authority": "Protecția Consumatorului",
            "factual_situation": "În data de 01.01.2024 am achiziționat produsul X...",
            "complaint_reasons": "Produsul prezintă defecte de fabricație...",
            "requests": "Solicit înlocuirea produsului și despăgubiri..."
        }
        result = self.generator.generate_draft("complaint", context)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("PLÂNGERE", result["content"])
        self.assertIn(context["recipient_authority"], result["content"])
        self.assertIn("SITUAȚIA DE FAPT", result["content"])
        self.assertIn(context["factual_situation"], result["content"])

    def test_invalid_template_type(self):
        """Test handling of invalid template type."""
        with self.assertRaises(ValueError):
            self.generator.generate_draft("nonexistent_template", {})

    def test_metadata_generation(self):
        """Test metadata generation for drafts."""
        result = self.generator.generate_draft("power_of_attorney", self.valid_person)
        
        self.assertIn("metadata", result)
        self.assertEqual(result["metadata"]["type"], "power_of_attorney")
        self.assertIn("generated_at", result["metadata"])
        self.assertEqual(result["metadata"]["version"], "1.0")

if __name__ == '__main__':
    unittest.main() 