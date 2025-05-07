# Case Tier System

## Overview

The Relex platform uses a tiered approach to classify legal cases based on their complexity. This system allows for appropriate pricing, resource allocation, and feature access. Each case is assigned to one of three tiers (1, 2, or 3) during the initial analysis by the AI agent.

## Tier Definitions

### Tier 1: Basic Cases

**English Definition:**
Cases that involve simple legal matters, requiring minimal AI interaction and resources. These cases typically involve straightforward document preparation or basic legal information.

**Romanian Definition:**
Cazuri care implică probleme juridice simple, necesitând interacțiune minimă cu AI și resurse limitate. Aceste cazuri implică de obicei pregătirea documentelor simple sau informații juridice de bază.

**Examples:**
- Simple legal information requests
- Basic document preparation (power of attorney, notifications)
- Straightforward contracts review
- Standard complaint letters
- General legal advice on common topics

**Features:**
- Basic document generation
- Limited legal research
- Standard response templates
- Minimal AI reasoning complexity

### Tier 2: Standard Cases

**English Definition:**
Cases of moderate complexity that require more extensive AI analysis and assistance. These cases typically involve standard legal procedures, document preparation with moderate complexity, or legal research on specific topics.

**Romanian Definition:**
Cazuri de complexitate moderată care necesită analiză și asistență AI mai extinsă. Aceste cazuri implică de obicei proceduri juridice standard, pregătirea documentelor cu complexitate moderată sau cercetare juridică pe teme specifice.

**Examples:**
- Standard contracts (employment, rental, service agreements)
- Simple legal analysis of situations
- Preparation of statements of claim for common legal procedures
- Moderate complexity complaints to authorities
- Legal research on specific laws or regulations

**Features:**
- Advanced document generation with customization
- Comprehensive legal research
- Personalized response templates
- Moderate AI reasoning complexity
- Multiple document assistance

### Tier 3: Complex Cases

**English Definition:**
Cases involving complex legal matters that require sophisticated AI analysis, comprehensive legal research, and extensive document preparation. These cases typically involve multiple parties, complex legal issues, or specialized legal domains.

**Romanian Definition:**
Cazuri care implică probleme juridice complexe care necesită analiză AI sofisticată, cercetare juridică cuprinzătoare și pregătire extinsă a documentelor. Aceste cazuri implică de obicei mai multe părți, probleme juridice complexe sau domenii juridice specializate.

**Examples:**
- Complex litigation preparation
- Multi-party contracts and negotiations
- Specialized legal domains (intellectual property, corporate law)
- Comprehensive case strategy development
- Complex regulatory compliance issues
- Cases involving multiple jurisdictions or international elements

**Features:**
- Sophisticated document generation with advanced customization
- In-depth legal research across multiple sources
- Complex reasoning and strategic planning
- Multi-document case management
- Extended AI processing time

## Tier Determination Process

The AI agent determines the appropriate tier during the initial interaction with the user through the following process:

1. **Initial Assessment**: The agent analyzes the user's description of their legal issue.

2. **Complexity Factors**: The agent evaluates several factors:
   - Number of parties involved
   - Legal domains implicated
   - Procedural complexity
   - Document requirements
   - Research needs
   - Potential for litigation
   - Specialized knowledge requirements

3. **Tier Assignment**: Based on this analysis, the agent assigns the case to Tier 1, 2, or 3.

4. **User Confirmation**: The agent informs the user of the tier assignment and confirms whether they wish to proceed.

5. **Quota Check**: The agent checks if the user has available quota for the assigned tier using the `check_quota` tool.

6. **Payment Processing**: If additional payment is required, the agent initiates the payment process.

## Quota Consumption

Each tier consumes different amounts of the user's or organization's quota:

| Tier | Quota Points Consumed |
|------|----------------------|
| 1    | 1 point              |
| 2    | 3 points             |
| 3    | 5 points             |

## Implementation Details

The tier system is implemented across several components:

1. **Agent Logic**: The agent's tier determination logic is implemented in `functions/src/agent.py` and related modules.

2. **Payments System**: The quota and payment processing for each tier is implemented in `functions/src/payments.py`.

3. **Firestore Schema**: Tier and quota information is stored in the user and organization documents, as well as in the case document.

4. **API Integration**: Endpoints for quota checking and payment processing are exposed through the API Gateway.

## Tier-Specific Features

Certain features are only available for specific tiers:

### Tier 1 Features
- Basic document templates
- Simple legal information retrieval
- Standard response generation

### Tier 2 Features (includes all Tier 1 features, plus:)
- Advanced document customization
- Specific legal research
- Case timeline tracking
- Multiple document generation

### Tier 3 Features (includes all Tier 1 and 2 features, plus:)
- Complex legal strategy development
- Comprehensive case management
- Advanced multi-party document handling
- In-depth legal research and analysis
- Extended AI processing time

## Tier Upgrades

A case can be upgraded from a lower tier to a higher tier if the complexity increases or if the user requires additional features. The upgrade process includes:

1. The user requests an upgrade or the agent identifies the need for an upgrade
2. The agent determines the new appropriate tier
3. The system checks quota availability for the new tier
4. If necessary, the user makes an additional payment
5. The case is upgraded to the new tier with access to additional features 