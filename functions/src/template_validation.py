"""
Template Validation - Field validation for legal document templates
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import re

@dataclass
class FieldDefinition:
    """Definition of a template field with validation rules."""
    name: str
    required: bool = False
    field_type: str = "str"
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    choices: Optional[List[str]] = None
    description: str = ""

class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

class TemplateValidator:
    """Validator for template fields with specific rules for each template type."""
    
    def __init__(self):
        # Common field definitions
        self.person_fields = {
            "name": FieldDefinition(
                name="name",
                required=True,
                min_length=2,
                max_length=100,
                description="Numele complet al persoanei"
            ),
            "address": FieldDefinition(
                name="address",
                required=True,
                min_length=10,
                max_length=200,
                description="Adresa completă"
            ),
            "id_series": FieldDefinition(
                name="id_series",
                required=True,
                pattern=r'^[A-Z]{2}$',
                description="Seria CI (2 litere majuscule)"
            ),
            "id_number": FieldDefinition(
                name="id_number",
                required=True,
                pattern=r'^\d{6}$',
                description="Numărul CI (6 cifre)"
            )
        }
        
        self.company_fields = {
            "name": FieldDefinition(
                name="name",
                required=True,
                min_length=3,
                max_length=200,
                description="Denumirea completă a companiei"
            ),
            "registration_number": FieldDefinition(
                name="registration_number",
                required=True,
                pattern=r'^J\d{2}/\d{3,7}/\d{4}$',
                description="Numărul de înregistrare la Registrul Comerțului"
            ),
            "fiscal_code": FieldDefinition(
                name="fiscal_code",
                required=True,
                pattern=r'^RO?\d{2,10}$',
                description="Codul fiscal (CUI/CIF)"
            )
        }
        
        # Template-specific field definitions
        self.template_fields = {
            "court_appeal": {
                "court_name": FieldDefinition(
                    name="court_name",
                    required=True,
                    min_length=5,
                    max_length=100,
                    description="Denumirea instanței"
                ),
                "court_section": FieldDefinition(
                    name="court_section",
                    required=False,
                    description="Secția instanței"
                ),
                "appellant_name": FieldDefinition(
                    name="appellant_name",
                    required=True,
                    min_length=2,
                    max_length=100,
                    description="Numele recurentului"
                ),
                "appellant_address": FieldDefinition(
                    name="appellant_address",
                    required=True,
                    min_length=10,
                    description="Adresa recurentului"
                ),
                "appellant_quality": FieldDefinition(
                    name="appellant_quality",
                    required=True,
                    description="Calitatea procesuală a recurentului"
                ),
                "respondent_name": FieldDefinition(
                    name="respondent_name",
                    required=True,
                    min_length=2,
                    description="Numele intimatului"
                ),
                "respondent_address": FieldDefinition(
                    name="respondent_address",
                    required=True,
                    min_length=10,
                    description="Adresa intimatului"
                ),
                "contested_decision": FieldDefinition(
                    name="contested_decision",
                    required=True,
                    description="Hotărârea atacată"
                ),
                "case_number": FieldDefinition(
                    name="case_number",
                    required=True,
                    pattern=r'^\d+/\d+/\d{4}$',
                    description="Numărul dosarului"
                ),
                "appeal_reasons": FieldDefinition(
                    name="appeal_reasons",
                    required=True,
                    min_length=100,
                    description="Motivele de recurs"
                ),
                "legal_provisions": FieldDefinition(
                    name="legal_provisions",
                    required=True,
                    description="Dispozițiile legale pe care se întemeiază recursul"
                )
            },
            "cease_and_desist": {
                "notice_number": FieldDefinition(
                    name="notice_number",
                    required=True,
                    pattern=r'^\d+/\d{4}$',
                    description="Numărul somației"
                ),
                "recipient_name": FieldDefinition(
                    name="recipient_name",
                    required=True,
                    min_length=2,
                    description="Numele destinatarului"
                ),
                "recipient_address": FieldDefinition(
                    name="recipient_address",
                    required=True,
                    min_length=10,
                    description="Adresa destinatarului"
                ),
                "sender_name": FieldDefinition(
                    name="sender_name",
                    required=True,
                    min_length=2,
                    description="Numele expeditorului"
                ),
                "sender_quality": FieldDefinition(
                    name="sender_quality",
                    required=True,
                    description="Calitatea expeditorului"
                ),
                "cease_actions": FieldDefinition(
                    name="cease_actions",
                    required=True,
                    min_length=50,
                    description="Acțiunile care trebuie să înceteze"
                ),
                "reasons": FieldDefinition(
                    name="reasons",
                    required=True,
                    min_length=50,
                    description="Motivele somației"
                ),
                "legal_violations": FieldDefinition(
                    name="legal_violations",
                    required=True,
                    description="Prevederile legale încălcate"
                )
            },
            "settlement_agreement": {
                "agreement_number": FieldDefinition(
                    name="agreement_number",
                    required=True,
                    pattern=r'^\d+/\d{4}$',
                    description="Numărul acordului de mediere"
                ),
                "party1_name": FieldDefinition(
                    name="party1_name",
                    required=True,
                    min_length=2,
                    description="Numele primei părți"
                ),
                "party1_address": FieldDefinition(
                    name="party1_address",
                    required=True,
                    min_length=10,
                    description="Adresa primei părți"
                ),
                "party2_name": FieldDefinition(
                    name="party2_name",
                    required=True,
                    min_length=2,
                    description="Numele celei de-a doua părți"
                ),
                "party2_address": FieldDefinition(
                    name="party2_address",
                    required=True,
                    min_length=10,
                    description="Adresa celei de-a doua părți"
                ),
                "mediator_name": FieldDefinition(
                    name="mediator_name",
                    required=True,
                    min_length=2,
                    description="Numele mediatorului"
                ),
                "mediator_license": FieldDefinition(
                    name="mediator_license",
                    required=True,
                    pattern=r'^\d+/\d{4}$',
                    description="Numărul autorizației mediatorului"
                ),
                "dispute_description": FieldDefinition(
                    name="dispute_description",
                    required=True,
                    min_length=50,
                    description="Descrierea conflictului"
                ),
                "settlement_terms": FieldDefinition(
                    name="settlement_terms",
                    required=True,
                    min_length=100,
                    description="Termenii înțelegerii"
                ),
                "party1_obligations": FieldDefinition(
                    name="party1_obligations",
                    required=True,
                    min_length=50,
                    description="Obligațiile primei părți"
                ),
                "party2_obligations": FieldDefinition(
                    name="party2_obligations",
                    required=True,
                    min_length=50,
                    description="Obligațiile celei de-a doua părți"
                )
            },
            "power_of_attorney": {
                "principal_name": FieldDefinition(
                    name="principal_name",
                    required=True,
                    min_length=2,
                    description="Numele mandantului"
                ),
                "principal_address": FieldDefinition(
                    name="principal_address",
                    required=True,
                    min_length=10,
                    description="Adresa mandantului"
                ),
                "principal_id_series": FieldDefinition(
                    name="principal_id_series",
                    required=True,
                    pattern=r'^[A-Z]{2}$',
                    description="Seria CI mandant"
                ),
                "principal_id_number": FieldDefinition(
                    name="principal_id_number",
                    required=True,
                    pattern=r'^\d{6}$',
                    description="Numărul CI mandant"
                ),
                "principal_cnp": FieldDefinition(
                    name="principal_cnp",
                    required=True,
                    pattern=r'^\d{13}$',
                    description="CNP mandant"
                ),
                "agent_name": FieldDefinition(
                    name="agent_name",
                    required=True,
                    min_length=2,
                    description="Numele mandatarului"
                ),
                "agent_address": FieldDefinition(
                    name="agent_address",
                    required=True,
                    min_length=10,
                    description="Adresa mandatarului"
                ),
                "agent_id_series": FieldDefinition(
                    name="agent_id_series",
                    required=True,
                    pattern=r'^[A-Z]{2}$',
                    description="Seria CI mandatar"
                ),
                "agent_id_number": FieldDefinition(
                    name="agent_id_number",
                    required=True,
                    pattern=r'^\d{6}$',
                    description="Numărul CI mandatar"
                ),
                "agent_cnp": FieldDefinition(
                    name="agent_cnp",
                    required=True,
                    pattern=r'^\d{13}$',
                    description="CNP mandatar"
                ),
                "powers_description": FieldDefinition(
                    name="powers_description",
                    required=True,
                    min_length=10,
                    description="Descrierea puterilor acordate"
                ),
                "valid_from": FieldDefinition(
                    name="valid_from",
                    required=True,
                    pattern=r'^\d{2}\.\d{2}\.\d{4}$',
                    description="Valabilă de la (DD.MM.YYYY)"
                ),
                "valid_until": FieldDefinition(
                    name="valid_until",
                    required=True,
                    pattern=r'^\d{2}\.\d{2}\.\d{4}$',
                    description="Valabilă până la (DD.MM.YYYY)"
                )
            },
            "employment_contract": {
                # Company fields (employer)
                "name": FieldDefinition(
                    name="name",
                    required=True,
                    min_length=3,
                    max_length=200,
                    description="Denumirea completă a companiei angajatoare"
                ),
                "cui": FieldDefinition(
                    name="cui",
                    required=True,
                    pattern=r'^\d{8}$',
                    description="Codul Unic de Înregistrare al angajatorului"
                ),
                "reg_com": FieldDefinition(
                    name="reg_com",
                    required=True,
                    pattern=r'^J\d{2}/\d{3,7}/\d{4}$',
                    description="Numărul de înregistrare la Registrul Comerțului"
                ),
                "address": FieldDefinition(
                    name="address",
                    required=True,
                    min_length=10,
                    description="Adresa angajatorului"
                ),
                "email": FieldDefinition(
                    name="email",
                    required=True,
                    pattern=r'^[^@]+@[^@]+\.[^@]+$',
                    description="Email angajator"
                ),
                "phone": FieldDefinition(
                    name="phone",
                    required=True,
                    pattern=r'^0\d{9}$',
                    description="Telefon angajator"
                ),
                # Person fields (employee)
                "name": FieldDefinition(
                    name="name",
                    required=True,
                    min_length=2,
                    description="Numele angajatului"
                ),
                "address": FieldDefinition(
                    name="address",
                    required=True,
                    min_length=10,
                    description="Adresa angajatului"
                ),
                "id_series": FieldDefinition(
                    name="id_series",
                    required=True,
                    pattern=r'^[A-Z]{2}$',
                    description="Seria CI angajat"
                ),
                "id_number": FieldDefinition(
                    name="id_number",
                    required=True,
                    pattern=r'^\d{6}$',
                    description="Numărul CI angajat"
                ),
                "cnp": FieldDefinition(
                    name="cnp",
                    required=True,
                    pattern=r'^\d{13}$',
                    description="CNP angajat"
                ),
                "email": FieldDefinition(
                    name="email",
                    required=True,
                    pattern=r'^[^@]+@[^@]+\.[^@]+$',
                    description="Email angajat"
                ),
                "phone": FieldDefinition(
                    name="phone",
                    required=True,
                    pattern=r'^0\d{9}$',
                    description="Telefon angajat"
                ),
                # Contract specific fields
                "job_title": FieldDefinition(
                    name="job_title",
                    required=True,
                    min_length=2,
                    description="Funcția ocupată"
                ),
                "cor_code": FieldDefinition(
                    name="cor_code",
                    required=True,
                    pattern=r'^\d{6}$',
                    description="COR code"
                ),
                "salary_details": FieldDefinition(
                    name="salary_details",
                    required=True,
                    min_length=5,
                    description="Detalii salariale"
                ),
                "work_time": FieldDefinition(
                    name="work_time",
                    required=True,
                    min_length=5,
                    description="Programul de lucru"
                )
            },
            "rental_agreement": {
                # Person fields (landlord)
                "name": FieldDefinition(
                    name="name",
                    required=True,
                    min_length=2,
                    description="Numele proprietarului"
                ),
                "address": FieldDefinition(
                    name="address",
                    required=True,
                    min_length=10,
                    description="Adresa proprietarului"
                ),
                "id_series": FieldDefinition(
                    name="id_series",
                    required=True,
                    pattern=r'^[A-Z]{2}$',
                    description="Seria CI proprietar"
                ),
                "id_number": FieldDefinition(
                    name="id_number",
                    required=True,
                    pattern=r'^\d{6}$',
                    description="Numărul CI proprietar"
                ),
                "cnp": FieldDefinition(
                    name="cnp",
                    required=True,
                    pattern=r'^\d{13}$',
                    description="CNP proprietar"
                ),
                "email": FieldDefinition(
                    name="email",
                    required=True,
                    pattern=r'^[^@]+@[^@]+\.[^@]+$',
                    description="Email proprietar"
                ),
                "phone": FieldDefinition(
                    name="phone",
                    required=True,
                    pattern=r'^0\d{9}$',
                    description="Telefon proprietar"
                ),
                # Property and agreement details
                "property_address": FieldDefinition(
                    name="property_address",
                    required=True,
                    min_length=10,
                    description="Adresa imobilului"
                ),
                "property_description": FieldDefinition(
                    name="property_description",
                    required=True,
                    min_length=10,
                    description="Descrierea imobilului"
                ),
                "rental_period": FieldDefinition(
                    name="rental_period",
                    required=True,
                    min_length=5,
                    description="Perioada de închiriere"
                ),
                "monthly_rent": FieldDefinition(
                    name="monthly_rent",
                    required=True,
                    pattern=r'^\d+(\.\d{2})?$',
                    description="rent amount"
                ),
                "payment_method": FieldDefinition(
                    name="payment_method",
                    required=True,
                    min_length=5,
                    description="Metoda de plată"
                ),
                "security_deposit": FieldDefinition(
                    name="security_deposit",
                    required=True,
                    pattern=r'^\d+\s*RON$',
                    description="Depozitul de garanție (format: 2000 RON)"
                )
            }
        }
        
        # Add existing template fields...
        # [Previous template fields remain unchanged]

    def validate_field(
        self,
        field_name: str,
        field_value: Any,
        field_def: FieldDefinition
    ) -> Optional[ValidationError]:
        """Validate a single field against its definition."""
        if field_def.required and (field_value is None or field_value == ""):
            return ValidationError(field_name, f"Câmpul {field_name} este obligatoriu")
            
        if field_value:
            if isinstance(field_value, str):
                if field_def.min_length and len(field_value) < field_def.min_length:
                    return ValidationError(
                        field_name,
                        f"Câmpul {field_name} trebuie să aibă minim {field_def.min_length} caractere"
                    )
                    
                if field_def.max_length and len(field_value) > field_def.max_length:
                    return ValidationError(
                        field_name,
                        f"Câmpul {field_name} trebuie să aibă maxim {field_def.max_length} caractere"
                    )
                    
                if field_def.pattern and not re.match(field_def.pattern, field_value):
                    return ValidationError(
                        field_name,
                        f"Câmpul {field_name} nu respectă formatul cerut: {field_def.description}"
                    )
        
        return None

    def validate_template_fields(
        self,
        template_type: str,
        context: Dict[str, Any]
    ) -> List[ValidationError]:
        """Validate all fields for a specific template type."""
        if template_type not in self.template_fields:
            raise ValueError(f"Tip de șablon nesuportat: {template_type}")
            
        errors = []
        fields = self.template_fields[template_type]
        
        for field_name, field_def in fields.items():
            error = self.validate_field(field_name, context.get(field_name), field_def)
            if error:
                errors.append(error)
        
        return errors

    def get_template_requirements(self, template_type: str) -> Dict[str, str]:
        """Get the field requirements for a specific template type."""
        if template_type not in self.template_fields:
            raise ValueError(f"Tip de șablon nesuportat: {template_type}")
            
        requirements = {}
        fields = self.template_fields[template_type]
        
        for field_name, field_def in fields.items():
            requirements[field_name] = {
                "required": field_def.required,
                "description": field_def.description
            }
        
        return requirements
