/parties/{partyId} Document Structure
Stores details for each party involved in any case. Access to this data must be strictly controlled.

{
    "partyId": "string", // Unique ID for the party
    "partyType": "individual | organization",
    "createdByUserId": "string", // User who initially added this party record
    "createdAt": "timestamp",
    "updatedAt": "timestamp",

    // Fields for Individuals (Encrypted at rest, consider field-level encryption)
    "firstName": "string | null",
    "lastName": "string | null",
    "cnp": "string | null", // Cod Numeric Personal (Romanian National ID)
    "dateOfBirth": "date | null",
    "address": {
        "street": "string | null",
        "city": "string | null",
        "county": "string | null", // Județ
        "postalCode": "string | null",
        "country": "string | null"
    },
    "contact": {
        "email": "string | null",
        "phone": "string | null"
    },

    // Fields for Organizations (Encrypted at rest where sensitive)
    "organizationName": "string | null",
    "cui": "string | null", // Cod Unic de Înregistrare (Romanian Tax ID)
    "registrationNumber": "string | null", // Nr. Registrul Comerțului
    "registeredAddress": { // Similar address structure as above
        // ...
    },
    "primaryContactPerson": {
        "name": "string | null",
        "email": "string | null",
        "phone": "string | null"
    },

    "internalNotes": "string | null" // Non-sensitive notes about the party record itself
}