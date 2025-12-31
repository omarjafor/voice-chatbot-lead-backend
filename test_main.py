from fastapi.testclient import TestClient
from main import app, sessions, leads

client = TestClient(app)

def setup_function():
    """Clear data before each test"""
    sessions.clear()
    leads.clear()

def test_read_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

def test_start_chat_session():
    """Test starting a new chat session"""
    response = client.post("/api/chat/start")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["message"] == "What is your name?"

def test_conversation_flow():
    """Test complete conversation flow"""
    # Start session
    start_response = client.post("/api/chat/start")
    session_id = start_response.json()["session_id"]
    
    # Send name
    response = client.post("/api/chat/message", json={
        "session_id": session_id,
        "message": "John Doe"
    })
    assert response.status_code == 200
    assert response.json()["agent_message"] == "What is your email?"
    assert response.json()["is_complete"] == False
    
    # Send email
    response = client.post("/api/chat/message", json={
        "session_id": session_id,
        "message": "john@example.com"
    })
    assert response.status_code == 200
    assert response.json()["agent_message"] == "What service are you interested in?"
    
    # Send interest
    response = client.post("/api/chat/message", json={
        "session_id": session_id,
        "message": "Web Development"
    })
    assert response.status_code == 200
    assert response.json()["is_complete"] == True
    assert "thank you" in response.json()["agent_message"].lower()

def test_get_leads():
    """Test retrieving leads after conversation"""
    # Create a complete conversation
    start_response = client.post("/api/chat/start")
    session_id = start_response.json()["session_id"]
    
    client.post("/api/chat/message", json={"session_id": session_id, "message": "Jane Smith"})
    client.post("/api/chat/message", json={"session_id": session_id, "message": "jane@example.com"})
    client.post("/api/chat/message", json={"session_id": session_id, "message": "Marketing"})
    
    # Get leads
    response = client.get("/api/leads")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Jane Smith"

def test_invalid_session():
    """Test sending message with invalid session ID"""
    response = client.post("/api/chat/message", json={
        "session_id": "invalid-id",
        "message": "Test"
    })
    assert response.status_code == 404
