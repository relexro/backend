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

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    # Use the application default credentials
    firebase_admin.initialize_app()

@functions_framework.http
def receive_prompt(request):
    """Receive a prompt from the user.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to receive a prompt")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "caseId" not in data:
            logging.error("Bad Request: Missing caseId")
            return ({"error": "Bad Request", "message": "caseId is required"}, 400)
            
        if not isinstance(data["caseId"], str):
            logging.error("Bad Request: caseId must be a string")
            return ({"error": "Bad Request", "message": "caseId must be a string"}, 400)
            
        if not data["caseId"].strip():
            logging.error("Bad Request: caseId cannot be empty")
            return ({"error": "Bad Request", "message": "caseId cannot be empty"}, 400)
        
        if "prompt" not in data:
            logging.error("Bad Request: Missing prompt")
            return ({"error": "Bad Request", "message": "prompt is required"}, 400)
            
        if not isinstance(data["prompt"], str):
            logging.error("Bad Request: prompt must be a string")
            return ({"error": "Bad Request", "message": "prompt must be a string"}, 400)
            
        if not data["prompt"].strip():
            logging.error("Bad Request: prompt cannot be empty")
            return ({"error": "Bad Request", "message": "prompt cannot be empty"}, 400)
        
        # Extract fields
        case_id = data["caseId"].strip()
        prompt = data["prompt"].strip()
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Verify the case exists
        case_doc = db.collection("cases").document(case_id).get()
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
        # Generate a unique prompt ID
        prompt_id = str(uuid.uuid4())
        
        # Store the prompt in Firestore temporarily
        prompt_ref = db.collection("cases").document(case_id).collection("prompts").document(prompt_id)
        prompt_data = {
            "prompt": prompt,
            "userId": "test-user",  # Placeholder until auth is implemented
            "timestamp": firestore.SERVER_TIMESTAMP,
            "status": "received"
        }
        prompt_ref.set(prompt_data)
        
        # Return success response with prompt ID
        logging.info(f"Prompt received for case {case_id} with ID {prompt_id}")
        return ({"message": "Prompt received", "promptId": prompt_id}, 200)
    except Exception as e:
        logging.error(f"Error receiving prompt: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to process prompt"}, 500)

@functions_framework.http
def enrich_prompt(request):
    """Enrich the prompt with context before sending to Vertex AI.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to enrich a prompt with context")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "prompt" not in data:
            logging.error("Bad Request: Missing prompt")
            return ({"error": "Bad Request", "message": "prompt is required"}, 400)
            
        if not isinstance(data["prompt"], str):
            logging.error("Bad Request: prompt must be a string")
            return ({"error": "Bad Request", "message": "prompt must be a string"}, 400)
            
        if not data["prompt"].strip():
            logging.error("Bad Request: prompt cannot be empty")
            return ({"error": "Bad Request", "message": "prompt cannot be empty"}, 400)
        
        # Extract fields
        prompt = data["prompt"].strip()
        case_id = data.get("caseId")
        
        # If no case ID provided, return the original prompt
        if not case_id:
            logging.info("No case ID provided, returning original prompt")
            return ({"enrichedPrompt": prompt, "originalPrompt": prompt}, 200)
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Get the case document
        case_doc = db.collection("cases").document(case_id).get()
        
        # If case doesn't exist, return the original prompt
        if not case_doc.exists:
            logging.warning(f"Case with ID {case_id} not found, returning original prompt")
            return ({"enrichedPrompt": prompt, "originalPrompt": prompt}, 200)
        
        # Extract case data
        case_data = case_doc.to_dict()
        
        # Build context from case data
        context = []
        context.append(f"Case ID: {case_id}")
        
        if "title" in case_data:
            context.append(f"Title: {case_data['title']}")
        
        if "description" in case_data:
            context.append(f"Description: {case_data['description']}")
        
        if "status" in case_data:
            context.append(f"Status: {case_data['status']}")
        
        # Get most recent documents (up to 3)
        try:
            docs_query = db.collection("documents").where("caseId", "==", case_id).order_by("uploadDate", direction=firestore.Query.DESCENDING).limit(3).get()
            if docs_query:
                doc_names = [doc.to_dict().get("originalFilename", "Unknown file") for doc in docs_query]
                if doc_names:
                    context.append(f"Recent documents: {', '.join(doc_names)}")
        except Exception as e:
            logging.warning(f"Error fetching documents for case {case_id}: {str(e)}")
        
        # Get most recent messages (up to 5)
        try:
            messages_query = db.collection("cases").document(case_id).collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).get()
            if messages_query:
                recent_messages = []
                for msg in messages_query:
                    msg_data = msg.to_dict()
                    if "content" in msg_data and "sender" in msg_data:
                        recent_messages.append(f"{msg_data['sender']}: {msg_data['content']}")
                
                if recent_messages:
                    context.append("Recent messages:")
                    context.extend(recent_messages)
        except Exception as e:
            logging.warning(f"Error fetching messages for case {case_id}: {str(e)}")
        
        # Combine context and prompt
        context_str = "\n".join(context)
        enriched_prompt = f"Context:\n{context_str}\n\nUser query: {prompt}"
        
        # Return the enriched prompt
        logging.info(f"Successfully enriched prompt for case {case_id}")
        return ({"enrichedPrompt": enriched_prompt, "originalPrompt": prompt}, 200)
    except Exception as e:
        logging.error(f"Error enriching prompt: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to enrich prompt"}, 500)

