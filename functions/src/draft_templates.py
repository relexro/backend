"""
Draft Templates - Specialized templates for generating legal documents
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from .template_validation import TemplateValidator, ValidationError

# Common sections that can be reused across different templates
HEADER_TEMPLATE = """
{document_type}
Nr. {document_number} din {date}

Către: {recipient}
De la: {sender}
Ref: {reference}
"""

SIGNATURE_BLOCK = """
Cu stimă,
{name}
{position}
{organization}
Data: {date}
{signature_placeholder}
"""

class DraftGenerator:
    """Generator for various types of legal documents."""
    
    def __init__(self):
        self.validator = TemplateValidator()
        self.templates = {
            "power_of_attorney": self._power_of_attorney_template,
            "complaint": self._complaint_template,
            "contract_termination": self._contract_termination_template,
            "gdpr_notice": self._gdpr_notice_template,
            "employment_contract": self._employment_contract_template,
            "rental_agreement": self._rental_agreement_template,
            "privacy_policy": self._privacy_policy_template,
            "terms_of_service": self._terms_of_service_template,
            "court_appeal": self._court_appeal_template,
            "cease_and_desist": self._cease_and_desist_template,
            "settlement_agreement": self._settlement_agreement_template
        }

    def generate_draft(
        self,
        draft_type: str,
        context: Dict[str, Any],
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a legal document draft based on the specified type and context.
        Includes field validation.
        """
        try:
            if draft_type not in self.templates:
                raise ValueError(f"Unsupported draft type: {draft_type}")
            
            # Validate fields
            errors = self.validator.validate_template_fields(draft_type, context)
            if errors:
                return {
                    "status": "error",
                    "error": "Validation failed",
                    "validation_errors": [
                        {"field": e.field, "message": e.message}
                        for e in errors
                    ]
                }
            
            template_func = self.templates[draft_type]
            draft_content = template_func(context, custom_fields or {})
            
            return {
                "status": "success",
                "content": draft_content,
                "metadata": {
                    "type": draft_type,
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "template_requirements": self.validator.get_template_requirements(draft_type)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _power_of_attorney_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Power of Attorney (Procură)"""
        return f"""
PROCURĂ SPECIALĂ

Subsemnatul/a {context.get('principal_name')}, 
domiciliat/ă în {context.get('principal_address')},
identificat/ă cu CI seria {context.get('principal_id_series')} nr. {context.get('principal_id_number')},
CNP {context.get('principal_cnp')},

ÎMPUTERNICESC prin prezenta pe

Domnul/Doamna {context.get('agent_name')},
domiciliat/ă în {context.get('agent_address')},
identificat/ă cu CI seria {context.get('agent_id_series')} nr. {context.get('agent_id_number')},
CNP {context.get('agent_cnp')},

să mă reprezinte în fața {context.get('authority')} pentru {context.get('purpose')}.

Mandatarul va avea următoarele puteri:
{context.get('powers', '• să semneze în numele meu\n• să depună și să ridice documente')}

Prezenta procură este valabilă până la {context.get('validity_period', 'îndeplinirea mandatului')} 
și a fost dată astăzi, {datetime.now().strftime('%d.%m.%Y')}.

Semnătura mandant,
{context.get('principal_name')}
[Semnătură]

Semnătura mandatar,
{context.get('agent_name')}
[Semnătură]
"""

    def _complaint_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Official Complaints (Plângere)"""
        return f"""
PLÂNGERE

Către: {context.get('recipient_authority')}

Subsemnatul/a {context.get('complainant_name')},
domiciliat/ă în {context.get('complainant_address')},
telefon: {context.get('complainant_phone')},
email: {context.get('complainant_email')},

În temeiul {context.get('legal_basis', 'art. ... din ...')}, formulez prezenta

PLÂNGERE

împotriva {context.get('respondent_name')},
cu sediul în {context.get('respondent_address')},

pentru următoarele motive:

I. SITUAȚIA DE FAPT
{context.get('factual_situation')}

II. MOTIVELE PLÂNGERII
{context.get('complaint_reasons')}

III. PROBE
{context.get('evidence', 'În dovedirea plângerii, înțeleg să mă folosesc de următoarele probe:')}

IV. SOLICITĂRI
{context.get('requests', 'Pentru motivele arătate, vă solicit să dispuneți:')}

Anexez prezentei următoarele documente:
{context.get('attachments', '1. ...\n2. ...')}

Data: {datetime.now().strftime('%d.%m.%Y')}

Semnătura,
{context.get('complainant_name')}
[Semnătură]
"""

    def _contract_termination_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Contract Termination Notice (Notificare de Reziliere)"""
        return f"""
NOTIFICARE DE REZILIERE A CONTRACTULUI

Către: {context.get('recipient_name')}
{context.get('recipient_address')}

Ref: Contractul nr. {context.get('contract_number')} din {context.get('contract_date')}

Stimate/ă Domn/Doamnă,

Prin prezenta vă notific încetarea contractului mai sus menționat, începând cu data de {context.get('termination_date')}, în conformitate cu {context.get('termination_clause', 'prevederile art. ... din contract')}.

Motivul rezilierii:
{context.get('termination_reason')}

Măsuri necesare pentru încheierea relației contractuale:
{context.get('required_actions', '1. ...\n2. ...')}

Vă rog să confirmați primirea prezentei notificări și să procedați conform celor menționate mai sus.

{SIGNATURE_BLOCK.format(
    name=context.get('sender_name'),
    position=context.get('sender_position'),
    organization=context.get('sender_organization'),
    date=datetime.now().strftime('%d.%m.%Y'),
    signature_placeholder='[Semnătură]'
)}
"""

    def _gdpr_notice_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for GDPR Privacy Notice (Notă de Informare GDPR)"""
        return f"""
NOTĂ DE INFORMARE
privind prelucrarea datelor cu caracter personal

1. IDENTITATEA OPERATORULUI
{context.get('company_name')}
Sediu: {context.get('company_address')}
CUI: {context.get('company_registration_number')}
Email: {context.get('company_email')}

2. SCOPURILE PRELUCRĂRII
{context.get('processing_purposes', '• ...\n• ...')}

3. TEMEIUL JURIDIC AL PRELUCRĂRII
{context.get('legal_basis', 'Prelucrarea se face în baza:')}

4. CATEGORIILE DE DATE PRELUCRATE
{context.get('data_categories', '• Date de identificare\n• Date de contact')}

5. PERIOADA DE STOCARE
{context.get('storage_period')}

6. DREPTURILE PERSOANEI VIZATE
{context.get('data_subject_rights', '''• Dreptul de acces
• Dreptul la rectificare
• Dreptul la ștergere
• Dreptul la restricționarea prelucrării
• Dreptul la portabilitatea datelor
• Dreptul la opoziție
• Dreptul de a nu face obiectul unei decizii bazate exclusiv pe prelucrarea automată''')}

7. TRANSFERUL DATELOR
{context.get('data_transfer')}

8. MĂSURI DE SECURITATE
{context.get('security_measures')}

Data actualizării: {datetime.now().strftime('%d.%m.%Y')}

{context.get('company_name')}
Reprezentant legal: {context.get('legal_representative')}
[Semnătură și ștampilă]
"""

    def _employment_contract_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Employment Contract (Contract Individual de Muncă)"""
        return f"""
CONTRACT INDIVIDUAL DE MUNCĂ
încheiat și înregistrat sub nr. {context.get('contract_number')} din {context.get('contract_date')}

A. PĂRȚILE CONTRACTANTE

1. {context.get('employer_name')}, cu sediul în {context.get('employer_address')},
înregistrată la Registrul Comerțului sub nr. {context.get('employer_registration')},
CUI {context.get('employer_cui')}, telefon {context.get('employer_phone')},
reprezentată legal prin {context.get('employer_representative')},
în calitate de ANGAJATOR,

și

2. Domnul/Doamna {context.get('employee_name')},
domiciliat/ă în {context.get('employee_address')},
posesor/oare al/a CI seria {context.get('employee_id_series')} nr. {context.get('employee_id_number')},
CNP {context.get('employee_cnp')},
în calitate de SALARIAT,

au încheiat prezentul contract individual de muncă în următoarele condiții:

B. OBIECTUL CONTRACTULUI
{context.get('contract_object', 'Salariatul va presta muncă în funcția de ...')}

C. DURATA CONTRACTULUI
{context.get('contract_duration', 'Nedeterminată')}

D. LOCUL DE MUNCĂ
{context.get('workplace')}

E. FELUL MUNCII
Funcția/meseria: {context.get('job_title')}
COR: {context.get('cor_code')}

F. ATRIBUȚIILE POSTULUI
{context.get('job_duties', 'Conform fișei postului, anexă la prezentul contract.')}

G. CONDIȚII DE MUNCĂ
{context.get('work_conditions')}

H. DURATA MUNCII
{context.get('work_time')}

I. CONCEDIUL
{context.get('vacation')}

J. SALARIZARE
{context.get('salary_details')}

K. DREPTURI ȘI OBLIGAȚII ALE PĂRȚILOR
{context.get('rights_and_obligations')}

L. DISPOZIȚII FINALE
{context.get('final_provisions')}

Prezentul contract a fost încheiat în două exemplare, câte unul pentru fiecare parte.

ANGAJATOR,                                    SALARIAT,
{context.get('employer_name')}                {context.get('employee_name')}
[Semnătură și ștampilă]                       [Semnătură]
"""

    def _rental_agreement_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Rental Agreement (Contract de Închiriere)"""
        return f"""
CONTRACT DE ÎNCHIRIERE

I. PĂRȚILE CONTRACTANTE

1.1. {context.get('landlord_name')},
domiciliat/ă în {context.get('landlord_address')},
identificat/ă cu CI seria {context.get('landlord_id_series')} nr. {context.get('landlord_id_number')},
CNP {context.get('landlord_cnp')}, în calitate de PROPRIETAR,

și

1.2. {context.get('tenant_name')},
domiciliat/ă în {context.get('tenant_address')},
identificat/ă cu CI seria {context.get('tenant_id_series')} nr. {context.get('tenant_id_number')},
CNP {context.get('tenant_cnp')}, în calitate de CHIRIAȘ,

au convenit încheierea prezentului contract de închiriere.

II. OBIECTUL CONTRACTULUI

2.1. Proprietarul închiriază, iar chiriașul ia în chirie imobilul situat în:
{context.get('property_address')}

2.2. Descrierea imobilului:
{context.get('property_description')}

III. DURATA CONTRACTULUI

3.1. Durata închirierii este de {context.get('rental_period')}, 
începând cu data de {context.get('start_date')} 
până la data de {context.get('end_date')}.

IV. PREȚUL ÎNCHIRIERII

4.1. Chiria lunară este de {context.get('monthly_rent')} lei.
4.2. Modalitatea de plată: {context.get('payment_method')}
4.3. Garanția: {context.get('security_deposit')}

V. OBLIGAȚIILE PĂRȚILOR
{context.get('obligations')}

VI. ÎNCETAREA CONTRACTULUI
{context.get('termination_conditions')}

VII. ALTE CLAUZE
{context.get('additional_clauses')}

Prezentul contract a fost încheiat astăzi, {datetime.now().strftime('%d.%m.%Y')},
în două exemplare, câte unul pentru fiecare parte.

PROPRIETAR,                                   CHIRIAȘ,
{context.get('landlord_name')}                {context.get('tenant_name')}
[Semnătură]                                   [Semnătură]
"""

    def _privacy_policy_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Privacy Policy (Politica de Confidențialitate)"""
        return f"""
POLITICA DE CONFIDENȚIALITATE
{context.get('company_name')}

Ultima actualizare: {datetime.now().strftime('%d.%m.%Y')}

1. INTRODUCERE
{context.get('introduction')}

2. INFORMAȚIILE PE CARE LE COLECTĂM
{context.get('collected_information')}

3. CUM UTILIZĂM INFORMAȚIILE
{context.get('information_usage')}

4. PARTAJAREA INFORMAȚIILOR
{context.get('information_sharing')}

5. DREPTURILE DUMNEAVOASTRĂ
{context.get('user_rights')}

6. SECURITATEA DATELOR
{context.get('data_security')}

7. MODIFICĂRI ALE POLITICII
{context.get('policy_changes')}

8. CONTACT
{context.get('contact_info')}

{context.get('company_name')}
{context.get('company_address')}
Email: {context.get('company_email')}
Telefon: {context.get('company_phone')}
"""

    def _terms_of_service_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Terms of Service (Termeni și Condiții)"""
        return f"""
TERMENI ȘI CONDIȚII
{context.get('company_name')}

Ultima actualizare: {datetime.now().strftime('%d.%m.%Y')}

1. ACCEPTAREA TERMENILOR
{context.get('terms_acceptance')}

2. DESCRIEREA SERVICIILOR
{context.get('services_description')}

3. ELIGIBILITATE
{context.get('eligibility')}

4. CONTUL UTILIZATORULUI
{context.get('user_account')}

5. DREPTURI ȘI RESTRICȚII
{context.get('rights_and_restrictions')}

6. PROPRIETATE INTELECTUALĂ
{context.get('intellectual_property')}

7. LIMITAREA RĂSPUNDERII
{context.get('liability_limitation')}

8. DESPĂGUBIRI
{context.get('indemnification')}

9. REZILIERE
{context.get('termination')}

10. LEGEA APLICABILĂ
{context.get('applicable_law')}

11. MODIFICĂRI ALE TERMENILOR
{context.get('terms_changes')}

12. CONTACT
{context.get('contact_details')}

{context.get('company_name')}
{context.get('company_address')}
Email: {context.get('company_email')}
Telefon: {context.get('company_phone')}
"""

    def _court_appeal_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Court Appeal (Recurs)"""
        return f"""
RECURS

Către
{context.get('court_name')}
{context.get('court_section', 'Secția Civilă')}

DOMNULE PREȘEDINTE,

Subsemnatul/a {context.get('appellant_name')},
domiciliat/ă în {context.get('appellant_address')},
în calitate de {context.get('appellant_quality')},

în contradictoriu cu

{context.get('respondent_name')},
cu domiciliul/sediul în {context.get('respondent_address')},
în calitate de {context.get('respondent_quality')},

formulez prezentul

RECURS

împotriva {context.get('contested_decision')}, pronunțată în dosarul nr. {context.get('case_number')},
pentru următoarele motive:

I. SITUAȚIA DE FAPT
{context.get('factual_situation')}

II. MOTIVELE DE RECURS
{context.get('appeal_reasons')}

III. PROBE
În dovedirea recursului, înțeleg să mă folosesc de următoarele probe:
{context.get('evidence', '1. Înscrisuri\n2. ...')}

IV. TEMEI DE DREPT
{context.get('legal_basis', 'Art. ... din ...')}

Pentru aceste motive, vă solicit să dispuneți:
{context.get('requests')}

În drept, îmi întemeiez cererea pe dispozițiile {context.get('legal_provisions')}.

Data: {datetime.now().strftime('%d.%m.%Y')}

Recurent,
{context.get('appellant_name')}
[Semnătură]
"""

    def _cease_and_desist_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Cease and Desist Letter (Somație)"""
        return f"""
SOMAȚIE
Nr. {context.get('notice_number')} din {datetime.now().strftime('%d.%m.%Y')}

Către: {context.get('recipient_name')}
{context.get('recipient_address')}

Stimate domn/Stimată doamnă,

Subsemnatul/a {context.get('sender_name')}, în calitate de {context.get('sender_quality')},
vă adresez prezenta somație prin care vă solicit să încetați imediat următoarele acțiuni:

{context.get('cease_actions')}

Motivele acestei solicitări sunt următoarele:
{context.get('reasons')}

Menționez că aceste acțiuni încalcă următoarele drepturi/prevederi legale:
{context.get('legal_violations')}

Vă acordăm un termen de {context.get('deadline', '15 zile')} de la primirea prezentei somații
pentru a vă conforma solicitărilor noastre și a înceta acțiunile mai sus menționate.

În cazul în care nu veți da curs prezentei somații în termenul acordat, ne rezervăm dreptul
de a întreprinde toate măsurile legale care se impun, inclusiv:
{context.get('consequences', '''1. Formularea unei plângeri penale
2. Introducerea unei acțiuni în instanță
3. Solicitarea de daune-interese''')}

Prezenta somație constituie ultimul avertisment înainte de a recurge la măsurile legale
menționate mai sus.

{context.get('additional_notes', '')}

Cu speranța unei soluționări amiabile,

{context.get('sender_name')}
{context.get('sender_position')}
{context.get('sender_organization')}

[Semnătură și ștampilă]
"""

    def _settlement_agreement_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Settlement Agreement (Acord de Mediere)"""
        return f"""
ACORD DE MEDIERE
Nr. {context.get('agreement_number')} din {datetime.now().strftime('%d.%m.%Y')}

I. PĂRȚILE ACORDULUI

1.1. {context.get('party1_name')},
domiciliat/ă în {context.get('party1_address')},
identificat/ă cu CI seria {context.get('party1_id_series')} nr. {context.get('party1_id_number')},
în calitate de PARTE,

și

1.2. {context.get('party2_name')},
domiciliat/ă în {context.get('party2_address')},
identificat/ă cu CI seria {context.get('party2_id_series')} nr. {context.get('party2_id_number')},
în calitate de PARTE,

cu participarea mediatorului autorizat:
{context.get('mediator_name')},
cu sediul profesional în {context.get('mediator_address')},
autorizație nr. {context.get('mediator_license')},

au convenit încheierea prezentului acord de mediere.

II. OBIECTUL ACORDULUI

2.1. Prezentul acord are ca obiect soluționarea pe cale amiabilă a următorului conflict:
{context.get('dispute_description')}

III. SITUAȚIA DE FAPT
{context.get('factual_situation')}

IV. SOLUȚIA AGREATĂ DE PĂRȚI
{context.get('settlement_terms')}

V. OBLIGAȚIILE PĂRȚILOR

5.1. {context.get('party1_name')} se obligă să:
{context.get('party1_obligations')}

5.2. {context.get('party2_name')} se obligă să:
{context.get('party2_obligations')}

VI. TERMENE ȘI CONDIȚII
{context.get('terms_and_conditions')}

VII. CONFIDENȚIALITATE
{context.get('confidentiality_terms', '''Părțile se obligă să păstreze confidențialitatea asupra:
• Informațiilor schimbate în cadrul procedurii de mediere
• Documentelor pregătite exclusiv pentru mediere
• Propunerilor de soluționare făcute în cadrul medierii''')}

VIII. CLAUZE FINALE

8.1. Prezentul acord reprezintă voința părților și înlătură orice altă înțelegere verbală dintre acestea.
8.2. Acordul a fost încheiat astăzi, {datetime.now().strftime('%d.%m.%Y')}, în {context.get('copies_count', 'trei')} exemplare originale,
câte unul pentru fiecare parte și unul pentru mediator.

SEMNĂTURI

Parte,                                    Parte,
{context.get('party1_name')}              {context.get('party2_name')}
[Semnătură]                               [Semnătură]

Mediator,
{context.get('mediator_name')}
[Semnătură și ștampilă]
""" 