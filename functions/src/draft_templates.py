"""
Draft Templates - Specialized templates for generating legal documents
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from template_validation import TemplateValidator, ValidationError

# Common sections that can be reused across different templates
HEADER_TEMPLATE = """
[Logo/Antet]

{company_name}
{company_address}
CUI: {company_registration}
Tel: {company_phone}
Email: {company_email}
Web: {company_website}
"""

SIGNATURE_BLOCK = """
Cu stimă,

{name}
{position}
{organization}

Data: {date}
{signature_placeholder}
"""

class DraftTemplates:
    """Collection of legal document templates with context-based filling"""
    
    def __init__(self):
        """Initialize the template collection"""
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
        
    def get_template(self, template_name: str) -> Optional[callable]:
        """Get a template function by name"""
        return self.templates.get(template_name)
    
    def generate_draft(
        self, 
        template_name: str, 
        context: Dict[str, Any],
        custom_fields: Dict[str, Any] = None
    ) -> str:
        """Generate a document draft using the specified template and context"""
        if custom_fields is None:
            custom_fields = {}
            
        template_func = self.get_template(template_name)
        if not template_func:
            raise ValueError(f"Template '{template_name}' not found")
            
        return template_func(context, custom_fields)
    
    def list_available_templates(self) -> List[str]:
        """Return a list of available template names"""
        return list(self.templates.keys())
    
    def _power_of_attorney_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Power of Attorney (Procură)"""
        return '''
PROCURĂ

Subsemnatul/a {0},
domiciliat/ă în {1},
identificat/ă cu CI seria {2} nr. {3},
CNP {4},

împuternicesc prin prezenta pe

Domnul/Doamna {5},
domiciliat/ă în {6},
identificat/ă cu CI seria {7} nr. {8},
CNP {9},

să mă reprezinte și să îndeplinească în numele meu și pentru mine următoarele:

{10}

Mandatarul va avea următoarele puteri:
{11}

Prezenta procură este valabilă de la data de {12} până la data de {13}.

Data: {14}

Semnătura mandant,
{15}
[Semnătură]

Semnătura mandatar,
{16}
[Semnătură]
'''.format(
    context.get('principal_name'),
    context.get('principal_address'),
    context.get('principal_id_series'),
    context.get('principal_id_number'),
    context.get('principal_cnp'),
    context.get('agent_name'),
    context.get('agent_address'),
    context.get('agent_id_series'),
    context.get('agent_id_number'),
    context.get('agent_cnp'),
    context.get('powers_description'),
    context.get('specific_powers', '• ...\n• ...'),
    context.get('valid_from'),
    context.get('valid_until'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('principal_name'),
    context.get('agent_name')
)

    def _complaint_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Official Complaints (Plângere)"""
        return '''
PLÂNGERE

Către: {0}

Subsemnatul/a {1},
domiciliat/ă în {2},
telefon: {3},
email: {4},

În temeiul {5}, formulez prezenta

PLÂNGERE

împotriva {6},
cu sediul în {7},

pentru următoarele motive:

I. SITUAȚIA DE FAPT
{8}

II. MOTIVELE PLÂNGERII
{9}

III. PROBE
{10}

IV. SOLICITĂRI
{11}

Anexez prezentei următoarele documente:
{12}

Data: {13}

Semnătura,
{14}
[Semnătură]
'''.format(
    context.get('recipient_authority'),
    context.get('complainant_name'),
    context.get('complainant_address'),
    context.get('complainant_phone'),
    context.get('complainant_email'),
    context.get('legal_basis', 'art. ... din ...'),
    context.get('respondent_name'),
    context.get('respondent_address'),
    context.get('factual_situation'),
    context.get('complaint_reasons'),
    context.get('evidence', 'În dovedirea plângerii, înțeleg să mă folosesc de următoarele probe:'),
    context.get('requests', 'Pentru motivele arătate, vă solicit să dispuneți:'),
    context.get('attachments', '1. ...\n2. ...'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('complainant_name')
)

    def _contract_termination_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Contract Termination Notice (Notificare de Reziliere)"""
        return '''
NOTIFICARE DE REZILIERE A CONTRACTULUI

Către: {0}
{1}

Ref: Contractul nr. {2} din {3}

Stimate/ă Domn/Doamnă,

Prin prezenta vă notific încetarea contractului mai sus menționat, începând cu data de {4}, în conformitate cu {5}.

Motivul rezilierii:
{6}

Măsuri necesare pentru încheierea relației contractuale:
{7}

Vă rog să confirmați primirea prezentei notificări și să procedați conform celor menționate mai sus.

{8}
'''.format(
    context.get('recipient_name'),
    context.get('recipient_address'),
    context.get('contract_number'),
    context.get('contract_date'),
    context.get('termination_date'),
    context.get('termination_clause', 'prevederile art. ... din contract'),
    context.get('termination_reason'),
    context.get('required_actions', '1. ...\n2. ...'),
    SIGNATURE_BLOCK.format(
        name=context.get('sender_name'),
        position=context.get('sender_position'),
        organization=context.get('sender_organization'),
        date=datetime.now().strftime('%d.%m.%Y'),
        signature_placeholder='[Semnătură]'
    )
)

    def _gdpr_notice_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for GDPR Privacy Notice (Notă de Informare GDPR)"""
        return '''
NOTĂ DE INFORMARE
privind prelucrarea datelor cu caracter personal

1. IDENTITATEA OPERATORULUI
{0}
Sediu: {1}
CUI: {2}
Email: {3}

2. SCOPURILE PRELUCRĂRII
{4}

3. TEMEIUL JURIDIC AL PRELUCRĂRII
{5}

4. CATEGORIILE DE DATE PRELUCRATE
{6}

5. PERIOADA DE STOCARE
{7}

6. DREPTURILE PERSOANEI VIZATE
{8}

7. TRANSFERUL DATELOR
{9}

8. MĂSURI DE SECURITATE
{10}

Data actualizării: {11}

{12}
Reprezentant legal: {13}
[Semnătură și ștampilă]
'''.format(
    context.get('company_name'),
    context.get('company_address'),
    context.get('company_registration_number'),
    context.get('company_email'),
    context.get('processing_purposes', '• ...\n• ...'),
    context.get('legal_basis', 'Prelucrarea se face în baza:'),
    context.get('data_categories', '• Date de identificare\n• Date de contact'),
    context.get('storage_period'),
    context.get('data_subject_rights', '''• Dreptul de acces
• Dreptul la rectificare
• Dreptul la ștergere
• Dreptul la restricționarea prelucrării
• Dreptul la portabilitatea datelor
• Dreptul la opoziție
• Dreptul de a nu face obiectul unei decizii bazate exclusiv pe prelucrarea automată'''),
    context.get('data_transfer'),
    context.get('security_measures'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('company_name'),
    context.get('legal_representative')
)

    def _employment_contract_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Employment Contract (Contract Individual de Muncă)"""
        return '''
CONTRACT INDIVIDUAL DE MUNCĂ
încheiat și înregistrat sub nr. {0} din {1}

A. PĂRȚILE CONTRACTANTE

1. {2}, cu sediul în {3},
înregistrată la Registrul Comerțului sub nr. {4},
CUI {5}, telefon {6},
reprezentată legal prin {7},
în calitate de ANGAJATOR,

și

2. Domnul/Doamna {8},
domiciliat/ă în {9},
posesor/oare al/a CI seria {10} nr. {11},
CNP {12},
în calitate de SALARIAT,

au încheiat prezentul contract individual de muncă în următoarele condiții:

B. OBIECTUL CONTRACTULUI
{13}

C. DURATA CONTRACTULUI
{14}

D. LOCUL DE MUNCĂ
{15}

E. FELUL MUNCII
Funcția/meseria: {16}
COR: {17}

F. ATRIBUȚIILE POSTULUI
{18}

G. CONDIȚII DE MUNCĂ
{19}

H. DURATA MUNCII
{20}

I. CONCEDIUL
{21}

J. SALARIZARE
{22}

K. DREPTURI ȘI OBLIGAȚII ALE PĂRȚILOR
{23}

L. DISPOZIȚII FINALE
{24}

Prezentul contract a fost încheiat în două exemplare, câte unul pentru fiecare parte.

ANGAJATOR,                                    SALARIAT,
{25}                {26}
[Semnătură și ștampilă]                       [Semnătură]
'''.format(
    context.get('contract_number'),
    context.get('contract_date'),
    context.get('employer_name'),
    context.get('employer_address'),
    context.get('employer_registration'),
    context.get('employer_cui'),
    context.get('employer_phone'),
    context.get('employer_representative'),
    context.get('employee_name'),
    context.get('employee_address'),
    context.get('employee_id_series'),
    context.get('employee_id_number'),
    context.get('employee_cnp'),
    context.get('contract_object', 'Salariatul va presta muncă în funcția de ...'),
    context.get('contract_duration', 'Nedeterminată'),
    context.get('workplace'),
    context.get('job_title'),
    context.get('cor_code'),
    context.get('job_duties', 'Conform fișei postului, anexă la prezentul contract.'),
    context.get('work_conditions'),
    context.get('work_time'),
    context.get('vacation'),
    context.get('salary_details'),
    context.get('rights_and_obligations'),
    context.get('final_provisions'),
    context.get('employer_name'),
    context.get('employee_name')
)

    def _rental_agreement_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Rental Agreement (Contract de Închiriere)"""
        return '''
CONTRACT DE ÎNCHIRIERE

I. PĂRȚILE CONTRACTANTE

1.1. {0},
domiciliat/ă în {1},
identificat/ă cu CI seria {2} nr. {3},
CNP {4}, în calitate de PROPRIETAR,

și

1.2. {5},
domiciliat/ă în {6},
identificat/ă cu CI seria {7} nr. {8},
CNP {9}, în calitate de CHIRIAȘ,

au convenit încheierea prezentului contract de închiriere.

II. OBIECTUL CONTRACTULUI

2.1. Proprietarul închiriază, iar chiriașul ia în chirie imobilul situat în:
{10}

2.2. Descrierea imobilului:
{11}

III. DURATA CONTRACTULUI

3.1. Durata închirierii este de {12}, 
începând cu data de {13} 
până la data de {14}.

IV. PREȚUL ÎNCHIRIERII

4.1. Chiria lunară este de {15} lei.
4.2. Modalitatea de plată: {16}
4.3. Garanția: {17}

V. OBLIGAȚIILE PĂRȚILOR
{18}

VI. ÎNCETAREA CONTRACTULUI
{19}

VII. ALTE CLAUZE
{20}

Prezentul contract a fost încheiat astăzi, {21},
în două exemplare, câte unul pentru fiecare parte.

PROPRIETAR,                                   CHIRIAȘ,
{22}                {23}
[Semnătură]                                   [Semnătură]
'''.format(
    context.get('landlord_name'),
    context.get('landlord_address'),
    context.get('landlord_id_series'),
    context.get('landlord_id_number'),
    context.get('landlord_cnp'),
    context.get('tenant_name'),
    context.get('tenant_address'),
    context.get('tenant_id_series'),
    context.get('tenant_id_number'),
    context.get('tenant_cnp'),
    context.get('property_address'),
    context.get('property_description'),
    context.get('rental_period'),
    context.get('start_date'),
    context.get('end_date'),
    context.get('monthly_rent'),
    context.get('payment_method'),
    context.get('security_deposit'),
    context.get('obligations'),
    context.get('termination_conditions'),
    context.get('additional_clauses'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('landlord_name'),
    context.get('tenant_name')
)

    def _privacy_policy_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Privacy Policy (Politica de Confidențialitate)"""
        return '''
POLITICA DE CONFIDENȚIALITATE
{0}

Ultima actualizare: {1}

1. INTRODUCERE
{2}

2. INFORMAȚIILE PE CARE LE COLECTĂM
{3}

3. CUM UTILIZĂM INFORMAȚIILE
{4}

4. PARTAJAREA INFORMAȚIILOR
{5}

5. DREPTURILE DUMNEAVOASTRĂ
{6}

6. SECURITATEA DATELOR
{7}

7. MODIFICĂRI ALE POLITICII
{8}

8. CONTACT
{9}

{10}
{11}
Email: {12}
Telefon: {13}
'''.format(
    context.get('company_name'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('introduction'),
    context.get('collected_information'),
    context.get('information_usage'),
    context.get('information_sharing'),
    context.get('user_rights'),
    context.get('data_security'),
    context.get('policy_changes'),
    context.get('contact_info'),
    context.get('company_name'),
    context.get('company_address'),
    context.get('company_email'),
    context.get('company_phone')
)

    def _terms_of_service_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Terms of Service (Termeni și Condiții)"""
        return '''
TERMENI ȘI CONDIȚII
{0}

Ultima actualizare: {1}

1. ACCEPTAREA TERMENILOR
{2}

2. DESCRIEREA SERVICIILOR
{3}

3. ELIGIBILITATE
{4}

4. CONTUL UTILIZATORULUI
{5}

5. DREPTURI ȘI RESTRICȚII
{6}

6. PROPRIETATE INTELECTUALĂ
{7}

7. LIMITAREA RĂSPUNDERII
{8}

8. DESPĂGUBIRI
{9}

9. REZILIERE
{10}

10. LEGEA APLICABILĂ
{11}

11. MODIFICĂRI ALE TERMENILOR
{12}

12. CONTACT
{13}

{14}
{15}
Email: {16}
Telefon: {17}
'''.format(
    context.get('company_name'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('terms_acceptance'),
    context.get('services_description'),
    context.get('eligibility'),
    context.get('user_account'),
    context.get('rights_and_restrictions'),
    context.get('intellectual_property'),
    context.get('liability_limitation'),
    context.get('indemnification'),
    context.get('termination'),
    context.get('applicable_law'),
    context.get('terms_changes'),
    context.get('contact_details'),
    context.get('company_name'),
    context.get('company_address'),
    context.get('company_email'),
    context.get('company_phone')
)

    def _court_appeal_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Court Appeal (Recurs)"""
        return '''
RECURS

Către
{0}
{1}

DOMNULE PREȘEDINTE,

Subsemnatul/a {2},
domiciliat/ă în {3},
în calitate de {4},

în contradictoriu cu

{5},
cu domiciliul/sediul în {6},
în calitate de {7},

formulez prezentul

RECURS

împotriva {8}, pronunțată în dosarul nr. {9},
pentru următoarele motive:

I. SITUAȚIA DE FAPT
{10}

II. MOTIVELE DE RECURS
{11}

III. PROBE
În dovedirea recursului, înțeleg să mă folosesc de următoarele probe:
{12}

IV. TEMEI DE DREPT
{13}

Pentru aceste motive, vă solicit să dispuneți:
{14}

În drept, îmi întemeiez cererea pe dispozițiile {15}.

Data: {16}

Recurent,
{17}
[Semnătură]
'''.format(
    context.get('court_name'),
    context.get('court_section', 'Secția Civilă'),
    context.get('appellant_name'),
    context.get('appellant_address'),
    context.get('appellant_quality'),
    context.get('respondent_name'),
    context.get('respondent_address'),
    context.get('respondent_quality'),
    context.get('contested_decision'),
    context.get('case_number'),
    context.get('factual_situation'),
    context.get('appeal_reasons'),
    context.get('evidence', '1. Înscrisuri\n2. ...'),
    context.get('legal_basis', 'Art. ... din ...'),
    context.get('requests'),
    context.get('legal_provisions'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('appellant_name')
)

    def _cease_and_desist_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Cease and Desist Letter (Somație)"""
        return '''
SOMAȚIE
Nr. {0} din {1}

Către: {2}
{3}

Stimate domn/Stimată doamnă,

Subsemnatul/a {4}, în calitate de {5},
vă adresez prezenta somație prin care vă solicit să încetați imediat următoarele acțiuni:

{6}

Motivele acestei solicitări sunt următoarele:
{7}

Menționez că aceste acțiuni încalcă următoarele drepturi/prevederi legale:
{8}

Vă acordăm un termen de {9} de la primirea prezentei somații
pentru a vă conforma solicitărilor noastre și a înceta acțiunile mai sus menționate.

În cazul în care nu veți da curs prezentei somații în termenul acordat, ne rezervăm dreptul
de a întreprinde toate măsurile legale care se impun, inclusiv:
{10}

Prezenta somație constituie ultimul avertisment înainte de a recurge la măsurile legale
menționate mai sus.

{11}

Cu speranța unei soluționări amiabile,

{12}
{13}
{14}

[Semnătură și ștampilă]
'''.format(
    context.get('notice_number'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('recipient_name'),
    context.get('recipient_address'),
    context.get('sender_name'),
    context.get('sender_quality'),
    context.get('cease_actions'),
    context.get('reasons'),
    context.get('legal_violations'),
    context.get('deadline', '15 zile'),
    context.get('consequences', '''1. Formularea unei plângeri penale
2. Introducerea unei acțiuni în instanță
3. Solicitarea de daune-interese'''),
    context.get('additional_notes', ''),
    context.get('sender_name'),
    context.get('sender_position'),
    context.get('sender_organization')
)

    def _settlement_agreement_template(
        self,
        context: Dict[str, Any],
        custom_fields: Dict[str, Any]
    ) -> str:
        """Template for Settlement Agreement (Acord de Mediere)"""
        return '''
ACORD DE MEDIERE
Nr. {0} din {1}

I. PĂRȚILE ACORDULUI

1.1. {2},
domiciliat/ă în {3},
identificat/ă cu CI seria {4} nr. {5},
în calitate de PARTE,

și

1.2. {6},
domiciliat/ă în {7},
identificat/ă cu CI seria {8} nr. {9},
în calitate de PARTE,

cu participarea mediatorului autorizat:
{10},
cu sediul profesional în {11},
autorizație nr. {12},

au convenit încheierea prezentului acord de mediere.

II. OBIECTUL ACORDULUI

2.1. Prezentul acord are ca obiect soluționarea pe cale amiabilă a următorului conflict:
{13}

III. SITUAȚIA DE FAPT
{14}

IV. SOLUȚIA AGREATĂ DE PĂRȚI
{15}

V. OBLIGAȚIILE PĂRȚILOR

5.1. {16} se obligă să:
{17}

5.2. {18} se obligă să:
{19}

VI. TERMENE ȘI CONDIȚII
{20}

VII. CONFIDENȚIALITATE
{21}

VIII. CLAUZE FINALE

8.1. Prezentul acord reprezintă voința părților și înlătură orice altă înțelegere verbală dintre acestea.
8.2. Acordul a fost încheiat astăzi, {22}, în {23} exemplare originale,
câte unul pentru fiecare parte și unul pentru mediator.

SEMNĂTURI

Parte,                                    Parte,
{24}              {25}
[Semnătură]                               [Semnătură]

Mediator,
{26}
[Semnătură și ștampilă]
'''.format(
    context.get('agreement_number'),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('party1_name'),
    context.get('party1_address'),
    context.get('party1_id_series'),
    context.get('party1_id_number'),
    context.get('party2_name'),
    context.get('party2_address'),
    context.get('party2_id_series'),
    context.get('party2_id_number'),
    context.get('mediator_name'),
    context.get('mediator_address'),
    context.get('mediator_license'),
    context.get('dispute_description'),
    context.get('factual_situation'),
    context.get('settlement_terms'),
    context.get('party1_name'),
    context.get('party1_obligations'),
    context.get('party2_name'),
    context.get('party2_obligations'),
    context.get('terms_and_conditions'),
    context.get('confidentiality_terms', '''Părțile se obligă să păstreze confidențialitatea asupra:
• Informațiilor schimbate în cadrul procedurii de mediere
• Documentelor pregătite exclusiv pentru mediere
• Propunerilor de soluționare făcute în cadrul medierii'''),
    datetime.now().strftime('%d.%m.%Y'),
    context.get('copies_count', 'trei'),
    context.get('party1_name'),
    context.get('party2_name'),
    context.get('mediator_name')
)