@functions_framework.http
def send_to_vertex_ai(request):
    """Send prompt to Vertex AI Conversational Agent.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to send prompt to Vertex AI")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "promptId" not in data:
            logging.error("Bad Request: Missing promptId")
            return ({"error": "Bad Request", "message": "promptId is required"}, 400)
            
        if not isinstance(data["promptId"], str):
            logging.error("Bad Request: promptId must be a string")
            return ({"error": "Bad Request", "message": "promptId must be a string"}, 400)
            
        if not data["promptId"].strip():
            logging.error("Bad Request: promptId cannot be empty")
            return ({"error": "Bad Request", "message": "promptId cannot be empty"}, 400)
        
        if "prompt" not in data:
            logging.error("Bad Request: Missing prompt")
            return ({"error": "Bad Request", "message": "prompt is required"}, 400)
            
        if not isinstance(data["prompt"], str):
            logging.error("Bad Request: prompt must be a string")
            return ({"error": "Bad Request", "message": "prompt must be a string"}, 400)
            
        if not data["prompt"].strip():
            logging.error("Bad Request: prompt cannot be empty")
            return ({"error": "Bad Request", "message": "prompt cannot be empty"}, 400)
        
        if "caseId" not in data:
            logging.error("Bad Request: Missing caseId")
            return ({"error": "Bad Request", "message": "caseId is required"}, 400)
        
        # Extract fields
        prompt_id = data["promptId"].strip()
        prompt = data["prompt"].strip()
        case_id = data["caseId"].strip()
        
        # Initialize Vertex AI
        try:
            # Initialize Vertex AI client
            # Get default project from credentials
            credentials, project_id = google.auth.default()
            # Override project_id with explicitly set value (relexro)
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "relexro")
            location = os.environ.get("GOOGLE_CLOUD_REGION", "europe-west3")
            
            logging.info(f"Initializing Vertex AI client with project={project_id}, location={location}")
            
            # Initialize Vertex AI API client
            aiplatform.init(project=project_id, location=location)
            
            # For demo purposes, we'll return a mock response
            # In production, we'd actually call the Vertex AI API using:
            # endpoint = aiplatform.Endpoint("your-endpoint-id")
            # response = endpoint.predict(instances=[prompt])
            
            # Mock Vertex AI response for testing
            ai_response = f"This is a mock response from Vertex AI in response to: '{prompt}'. In a real implementation, this would be from the actual Vertex AI service. As you continue building this module, you'll integrate with a specific Vertex AI model endpoint."
            
            # Update prompt status in Firestore
            db = firestore.client()
            prompt_ref = db.collection("cases").document(case_id).collection("prompts").document(prompt_id)
            prompt_ref.update({
                "status": "processed",
                "responseTimestamp": firestore.SERVER_TIMESTAMP
            })
            
            # Return the response
            logging.info(f"Successfully processed prompt {prompt_id} with Vertex AI")
            return ({"response": ai_response}, 200)
        except Exception as e:
            logging.error(f"Error processing prompt with Vertex AI: {str(e)}")
            return ({"error": "Internal Server Error", "message": f"Failed to process prompt with Vertex AI: {str(e)}"}, 500)
    except Exception as e:
        logging.error(f"Error sending prompt to Vertex AI: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to send prompt to Vertex AI"}, 500)

@functions_framework.http
def store_conversation(request):
    """Store the conversation in Firestore.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        tuple: (response, status_code)
    """
    logging.info("Received request to store conversation")
    
    try:
        # Extract data from request
        data = request.get_json(silent=True)
        if not data:
            logging.error("Bad Request: No JSON data provided")
            return ({"error": "Bad Request", "message": "No JSON data provided"}, 400)
        
        # Validate required fields
        if "caseId" not in data:
            logging.error("Bad Request: Missing caseId")
            return ({"error": "Bad Request", "message": "caseId is required"}, 400)
            
        if not isinstance(data["caseId"], str):
            logging.error("Bad Request: caseId must be a string")
            return ({"error": "Bad Request", "message": "caseId must be a string"}, 400)
            
        if not data["caseId"].strip():
            logging.error("Bad Request: caseId cannot be empty")
            return ({"error": "Bad Request", "message": "caseId cannot be empty"}, 400)
        
        if "promptId" not in data:
            logging.error("Bad Request: Missing promptId")
            return ({"error": "Bad Request", "message": "promptId is required"}, 400)
            
        if not isinstance(data["promptId"], str):
            logging.error("Bad Request: promptId must be a string")
            return ({"error": "Bad Request", "message": "promptId must be a string"}, 400)
            
        if not data["promptId"].strip():
            logging.error("Bad Request: promptId cannot be empty")
            return ({"error": "Bad Request", "message": "promptId cannot be empty"}, 400)
        
        if "prompt" not in data:
            logging.error("Bad Request: Missing prompt")
            return ({"error": "Bad Request", "message": "prompt is required"}, 400)
            
        if not isinstance(data["prompt"], str):
            logging.error("Bad Request: prompt must be a string")
            return ({"error": "Bad Request", "message": "prompt must be a string"}, 400)
        
        if "response" not in data:
            logging.error("Bad Request: Missing response")
            return ({"error": "Bad Request", "message": "response is required"}, 400)
            
        if not isinstance(data["response"], str):
            logging.error("Bad Request: response must be a string")
            return ({"error": "Bad Request", "message": "response must be a string"}, 400)
        
        # Extract fields
        case_id = data["caseId"].strip()
        prompt_id = data["promptId"].strip()
        prompt = data["prompt"]
        response = data["response"]
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Verify the case exists
        case_doc = db.collection("cases").document(case_id).get()
        if not case_doc.exists:
            logging.error(f"Not Found: Case with ID {case_id} not found")
            return ({"error": "Not Found", "message": "Case not found"}, 404)
        
        # Store the conversation in a conversations subcollection
        conversation_ref = db.collection("cases").document(case_id).collection("conversations").document(prompt_id)
        conversation_data = {
            "prompt": prompt,
            "response": response,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "userId": "test-user"  # Placeholder until auth is implemented
        }
        conversation_ref.set(conversation_data)
        
        # Return success response
        logging.info(f"Conversation stored for case {case_id} with prompt ID {prompt_id}")
        return ({"message": "Conversation stored"}, 200)
    except Exception as e:
        logging.error(f"Error storing conversation: {str(e)}")
        return ({"error": "Internal Server Error", "message": "Failed to store conversation"}, 500) 