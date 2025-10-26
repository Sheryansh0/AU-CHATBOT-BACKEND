# AnuragBot Backend

Flask-based backend server for AnuragBot AI assistant. Handles conversation management, file uploads, and integration with Google's Gemini AI.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API Key

### Setup

1. **Navigate to backend directory:**

```powershell
cd backend
```

2. **Create virtual environment:**

```powershell
python -m venv venv
```

3. **Activate virtual environment:**

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate
```

4. **Install dependencies:**

```powershell
pip install -r requirements.txt
```

5. **Create .env file:**

```powershell
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

6. **Run server:**

```powershell
python app.py
# Server runs on http://localhost:5000
```

## 📚 API Endpoints

### GET `/api/conversations`

Get all conversations

- **Response:** Array of conversation objects

### POST `/api/conversations`

Create new conversation

- **Body:** `{ "title": "Chat Title" }`
- **Response:** New conversation object

### GET `/api/conversations/<id>`

Get specific conversation

- **Response:** Conversation object with messages

### DELETE `/api/conversations/<id>`

Delete conversation

- **Response:** `{ "success": true }`

### POST `/api/chat`

Send message with optional file

- **Body (FormData):**
  - `message` - Text message
  - `conversation_id` - Conversation ID
  - `language` - Response language (English/Telugu/Hindi)
  - `file` - Optional image/PDF file
- **Response:** AI response with metadata

### POST `/api/export`

Export conversation

- **Body:** `{ "conversation_id": "id", "format": "markdown" | "json" }`
- **Response:** Exportable content

### POST `/api/regenerate`

Regenerate last AI response

- **Body:** `{ "conversation_id": "id" }`
- **Response:** New AI response

### PUT `/api/messages/<conv_id>/<msg_id>`

Edit message

- **Body:** `{ "content": "new content" }`
- **Response:** `{ "success": true }`

## 🔧 Configuration

### Environment Variables (.env)

```
GEMINI_API_KEY=your_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
```

### Flask Config (app.py)

- **MAX_CONTENT_LENGTH:** 16 MB (max file upload size)
- **CORS:** Enabled for all origins
- **Port:** 5000
- **Debug:** True (development)

## 📦 Dependencies

- `Flask` 3.1.2 - Web framework
- `flask-cors` 6.0.1 - CORS support
- `google-generativeai` 0.7.0 - Gemini API
- `python-dotenv` 1.2.0 - Env variable management
- `Pillow` 10.1.0 - Image processing
- `Werkzeug` 3.1.3 - WSGI utilities
- `requests` 2.32.5 - HTTP library

## 🤖 AI Configuration

### Model: Gemini 2.0 Flash

- **Vision Capabilities:** Image analysis (JPG, PNG, WebP)
- **Document Support:** PDF analysis
- **Temperature:** 0.7 (balanced creativity/consistency)
- **Max Tokens:** 2048

### System Prompt

AnuragBot is configured as a professional AI assistant for Anurag University:

- Provides information about admissions, programs, campus facilities
- Responds in selected language (English, Telugu, Hindi)
- Redirects off-topic questions politely

## 📝 File Upload

### Supported Formats

- **Images:** JPG, PNG, WebP (2-5 MB typical)
- **Documents:** PDF (up to 10 MB)

### Processing Flow

1. File received via FormData
2. MIME type validation
3. Base64 encoding
4. Sent to Gemini API as inline_data
5. AI analyzes and responds

## 🧠 Conversation Management

### In-Memory Storage

- Conversations stored in memory (ConversationManager class)
- Lost on server restart
- Good for development/testing

### Production Considerations

- Implement database persistence (MongoDB, PostgreSQL)
- Add conversation archival
- Implement message deletion policies

## 🔐 Security

### Current Implementation

- CORS enabled (⚠️ adjust for production)
- No authentication/authorization
- API key in environment variable

### Production Recommendations

- Restrict CORS origins
- Add user authentication
- Implement API rate limiting
- Add input validation/sanitization
- Use HTTPS only
- Add request logging

## 🐛 Troubleshooting

### Port 5000 already in use

```powershell
# Find and kill process using port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or change port in app.py:
# app.run(debug=True, port=5001)
```

### GEMINI_API_KEY not found

- Ensure .env file exists in backend directory
- Verify format: `GEMINI_API_KEY=your_key_here` (no quotes)
- Restart server after changing .env

### File upload fails

- Check file size (max 10 MB)
- Verify MIME type (JPG/PNG/WebP/PDF)
- Ensure API key has vision model access

### CORS errors from frontend

- Check frontend is accessing `http://localhost:5000`
- Verify CORS(app) is initialized in app.py
- Check browser console for specific error

## 📊 Performance Tips

- File uploads are synchronous (consider async for large files)
- Conversations kept in memory (consider pagination for many conversations)
- Gemini API calls have rate limits (implement queue if needed)

## 🚢 Deployment

### Gunicorn (Production)

```powershell
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Environment Variables

Set production variables before deployment:

```
GEMINI_API_KEY=production_key
FLASK_ENV=production
FLASK_DEBUG=False
```

### Database Setup

1. Choose database (PostgreSQL recommended)
2. Implement models for conversations/messages
3. Update ConversationManager to use database
4. Add migration scripts

---

For full project documentation, see [../README.md](../README.md)
