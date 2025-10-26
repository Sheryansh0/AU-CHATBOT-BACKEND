from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime
import re
import base64
import mimetypes
from io import BytesIO
from PIL import Image
import google.generativeai as genai

load_dotenv()

# Configure Flask to serve the React frontend
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, static_url_path='')
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY or API_KEY == 'your_gemini_api_key_here':
    print("⚠️  WARNING: GEMINI_API_KEY not configured!")
    print("Please set your API key in backend/.env file")
    print("Get your key from: https://aistudio.google.com/app/apikey")
    API_KEY = None
else:
    genai.configure(api_key=API_KEY)

# Generative AI models
vision_model = None
if API_KEY:
    try:
        vision_model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"⚠️  Error initializing vision model: {e}")
        vision_model = None

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
def index():
    return render_template('index.html')

@app.route('/<path:path>')
def catch_all(path):
    """Serve React app for all non-API routes"""
    if path.startswith('api/'):
        # Let API routes 404 if not found
        return jsonify({'error': 'API endpoint not found'}), 404
    # Serve React index.html for client-side routing
    return render_template('index.html')

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
    """Send a message and get a response, with optional file attachment"""
    try:
        # Check if API key is configured
        if not API_KEY or API_KEY == 'your_gemini_api_key_here':
            return jsonify({
                'success': False,
                'error': 'API key not configured. Please set GEMINI_API_KEY in backend/.env file'
            }), 500
        
        if not vision_model:
            return jsonify({
                'success': False,
                'error': 'Vision model not initialized. Check your API key.'
            }), 500
        
        user_message = request.form.get('message', '')
        conv_id = request.form.get('conversation_id')
        language = request.form.get('language', 'English')
        
        if not conv_id:
            conv_id = conv_manager.create_conversation()
        
        # Handle file upload
        file_data = None
        file_mime_type = None
        file_name = None
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                file_name = file.filename
                file_content = file.read()
                file_mime_type = file.mimetype or mimetypes.guess_type(file_name)[0]
                
                # Validate file
                valid_types = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
                if file_mime_type not in valid_types:
                    return jsonify({'success': False, 'error': 'Invalid file type'}), 400
                
                file_data = base64.standard_b64encode(file_content).decode('utf-8')
        
        # Add user message to conversation
        conv_manager.add_message(conv_id, 'user', user_message)
        
        # Get conversation history for context
        conversation = conv_manager.get_conversation(conv_id)
        
        # System prompt
        system_prompt = f"""You are AnuragBot, the official and highly professional AI assistant for Anurag University in Telangana, India. 
You provide accurate, up-to-date information about admissions, academic programs, campus facilities, and student life.
You respond in a polite, friendly, and conversational tone.
Respond entirely in {language}.
If asked about topics unrelated to Anurag University, politely redirect the conversation."""
        
        # Build message content with system prompt and user message
        message_content = [{'text': system_prompt + '\n\n' + user_message}]
        
        if file_data and file_mime_type:
            message_content.append({
                'inline_data': {
                    'mime_type': file_mime_type,
                    'data': file_data
                }
            })
        
        try:
            # Use Google Generative AI SDK for better file handling
            response = vision_model.generate_content(
                message_content,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                ),
            )
            
            bot_response = response.text if response.text else "I apologize, but I could not generate a response. Please try again."
            
            # Add bot response to conversation
            conv_manager.add_message(conv_id, 'assistant', bot_response)
            
            return jsonify({
                'success': True,
                'response': bot_response,
                'sources': [],
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
