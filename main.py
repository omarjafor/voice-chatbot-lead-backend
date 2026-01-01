from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, List
from datetime import datetime
import uuid
import re

app = FastAPI(title="Lead Collection Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: Dict[str, dict] = {}
leads: List[dict] = []

MAX_RETRIES = 2

CONVERSATION_STEPS = [
    {"step": 0, "field": "name", "question": "What is your name?", "validate": False, "confirm": False},
    {"step": 1, "field": "email", "question": "What is your email address?", "validate": True, "confirm": False},
    {"step": 2, "field": "email_confirm", "question": "", "validate": False, "confirm": True},
    {"step": 3, "field": "phone", "question": "What is your phone number?", "validate": True, "confirm": False},
    {"step": 4, "field": "phone_confirm", "question": "", "validate": False, "confirm": True},
    {"step": 5, "field": "interest", "question": "What service are you interested in?", "validate": False, "confirm": False},
    {"step": 6, "field": "complete", "question": "Thank you for your information! Our team will contact you soon.", "validate": False, "confirm": False}
]

class SessionStartResponse(BaseModel):
    session_id: str
    message: str

class UserMessage(BaseModel):
    session_id: str
    message: str

class AgentResponse(BaseModel):
    session_id: str
    agent_message: str
    is_complete: bool
    current_step: int
    validation_error: Optional[str] = None
    should_auto_listen: bool = True  # New field to control auto-listen

class Lead(BaseModel):
    id: str
    session_id: str
    name: str
    email: EmailStr
    phone: str
    interest: str
    created_at: str

def normalize_email(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'\s+', '', text) 
    
    text = re.sub(r'at\s*the\s*rate\s*of', '@', text, flags=re.IGNORECASE)
    text = re.sub(r'at\s*the\s*rate', '@', text, flags=re.IGNORECASE)
    text = re.sub(r'\sat\s', '@', text, flags=re.IGNORECASE)
    text = re.sub(r'^at\s', '@', text, flags=re.IGNORECASE)
    text = re.sub(r'\sat$', '@', text, flags=re.IGNORECASE)
    
    text = re.sub(r'\s*dot\s*', '.', text, flags=re.IGNORECASE)
    
    text = re.sub(r'gmail', 'gmail', text, flags=re.IGNORECASE)
    text = re.sub(r'g\s*mail', 'gmail', text, flags=re.IGNORECASE)
    
    return text

def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def normalize_phone(text: str) -> str:
    digits = re.sub(r'[^\d+]', '', text)
    return digits

def is_valid_phone(phone: str) -> bool:
    digits_only = re.sub(r'[^\d]', '', phone)
    return 10 <= len(digits_only) <= 15

def is_confirmation_positive(text: str) -> bool:
    text = text.lower().strip()
    positive_words = ['yes', 'yeah', 'yep', 'correct', 'right', 'that\'s right', 'that is right', 'ok', 'okay', 'sure', 'yup', 'affirmative', 'confirm']
    return any(word in text for word in positive_words)

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Lead Collection Chatbot API", "status": "running"}

@app.post("/api/chat/start", response_model=SessionStartResponse)
def start_chat_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "current_step": 0,
        "data": {},
        "email_retry_count": 0,
        "phone_retry_count": 0,
        "created_at": datetime.now().isoformat()
    }
    
    return SessionStartResponse(
        session_id=session_id,
        message=CONVERSATION_STEPS[0]["question"]
    )

