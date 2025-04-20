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
                required=True,
                min_length=2,
                max_length=100,
                description="Numele complet al persoanei"
            ),
            "address": FieldDefinition(
                required=True,
                min_length=10,
                max_length=200,
                description="Adresa completă"
            ),
            "id_series": FieldDefinition(
                required=True,
                pattern=r'^[A-Z]{2}$',
                description="Seria CI (2 litere majuscule)"
            ),
            "id_number": FieldDefinition(
                required=True,
                pattern=r'^\d{6}$',
                description="Numărul CI (6 cifre)"
            )
        }
        
        self.company_fields = {
            "name": FieldDefinition(
                required=True,
                min_length=3,
                max_length=200,
                description="Denumirea completă a companiei"
            ),
            "registration_number": FieldDefinition(
                required=True,
                pattern=r'^J\d{2}/\d{3,7}/\d{4}$',
                description="Numărul de înregistrare la Registrul Comerțului"
            ),
            "fiscal_code": FieldDefinition(
                required=True,
                pattern=r'^RO?\d{2,10}$',
                description="Codul fiscal (CUI/CIF)"
            )
        }
        
        # Template-specific field definitions
        self.template_fields = {
            "court_appeal": {
                "court_name": FieldDefinition(
                    required=True,
                    min_length=5,
                    max_length=100,
                    description="Denumirea instanței"
                ),
                "court_section": FieldDefinition(
                    required=False,
                    description="Secția instanței"
                ),
                "appellant_name": FieldDefinition(
                    required=True,
                    min_length=2,
                    max_length=100,
                    description="Numele recurentului"
                ),
                "appellant_address": FieldDefinition(
                    required=True,
                    min_length=10,
                    description="Adresa recurentului"
                ),
                "appellant_quality": FieldDefinition(
                    required=True,
                    description="Calitatea procesuală a recurentului"
                ),
                "respondent_name": FieldDefinition(
                    required=True,
                    min_length=2,
                    description="Numele intimatului"
                ),
                "respondent_address": FieldDefinition(
                    required=True,
                    min_length=10,
                    description="Adresa intimatului"
                ),
                "contested_decision": FieldDefinition(
                    required=True,
                    description="Hotărârea atacată"
                ),
                "case_number": FieldDefinition(
                    required=True,
                    pattern=r'^\d+/\d+/\d{4}$',
                    description="Numărul dosarului"
                ),
                "appeal_reasons": FieldDefinition(
                    required=True,
                    min_length=100,
                    description="Motivele de recurs"
                ),
                "legal_provisions": FieldDefinition(
                    required=True,
                    description="Dispozițiile legale pe care se întemeiază recursul"
                )
            },
            "cease_and_desist": {
                "notice_number": FieldDefinition(
                    required=True,
                    pattern=r'^\d+/\d{4}$',
                    description="Numărul somației"
                ),
                "recipient_name": FieldDefinition(
                    required=True,
                    min_length=2,
                    description="Numele destinatarului"
                ),
                "recipient_address": FieldDefinition(
                    required=True,
                    min_length=10,
                    description="Adresa destinatarului"
                ),
                "sender_name": FieldDefinition(
                    required=True,
                    min_length=2,
                    description="Numele expeditorului"
                ),
                "sender_quality": FieldDefinition(
                    required=True,
                    description="Calitatea expeditorului"
                ),
                "cease_actions": FieldDefinition(
                    required=True,
                    min_length=50,
                    description="Acțiunile care trebuie să înceteze"
                ),
                "reasons": FieldDefinition(
                    required=True,
                    min_length=50,
                    description="Motivele somației"
                ),
                "legal_violations": FieldDefinition(
                    required=True,
                    description="Prevederile legale încălcate"
                )
            },
            "settlement_agreement": {
                "agreement_number": FieldDefinition(
                    required=True,
                    pattern=r'^\d+/\d{4}$',
                    description="Numărul acordului de mediere"
                ),
                "party1_name": FieldDefinition(
                    required=True,
                    min_length=2,
                    description="Numele primei părți"
                ),
                "party1_address": FieldDefinition(
                    required=True,
                    min_length=10,
                    description="Adresa primei părți"
                ),
                "party2_name": FieldDefinition(
                    required=True,
                    min_length=2,
                    description="Numele celei de-a doua părți"
                ),
                "party2_address": FieldDefinition(
                    required=True,
                    min_length=10,
                    description="Adresa celei de-a doua părți"
                ),
                "mediator_name": FieldDefinition(
                    required=True,
                    min_length=2,
                    description="Numele mediatorului"
                ),
                "mediator_license": FieldDefinition(
                    required=True,
                    pattern=r'^\d+/\d{4}$',
                    description="Numărul autorizației mediatorului"
                ),
                "dispute_description": FieldDefinition(
                    required=True,
                    min_length=50,
                    description="Descrierea conflictului"
                ),
                "settlement_terms": FieldDefinition(
                    required=True,
                    min_length=100,
                    description="Termenii înțelegerii"
                ),
                "party1_obligations": FieldDefinition(
                    required=True,
                    min_length=50,
                    description="Obligațiile primei părți"
                ),
                "party2_obligations": FieldDefinition(
                    required=True,
                    min_length=50,
                    description="Obligațiile celei de-a doua părți"
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