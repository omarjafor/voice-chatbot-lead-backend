# Lead Collection Chatbot - Backend API

A FastAPI-based backend service for a voice-enabled lead collection chatbot. The API manages conversation flow, stores lead information, and provides endpoints for session management.

## Features

- RESTful API with FastAPI
- Step-by-step conversation state management
- In-memory lead storage (easily replaceable with database)
- CORS enabled for frontend integration
- Comprehensive test suite
- Clean, extensible code structure

## Tech Stack

- **Framework**: FastAPI 0.115.0
- **Server**: Uvicorn
- **Validation**: Pydantic v2
- **Testing**: pytest + httpx

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

### Development Mode

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Production Mode

```bash
python main.py
```

## API Documentation

Once the server is running, access:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

## API Endpoints

### 1. Start Chat Session
**POST** `/api/chat/start`

Initializes a new conversation session.

**Response:**
```json
{
  "session_id": "uuid-string",
  "message": "What is your name?"
}
```

### 2. Send User Message
**POST** `/api/chat/message`

Processes user response and returns the next question.

**Request:**
```json
{
  "session_id": "uuid-string",
  "message": "User's response"
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "agent_message": "Next question",
  "is_complete": false,
  "current_step": 1
}
```

### 3. Get All Leads
**GET** `/api/leads`

Retrieves all collected lead information.

**Response:**
```json
[
  {
    "id": "uuid-string",
    "name": "John Doe",
    "email": "john@example.com",
    "interest": "Web Development",
    "created_at": "2025-12-31T12:00:00"
  }
]
```

### 4. Get Single Lead
**GET** `/api/leads/{lead_id}`

Retrieves a specific lead by ID.

### 5. Delete Session
**DELETE** `/api/sessions/{session_id}`

Removes a chat session from memory.

## Conversation Flow

The chatbot follows this sequence:

1. **Step 0**: "What is your name?" → Stores as `name`
2. **Step 1**: "What is your email?" → Stores as `email`
3. **Step 2**: "What service are you interested in?" → Stores as `interest`
4. **Step 3**: "Thank you, our team will contact you soon." → Completes conversation & saves lead

## Testing

Run the test suite:

```bash
pytest test_main.py -v
```

Run with coverage:

```bash
pytest test_main.py --cov=main --cov-report=term-missing
```

## Code Structure

```
backend/
├── main.py              # FastAPI application & endpoints
├── requirements.txt     # Python dependencies
├── test_main.py         # Test suite
└── README.md           # This file
```

## Data Storage

Currently uses in-memory dictionaries:
- `sessions`: Stores active conversation sessions
- `leads`: Stores completed lead information

**For production**, replace with a database:
- PostgreSQL with SQLAlchemy
- MongoDB with Motor
- SQLite for lightweight deployments

## Extending the API

### Adding More Conversation Steps

Modify the `CONVERSATION_STEPS` list in `main.py`:

```python
CONVERSATION_STEPS = [
    {"step": 0, "field": "name", "question": "What is your name?"},
    {"step": 1, "field": "email", "question": "What is your email?"},
    {"step": 2, "field": "phone", "question": "What is your phone number?"},  # New step
    {"step": 3, "field": "interest", "question": "What service are you interested in?"},
    {"step": 4, "field": "complete", "question": "Thank you!"}
]
```

### Adding AI Integration

The API accepts text and returns text, making it easy to add:
- OpenAI GPT for dynamic responses
- Custom NLP models
- Intent classification
- Sentiment analysis

Modify the `process_user_message` function to include AI logic before returning the next question.

### Adding Database

1. Install database driver (e.g., `pip install sqlalchemy psycopg2-binary`)
2. Create models for Session and Lead
3. Replace dictionary operations with database queries
4. Add database initialization in startup event

## CORS Configuration

The API allows requests from:
- `http://localhost:3000`
- `http://127.0.0.1:3000`

Modify the `allow_origins` list in `main.py` to add production domains.

## Environment Variables

For production deployment, consider adding:
- `DATABASE_URL`: Database connection string
- `API_KEY`: Authentication key
- `CORS_ORIGINS`: Allowed frontend origins
- `DEBUG`: Enable/disable debug mode

## Troubleshooting

**Port already in use:**
```bash
# Change port number
uvicorn main:app --reload --port 8001
```

**CORS errors:**
- Verify the frontend URL in `allow_origins`
- Check browser console for specific CORS errors

**Import errors:**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

## License

MIT License - Feel free to use and modify for your projects.