@app.post("/api/chat/message", response_model=AgentResponse)
def process_user_message(user_message: UserMessage):
    session_id = user_message.session_id
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    current_step = session["current_step"]
    
    if current_step >= len(CONVERSATION_STEPS):
        raise HTTPException(status_code=400, detail="Conversation already complete")
    
    current_field_config = CONVERSATION_STEPS[current_step]
    field_name = current_field_config["field"]
    user_input = user_message.message.strip()
    
    # Handle email confirmation
    if field_name == "email_confirm":
        if is_confirmation_positive(user_input):
            # Reset retry count on successful confirmation
            session["email_retry_count"] = 0
            session["current_step"] += 1
            next_step = session["current_step"]
            return AgentResponse(
                session_id=session_id,
                agent_message=CONVERSATION_STEPS[next_step]["question"],
                is_complete=False,
                current_step=next_step,
                should_auto_listen=True  # Auto-listen enabled
            )
        else:
            session["email_retry_count"] = session.get("email_retry_count", 0) + 1
            
            if session["email_retry_count"] >= MAX_RETRIES:
                return AgentResponse(
                    session_id=session_id,
                    agent_message=f"I'm having trouble with the email. Please type it in the chat box instead.",
                    is_complete=False,
                    current_step=1,
                    validation_error="max_retries_email",
                    should_auto_listen=False  # Disable auto-listen
                )
            
            session["current_step"] = 1
            session["data"].pop("email", None)
            return AgentResponse(
                session_id=session_id,
                agent_message="No problem. Let's try again. What is your email address?",
                is_complete=False,
                current_step=1,
                should_auto_listen=True  # Auto-listen enabled
            )
    
    # Handle phone confirmation
    if field_name == "phone_confirm":
        if is_confirmation_positive(user_input):
            # Reset retry count on successful confirmation
            session["phone_retry_count"] = 0
            session["current_step"] += 1
            next_step = session["current_step"]
            return AgentResponse(
                session_id=session_id,
                agent_message=CONVERSATION_STEPS[next_step]["question"],
                is_complete=False,
                current_step=next_step,
                should_auto_listen=True  # Auto-listen enabled
            )
        else:
            session["phone_retry_count"] = session.get("phone_retry_count", 0) + 1
            
            if session["phone_retry_count"] >= MAX_RETRIES:
                return AgentResponse(
                    session_id=session_id,
                    agent_message=f"I'm having trouble with the phone number. Please type it in the chat box instead.",
                    is_complete=False,
                    current_step=3,
                    validation_error="max_retries_phone",
                    should_auto_listen=False  # Disable auto-listen
                )
            
            session["current_step"] = 3
            session["data"].pop("phone", None)
            return AgentResponse(
                session_id=session_id,
                agent_message="No problem. Let's try again. What is your phone number?",
                is_complete=False,
                current_step=3,
                should_auto_listen=True  # Auto-listen enabled
            )
    
    # Handle email validation
    if current_step < len(CONVERSATION_STEPS) - 1:
        if field_name == "email":
            normalized_email = normalize_email(user_input)
            if not is_valid_email(normalized_email):
                session["email_retry_count"] = session.get("email_retry_count", 0) + 1
                
                if session["email_retry_count"] >= MAX_RETRIES:
                    return AgentResponse(
                        session_id=session_id,
                        agent_message=f"I'm having trouble understanding the email. Please type it in the chat box instead.",
                        is_complete=False,
                        current_step=current_step,
                        validation_error="max_retries_email",
                        should_auto_listen=False  # Disable auto-listen
                    )
                
                retry_message = f"I couldn't understand that email address. Please say it clearly, for example: john at gmail dot com. What is your email?"
                return AgentResponse(
                    session_id=session_id,
                    agent_message=retry_message,
                    is_complete=False,
                    current_step=current_step,
                    validation_error="invalid_email",
                    should_auto_listen=True  # Auto-listen enabled for retry
                )
            
            # Reset retry count on successful validation
            session["email_retry_count"] = 0
            user_input = normalized_email
            session["data"][field_name] = user_input
            session["current_step"] += 1
            next_step = session["current_step"]
            
            confirmation_message = f"Your email is {user_input}. Is this correct? Please say yes correct or no."
            return AgentResponse(
                session_id=session_id,
                agent_message=confirmation_message,
                is_complete=False,
                current_step=next_step,
                should_auto_listen=True  # Auto-listen enabled for confirmation
            )
        
        # Handle phone validation
        elif field_name == "phone":
            normalized_phone = normalize_phone(user_input)
            if not is_valid_phone(normalized_phone):
                session["phone_retry_count"] = session.get("phone_retry_count", 0) + 1
                
                if session["phone_retry_count"] >= MAX_RETRIES:
                    return AgentResponse(
                        session_id=session_id,
                        agent_message=f"I'm having trouble understanding the phone number. Please type it in the chat box instead.",
                        is_complete=False,
                        current_step=current_step,
                        validation_error="max_retries_phone",
                        should_auto_listen=False  # Disable auto-listen
                    )
                
                retry_message = f"I couldn't get a valid phone number. Please say your 10-digit phone number clearly. What is your phone number?"
                return AgentResponse(
                    session_id=session_id,
                    agent_message=retry_message,
                    is_complete=False,
                    current_step=current_step,
                    validation_error="invalid_phone",
                    should_auto_listen=True  # Auto-listen enabled for retry
                )
            
            # Reset retry count on successful validation
            session["phone_retry_count"] = 0
            user_input = normalized_phone
            session["data"][field_name] = user_input
            session["current_step"] += 1
            next_step = session["current_step"]
            
            confirmation_message = f"Your phone number is {user_input}. Is this correct? Please say yes correct or no."
            return AgentResponse(
                session_id=session_id,
                agent_message=confirmation_message,
                is_complete=False,
                current_step=next_step,
                should_auto_listen=True 
            )
        
        # Handle other fields (name, interest)
        else:
            session["data"][field_name] = user_input
    
    session["current_step"] += 1
    next_step = session["current_step"]
    
    # Check if conversation is complete
    if next_step == 6:
        lead = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "name": session["data"].get("name", ""),
            "email": session["data"].get("email", ""),
            "phone": session["data"].get("phone", ""),
            "interest": session["data"].get("interest", ""),
            "created_at": datetime.now().isoformat()
        }
        leads.append(lead)
        
        return AgentResponse(
            session_id=session_id,
            agent_message=CONVERSATION_STEPS[-1]["question"],
            is_complete=True,
            current_step=next_step,
            should_auto_listen=False  # No auto-listen when complete
        )
    
    return AgentResponse(
        session_id=session_id,
        agent_message=CONVERSATION_STEPS[next_step]["question"],
        is_complete=False,
        current_step=next_step,
        should_auto_listen=True  # Auto-listen enabled
    )

@app.get("/api/leads", response_model=List[Lead])
def get_all_leads():
    """Retrieve all collected leads"""
    return leads

@app.get("/api/leads/{lead_id}", response_model=Lead)
def get_lead(lead_id: str):
    """Retrieve a specific lead by ID"""
    for lead in leads:
        if lead["id"] == lead_id:
            return lead
    raise HTTPException(status_code=404, detail="Lead not found")

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    global leads
    before_count = len(leads)
    leads = [lead for lead in leads if lead.get("session_id") != session_id]

    if len(leads) == before_count:
        raise HTTPException(status_code=404, detail="No lead found for this session")

    return {"message": "Lead deleted successfully using session id"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)