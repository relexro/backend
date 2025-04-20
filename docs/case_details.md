// Inside Firestore document: /cases/{caseId}
{
  // ... other case fields like title, userId, organizationId, status, caseTier, caseTypeId ...
  "case_details": {
    "summary": { // AI-generated summary, constantly updated by Gemini
      "current": "string", // Latest concise summary of the case status and facts
      "history": [ // Optional: keep previous summaries for evolution tracking
        { "timestamp": "timestamp", "summary": "string" }
      ]
    },
    "facts": [ // Chronological list of established facts
      { "timestamp": "timestamp", "source": "user_message | document_X | inference", "fact": "string", "confidence": "high | medium | low" }
    ],
    "user_statements": [ // Key statements or claims made by the user
       { "timestamp": "timestamp", "statement": "string" }
    ],
    "objectives": [ // User's stated goals for the case
      { "timestamp": "timestamp", "objective": "string", "status": "pending | achieved | abandoned" }
    ],
    "parties_involved": [ // References to parties attached to the case
      { "partyId": "string", "role_in_case": "string (e.g., claimant, defendant, witness)" }
      // Note: Actual party PII is NOT stored here, only in /parties/{partyId}
    ],
    "documents_analysis": [ // Analysis derived from attached documents
      {
        "documentId": "string",
        "originalFilename": "string",
        "analysis_summary": "string", // Gemini's summary of the document's relevance/content
        "key_extracted_info": [ // Specific pieces of info extracted
           { "info": "string", "location_hint": "string (e.g., page 2, paragraph 3)" }
        ],
        "analysis_timestamp": "timestamp"
      }
    ],
    "legal_research": { // Findings from BigQuery (Legislation & Case Law)
      "legislation": [
        { "doc_id": "string", "title": "string", "summary": "string", "relevance_score": "float", "status": "considered | applied | irrelevant", "fetch_timestamp": "timestamp" }
      ],
      "jurisprudence": [
         { "doc_id": "string", "court": "string", "summary": "string", "relevance_score": "float", "status": "considered | applied | irrelevant", "fetch_timestamp": "timestamp" }
      ]
    },
    "agent_interactions": { // Log of significant agent decisions or requests for info
       "log": [
         { "timestamp": "timestamp", "agent": "Gemini | Grok", "type": "info_request_user | info_request_bq | guidance_request | decision | plan_step | draft_generation", "details": "string" }
       ],
       "active_info_request_to_user": "string | null" // The current question Gemini is asking the user based on Grok's request
    },
    "draft_status": [ // Tracks generated drafts and feedback
        {
          "draft_firestore_id": "string", // ID linking to the draft metadata entry
          "draft_name": "string (e.g., Cerere_chemare_judecata)",
          "revision": "integer",
          "gcs_path": "string",
          "generation_timestamp": "timestamp",
          "generated_by": "Gemini", // Based on Grok's guidance
          "status": "generated | user_feedback_received | revised",
          "user_feedback": [ // Log of feedback on this specific revision
            { "timestamp": "timestamp", "feedback_summary": "string" }
          ]
        }
    ],
    "case_timeline": [ // Key dates and events
        { "timestamp": "timestamp", "event_type": "case_created | document_added | party_attached | user_message | agent_message | draft_generated | ...", "description": "string" }
    ],
    "internal_notes": [ // Notes added by the agent system (e.g., uncertainties, inconsistencies)
        { "timestamp": "timestamp", "agent": "Gemini | Grok", "note": "string" }
    ],
    "last_updated": "timestamp" // Timestamp of the last update to case_details
  },
  "gemini_session_id": "string", // Session ID for Gemini API
  "grok_session_id": "string",   // Session ID for Grok API
  // ... other case fields
}