from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import re
import base64
import mimetypes
from PIL import Image
import io

load_dotenv()

# Initialize Flask app - API only (frontend hosted separately on Vercel)
app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration - Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not configured!")
    print("Please set your API key in backend/.env file")
    GEMINI_API_KEY = None
else:
    genai.configure(api_key=GEMINI_API_KEY)
    
# Initialize Gemini model
model = genai.GenerativeModel('gemini-1.5-flash')

# In-memory storage for conversations
conversations = {}
current_conversation_id = None

class ConversationManager:
    def __init__(self):
        self.conversations = {}
        self.current_id = None
    
    def create_conversation(self, title="New Conversation"):
        conv_id = datetime.now().isoformat()
        self.conversations[conv_id] = {
            'id': conv_id,
            'title': title,
            'messages': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        self.current_id = conv_id
        return conv_id
    
    def add_message(self, conv_id, role, content, metadata=None):
        if conv_id in self.conversations:
            self.conversations[conv_id]['messages'].append({
                'id': len(self.conversations[conv_id]['messages']),
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            })
            self.conversations[conv_id]['updated_at'] = datetime.now().isoformat()
    
    def get_conversation(self, conv_id):
        return self.conversations.get(conv_id)
    
    def get_all_conversations(self):
        return list(self.conversations.values())
    
    def delete_conversation(self, conv_id):
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            if self.current_id == conv_id:
                self.current_id = None
    
    def edit_message(self, conv_id, message_id, new_content):
        if conv_id in self.conversations:
            for msg in self.conversations[conv_id]['messages']:
                if msg['id'] == message_id:
                    msg['content'] = new_content
                    msg['edited'] = True
                    msg['edited_at'] = datetime.now().isoformat()
                    return True
        return False

conv_manager = ConversationManager()

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'AU Chatbot Backend API is running',
        'api_version': '1.0',
        'endpoints': ['/api/conversations', '/api/chat']
    })

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations"""
    return jsonify(conv_manager.get_all_conversations())

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation"""
    data = request.get_json()
    title = data.get('title', 'New Conversation')
    conv_id = conv_manager.create_conversation(title)
    conversation = conv_manager.get_conversation(conv_id)
    return jsonify(conversation)

@app.route('/api/conversations/<conv_id>', methods=['GET'])
def get_conversation(conv_id):
    """Get a specific conversation"""
    conv = conv_manager.get_conversation(conv_id)
    if conv:
        return jsonify(conv)
    return jsonify({'error': 'Conversation not found'}), 404

@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    """Delete a conversation"""
    conv_manager.delete_conversation(conv_id)
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Send a message and get a response using Gemini API"""
    try:
        # Log API key status (without exposing the actual key)
        api_key_status = "configured" if GEMINI_API_KEY else "missing"
        print(f"🔑 API Key Status: {api_key_status}")
        
        # Check if API key is configured
        if not GEMINI_API_KEY:
            error_msg = 'GEMINI_API_KEY environment variable is not set. Please add it in Environment settings.'
            print(f"❌ {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
        # Get request data (handle both JSON and form data)
        if request.is_json:
            data = request.get_json()
            user_message = data.get('message', '')
            conv_id = data.get('conversation_id')
            language = data.get('language', 'English')
            image_data = data.get('image')
            file_data = data.get('file')
            print(f"📨 Request type: JSON")
        else:
            user_message = request.form.get('message', '')
            conv_id = request.form.get('conversation_id')
            language = request.form.get('language', 'English')
            image_data = request.form.get('image')
            file_data = request.form.get('file')
            print(f"📨 Request type: FormData")
        
        print(f"💬 Message: {user_message[:50]}...")
        print(f"🆔 Conversation ID: {conv_id}")
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        if not conv_id:
            conv_id = conv_manager.create_conversation()
            print(f"✨ Created new conversation: {conv_id}")
        
        # Add user message to conversation
        conv_manager.add_message(conv_id, 'user', user_message)
        
        # Get conversation history for context
        conversation = conv_manager.get_conversation(conv_id)
        
        # Build context from conversation history
        context = f"""You are AnuragBot, the official AI assistant for Anurag University in Telangana, India. 

Your primary goal is to provide accurate, up-to-date information to parents, students, and visitors about:
- Admissions process and requirements
- Academic programs and courses
- Campus facilities and infrastructure
- Placements and career opportunities
- Contact information and location
- Events and announcements

