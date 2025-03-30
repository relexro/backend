import functions_framework
import logging
import firebase_admin
from firebase_admin import firestore
import json
import uuid
import datetime
from google.cloud import aiplatform
import google.auth
import os
from flask import Request
from auth import get_authenticated_user, check_permission, PermissionCheckRequest, TYPE_CASE # Corrected import

logging.basicConfig(level=logging.INFO)

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

db = firestore.client()

def receive_prompt(request: Request):
    logging.info("Logic function receive_prompt called")
    try:
        data = request.get_json(silent=True)
        if not data:
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)

        if not hasattr(request, 'user_id'):
             return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        user_id = request.user_id

        case_id = data.get("caseId")
        prompt_text = data.get("prompt")

        if not case_id or not isinstance(case_id, str) or not case_id.strip():
             return ({"error": "Bad Request", "message": "Valid caseId is required"}, 400)
        if not prompt_text or not isinstance(prompt_text, str) or not prompt_text.strip():
            return ({"error": "Bad Request", "message": "Valid prompt is required"}, 400)

        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return ({"error": "Not Found", "message": "Case not found"}, 404)

        case_data = case_doc.to_dict()
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,
            resourceId=case_id,
            action="update", # Sending a prompt implies updating the case conversation
            organizationId=case_data.get("organizationId")
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        prompt_id = str(uuid.uuid4())
        prompt_ref = case_ref.collection("prompts").document(prompt_id)
        prompt_data = {
            "promptId": prompt_id,
            "prompt": prompt_text.strip(),
            "userId": user_id,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "status": "received"
        }
        prompt_ref.set(prompt_data)

        # Trigger enrichment and AI processing asynchronously?
        # For now, just return prompt ID

        return ({"message": "Prompt received", "promptId": prompt_id}, 200)
    except Exception as e:
        logging.error(f"Error receiving prompt: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to process prompt"}, 500)


def enrich_prompt(request: Request):
    logging.info("Logic function enrich_prompt called")
    try:
        data = request.get_json(silent=True)
        if not data:
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)

        # No user auth check needed if called internally? If called externally, add auth check.
        # if not hasattr(request, 'user_id'):
        #      return {"error": "Unauthorized", "message": "Authentication data missing"}, 401
        # user_id = request.user_id

        prompt_text = data.get("prompt")
        case_id = data.get("caseId")

        if not prompt_text or not isinstance(prompt_text, str) or not prompt_text.strip():
            return ({"error": "Bad Request", "message": "Valid prompt is required"}, 400)
        if case_id and (not isinstance(case_id, str) or not case_id.strip()):
             return ({"error": "Bad Request", "message": "caseId must be a non-empty string if provided"}, 400)

        enriched_prompt_text = prompt_text # Start with original

        if case_id:
            case_doc = db.collection("cases").document(case_id).get()
            if case_doc.exists:
                case_data = case_doc.to_dict()
                context = []
                context.append(f"Case ID: {case_id}")
                if "title" in case_data: context.append(f"Title: {case_data['title']}")
                if "description" in case_data: context.append(f"Description: {case_data['description']}")
                if "status" in case_data: context.append(f"Status: {case_data['status']}")

                # Fetch recent documents (limit 3)
                try:
                    docs_query = db.collection("documents").where("caseId", "==", case_id).order_by("uploadDate", direction=firestore.Query.DESCENDING).limit(3).stream()
                    doc_names = [doc.to_dict().get("originalFilename", "file") for doc in docs_query]
                    if doc_names: context.append(f"Recent docs: {', '.join(doc_names)}")
                except Exception as e:
                    logging.warning(f"Error fetching docs for case {case_id}: {e}")

                # Fetch recent messages (limit 5, consider sender/receiver)
                try:
                    msg_query = db.collection("cases").document(case_id).collection("conversations").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()
                    recent_msgs = []
                    for msg in reversed(list(msg_query)): # Reverse to get chronological order
                         msg_data = msg.to_dict()
                         sender = "User" if msg_data.get("userId") else "AI" # Adjust based on actual structure
                         content = msg_data.get("prompt") or msg_data.get("response") # Get relevant content
                         if content: recent_msgs.append(f"{sender}: {content}")
                    if recent_msgs:
                         context.append("\nRecent Conversation:")
                         context.extend(recent_msgs)
                except Exception as e:
                     logging.warning(f"Error fetching messages for case {case_id}: {e}")

                context_str = "\n".join(context)
                enriched_prompt_text = f"Context:\n---\n{context_str}\n---\n\nUser query: {prompt_text}"
            else:
                 logging.warning(f"Case {case_id} not found for enrichment.")

        return ({"enrichedPrompt": enriched_prompt_text, "originalPrompt": prompt_text}, 200)
    except Exception as e:
        logging.error(f"Error enriching prompt: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to enrich prompt"}, 500)


