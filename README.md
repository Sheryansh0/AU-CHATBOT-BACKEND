# AnuragBot - AI Assistant for Anurag University

A modern, full-stack chatbot application built with React, TypeScript, and Flask. AnuragBot provides information about Anurag University using Google's Gemini AI with vision and document analysis capabilities.

## 🏗️ Project Structure

```
modern-chatbot/
├── backend/                    # Flask backend server
│   ├── app.py                 # Main Flask application
│   ├── requirements.txt        # Python dependencies
│   └── .env.example           # Environment variables template
│
├── frontend/                   # React + TypeScript frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── store/             # Zustand state management
│   │   ├── App.tsx            # Main App component
│   │   └── main.tsx           # React entry point
│   ├── package.json
│   ├── vite.config.ts         # Vite configuration
│   └── tailwind.config.ts      # Tailwind CSS config
│
├── package.json               # Root package.json
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** 16+ (for frontend)
- **Python** 3.8+ (for backend)
- **Google Gemini API Key** (get it from [AI Studio](https://aistudio.google.com/app/apikey))

### Backend Setup

1. **Navigate to backend directory:**

```powershell
cd backend
```

2. **Create Python virtual environment:**

```powershell
python -m venv venv
```

3. **Activate virtual environment:**

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows Command Prompt
venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate
```

4. **Install dependencies:**

```powershell
pip install -r requirements.txt
```

5. **Set up environment variables:**

```powershell
# Copy .env.example to .env
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_api_key_here
```

6. **Run backend server:**

```powershell
python app.py
# Server will start on http://localhost:5000
```

### Frontend Setup

1. **Open new terminal and navigate to frontend:**

```powershell
cd frontend
```

2. **Install dependencies:**

```powershell
npm install
```

3. **Run development server:**

```powershell
npm run dev
# Frontend will be available at http://localhost:3000
```

The frontend will automatically proxy API calls to `http://localhost:5000`.

## 🎯 Features

### ✅ Chat Functionality

- 💬 Real-time text chat with Gemini AI
- 🗣️ Voice input (speech-to-text)
- 🌐 Multi-language support (English, Telugu, Hindi)
- 📝 Conversation history and management

### ✅ File Upload & Analysis

- 📸 **Image Analysis**: Upload JPG, PNG, WebP images
- 📄 **PDF Analysis**: Upload and analyze PDF documents
- 🤖 **Gemini Vision**: AI-powered image and document analysis
- 📊 File preview in chat interface

### ✅ UI/UX Features

- 🎨 Dark mode support
- 🎭 Smooth animations with Framer Motion
- 📱 Responsive design
- ⚙️ Settings panel for customization
- 💾 Export conversations (Markdown/JSON)
- 🗑️ Conversation deletion

### ✅ Backend Features

- ⚡ RESTful API endpoints
- 🔄 In-memory conversation storage
- 📦 File upload handling (10MB limit)
- 🔐 CORS enabled for frontend communication

## 📚 API Endpoints

### Conversations

- `GET /api/conversations` - Get all conversations
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations/<id>` - Get specific conversation
- `DELETE /api/conversations/<id>` - Delete conversation

### Chat

- `POST /api/chat` - Send message (supports file upload via FormData)
- `POST /api/export` - Export conversation
- `POST /api/regenerate` - Regenerate last response
- `PUT /api/messages/<conv_id>/<msg_id>` - Edit message

## 🛠️ Development

### Build Frontend for Production

```powershell
cd frontend
npm run build
# Output: ../frontend/dist (served by Flask)
```

### Run Full Application in Production

1. Build frontend first
2. Run backend:

```powershell
cd backend
python app.py
```

3. Access at `http://localhost:5000`

### Lint & Format

```powershell
# Frontend
cd frontend
npm run lint

# Backend (manual with pylint/black)
# Install: pip install pylint black
# Format: black app.py
# Lint: pylint app.py
```

## 🔐 Environment Variables

### Backend `.env`

```
GEMINI_API_KEY=your_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
```

## 📦 Dependencies

### Frontend

- **React** 18.2.0 - UI library
- **TypeScript** 5.2.2 - Type safety
- **Vite** 5.0.8 - Build tool
- **Tailwind CSS** 3.3.6 - Styling
- **Zustand** 4.4.2 - State management
- **Axios** 1.6.2 - HTTP client
- **Framer Motion** 10.16.16 - Animations
- **React Router** 6.20.0 - Routing
- **Lucide React** 0.294.0 - Icons

### Backend

- **Flask** 3.1.2 - Web framework
- **Flask-CORS** 6.0.1 - CORS support
- **google-generativeai** 0.7.0 - Gemini API
- **python-dotenv** 1.2.0 - Environment variables
- **Pillow** 10.1.0 - Image processing
- **Werkzeug** 3.1.3 - WSGI utilities

## 🐛 Troubleshooting

### Backend won't start

- ✅ Check if port 5000 is available
- ✅ Ensure Python virtual environment is activated
- ✅ Verify all dependencies installed: `pip install -r requirements.txt`
- ✅ Check GEMINI_API_KEY is set in .env

### Frontend can't connect to backend

- ✅ Verify backend is running on port 5000
- ✅ Check that vite.config.ts proxy is set to `http://localhost:5000`
- ✅ Look for CORS errors in browser console
- ✅ Clear browser cache

### File upload not working

- ✅ Check file type is JPG, PNG, WebP, or PDF
- ✅ Verify file size is less than 10MB
- ✅ Ensure GEMINI_API_KEY is valid and has vision model access

### Voice input issues

- ✅ Use Chrome, Edge, or Safari (best support)
- ✅ Allow microphone permissions when prompted
- ✅ Check browser console for errors

## 📝 Notes

- Conversations are stored **in-memory** and will be lost on server restart
- For production, implement database persistence
- Keep GEMINI_API_KEY secure - never commit to version control
- The project uses Vite for fast HMR during development

## 🤝 Contributing

Feel free to submit issues and pull requests to improve the project!

## 📄 License

This project is open source and available under the MIT License.

## 📞 Support

For issues or questions about AnuragBot, please open an issue on the repository.

---

**Built with ❤️ for Anurag University**