IMPORTANT INSTRUCTIONS:
- PRIORITIZE ACCURACY: Only provide verified information about Anurag University
- PRIORITIZE CONCISENESS: Keep responses brief, direct, and focused on essential facts
- Use a polite, friendly, and conversational tone
- If a question is NOT related to Anurag University, politely decline and redirect
- For information you're uncertain about, suggest visiting the official website or contacting the university
- Always respond entirely in: {language}

Conversation History:
"""
        
        # Add recent conversation history
        for msg in conversation['messages'][-10:]:
            role = "User" if msg['role'] == 'user' else "AnuragBot"
            context += f"{role}: {msg['content']}\n"
        
        context += f"\nUser: {user_message}\nAnuragBot:"
        
        try:
            print(f"🌐 Calling Gemini API...")
            
            # Prepare content for Gemini
            content_parts = []
            
            # Add text
            content_parts.append(context)
            
            # Handle image if provided
            if image_data:
                try:
                    # Remove data URL prefix if present
                    if ',' in image_data:
                        image_data = image_data.split(',')[1]
                    
                    # Decode base64 image
                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(io.BytesIO(image_bytes))
                    content_parts.append(image)
                    print("📷 Image attached to request")
                except Exception as img_error:
                    print(f"⚠️  Image processing error: {str(img_error)}")
            
            # Handle PDF/document if provided
            if file_data:
                try:
                    # Remove data URL prefix if present
                    if ',' in file_data:
                        mime_type, file_data = file_data.split(',', 1)
                    
                    # Decode base64 file
                    file_bytes = base64.b64decode(file_data)
                    
                    # For PDF files, extract text or pass to Gemini
                    content_parts.append({
                        'mime_type': 'application/pdf',
                        'data': file_bytes
                    })
                    print("📄 PDF attached to request")
                except Exception as file_error:
                    print(f"⚠️  File processing error: {str(file_error)}")
            
            # Generate response using Gemini
            response = model.generate_content(
                content_parts,
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 2048,
                }
            )
            
            bot_response = response.text
            print(f"✅ Gemini API response received")
            
            # Add bot response to conversation
            conv_manager.add_message(conv_id, 'assistant', bot_response)
            
            return jsonify({
                'success': True,
                'response': bot_response,
                'conversation_id': conv_id
            })
            
        except Exception as e:
            error_msg = f"Gemini API Error: {str(e)}"
            print(f"❌ Chat error: {error_msg}")
            conv_manager.add_message(conv_id, 'assistant', 
                f"Sorry, I encountered an error: {str(e)[:100]}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'conversation_id': conv_id
            }), 500
    
    except Exception as e:
        error_msg = f"Server error: {str(e)}"
        print(f"❌ Server error: {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@app.route('/api/messages/<conv_id>/<int:message_id>', methods=['PUT'])
def edit_message(conv_id, message_id):
    """Edit a message"""
    data = request.get_json()
    new_content = data.get('content')
    success = conv_manager.edit_message(conv_id, message_id, new_content)
    return jsonify({'success': success})

@app.route('/api/regenerate', methods=['POST'])
def regenerate_response():
    """Regenerate the last bot response"""
    data = request.get_json()
    conv_id = data.get('conversation_id')
    
    conversation = conv_manager.get_conversation(conv_id)
    if not conversation or len(conversation['messages']) < 2:
        return jsonify({'error': 'No previous message to regenerate'}), 400
    
    # Remove last bot response
    if conversation['messages'][-1]['role'] == 'assistant':
        conversation['messages'].pop()
    
    # Get the last user message
    last_user_msg = None
    for msg in reversed(conversation['messages']):
        if msg['role'] == 'user':
            last_user_msg = msg['content']
            break
    
    if not last_user_msg:
        return jsonify({'error': 'No user message found'}), 400
    
    # Re-send the request
    return chat()

@app.route('/api/export', methods=['POST'])
def export_conversation():
    """Export conversation as markdown or JSON"""
    data = request.get_json()
    conv_id = data.get('conversation_id')
    export_format = data.get('format', 'markdown')
    
    conversation = conv_manager.get_conversation(conv_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    if export_format == 'json':
        return jsonify(conversation)
    
    # Markdown format
    markdown = f"# {conversation['title']}\n\n"
    markdown += f"Created: {conversation['created_at']}\n\n"
    
    for msg in conversation['messages']:
        role = "**User**" if msg['role'] == 'user' else "**Assistant**"
        markdown += f"{role}:\n{msg['content']}\n\n"
    
    return jsonify({
        'content': markdown,
        'filename': f"{conversation['title']}.md"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