def send_to_vertex_ai(request: Request):
    logging.info("Logic function send_to_vertex_ai called")
    try:
        data = request.get_json(silent=True)
        if not data:
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)

        # No user auth check needed if called internally? If called externally, add auth check.

        prompt_id = data.get("promptId")
        prompt_text = data.get("prompt") # Expecting enriched prompt here
        case_id = data.get("caseId")

        if not prompt_id or not isinstance(prompt_id, str) or not prompt_id.strip():
             return ({"error": "Bad Request", "message": "Valid promptId is required"}, 400)
        if not prompt_text or not isinstance(prompt_text, str) or not prompt_text.strip():
             return ({"error": "Bad Request", "message": "Valid prompt is required"}, 400)
        if not case_id or not isinstance(case_id, str) or not case_id.strip():
             return ({"error": "Bad Request", "message": "Valid caseId is required"}, 400)

        try:
            credentials, default_project_id = google.auth.default()
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", default_project_id)
            location = os.environ.get("GOOGLE_CLOUD_REGION", "europe-west3")
            endpoint_id = os.environ.get("VERTEX_AI_ENDPOINT_ID") # Needs to be configured

            if not project_id or not location or not endpoint_id:
                 logging.error("Vertex AI configuration (Project, Location, Endpoint ID) missing.")
                 return ({"error": "Configuration Error", "message": "Vertex AI not configured"}, 500)

            logging.info(f"Sending to Vertex AI: Project={project_id}, Location={location}, Endpoint={endpoint_id}")
            aiplatform.init(project=project_id, location=location, credentials=credentials)

            # TODO: Replace with actual Vertex AI endpoint call structure
            # This likely involves creating an Endpoint instance and calling predict
            # endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)
            # Example payload structure (adjust based on your model)
            # instances = [{"prompt": prompt_text}]
            # prediction = endpoint.predict(instances=instances)
            # ai_response_content = prediction.predictions[0]['content'] # Adjust based on actual response structure

            # --- Mock Response ---
            ai_response_content = f"Mock Vertex AI response for prompt: '{prompt_text[:100]}...'"
            logging.warning("Using Mock Vertex AI response!")
            # --- End Mock Response ---

            # Update prompt status in Firestore (consider doing this after storing conversation)
            # prompt_ref = db.collection("cases").document(case_id).collection("prompts").document(prompt_id)
            # prompt_ref.update({"status": "processed", "responseTimestamp": firestore.SERVER_TIMESTAMP})

            return ({"response": ai_response_content, "promptId": prompt_id, "caseId": case_id }, 200)
        except Exception as e:
            logging.error(f"Vertex AI interaction error: {str(e)}", exc_info=True)
            return ({"error": "Vertex AI Error", "message": f"Failed to get response from Vertex AI: {str(e)}"}, 500)

    except Exception as e:
        logging.error(f"Error sending to Vertex AI: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to process request"}, 500)

def store_conversation(request: Request):
    logging.info("Logic function store_conversation called")
    try:
        data = request.get_json(silent=True)
        if not data:
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)

        # Auth check: Should the user who initiated the prompt be the one storing it?
        if not hasattr(request, 'user_id'):
             # If called internally without auth context, get user_id from data? Less secure.
             user_id = data.get("userId")
             if not user_id:
                  return {"error": "Bad Request", "message": "userId missing in request body (or auth failed)"}, 400
        else:
             user_id = request.user_id

        case_id = data.get("caseId")
        prompt_id = data.get("promptId")
        prompt_text = data.get("prompt") # Original or enriched prompt? Store original?
        response_text = data.get("response")

        if not case_id or not isinstance(case_id, str) or not case_id.strip():
             return ({"error": "Bad Request", "message": "Valid caseId is required"}, 400)
        if not prompt_id or not isinstance(prompt_id, str) or not prompt_id.strip():
             return ({"error": "Bad Request", "message": "Valid promptId is required"}, 400)
        if not prompt_text or not isinstance(prompt_text, str): # Allow empty prompt?
             return ({"error": "Bad Request", "message": "Valid prompt is required"}, 400)
        if not response_text or not isinstance(response_text, str): # Allow empty response?
            return ({"error": "Bad Request", "message": "Valid response is required"}, 400)

        # Fetch the case document to ensure it exists and get its organizationId
        case_ref = db.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return ({"error": "Not Found", "message": "Case not found"}, 404)
            
        # Get case data for permission check
        case_data = case_doc.to_dict()
        
        # Add permission check before writing to the subcollection
        permission_request = PermissionCheckRequest(
            resourceType=TYPE_CASE,  # Make sure TYPE_CASE is imported from auth
            resourceId=case_id,
            action="update",  # Storing conversation implies updating case history
            organizationId=case_data.get("organizationId")  # Pass org ID for permission context
        )
        has_permission, error_message = check_permission(user_id, permission_request)
        if not has_permission:
            return ({"error": "Forbidden", "message": error_message}), 403

        # Use prompt_id as the document ID for the conversation turn
        # Changed the subcollection name from "conversations" to "caseChatMessages"
        conversation_ref = case_ref.collection("caseChatMessages").document(prompt_id)

        # Consider storing original prompt from prompt collection if needed
        # prompt_doc = case_ref.collection("prompts").document(prompt_id).get()
        # original_prompt = prompt_doc.to_dict().get("prompt") if prompt_doc.exists else prompt_text

        conversation_data = {
            "promptId": prompt_id,
            "prompt": prompt_text, # Storing the prompt text received by this function
            "response": response_text,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "userId": user_id # User who initiated the prompt
        }
        conversation_ref.set(conversation_data)

        # Optionally update case's updatedAt timestamp
        case_ref.update({"updatedAt": firestore.SERVER_TIMESTAMP})

        return ({"message": "Conversation stored", "conversationId": prompt_id}, 200)
    except Exception as e:
        logging.error(f"Error storing conversation: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "Failed to store conversation"}, 500)