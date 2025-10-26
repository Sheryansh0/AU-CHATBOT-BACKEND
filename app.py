from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime
import re
import base64
import mimetypes

load_dotenv()

# Initialize Flask app - API only (frontend hosted separately on Vercel)
app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration - Perplexity API
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
if not PERPLEXITY_API_KEY:
    print("⚠️  WARNING: PERPLEXITY_API_KEY not configured!")
    print("Please set your API key in backend/.env file")
    PERPLEXITY_API_KEY = None

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
    """Send a message and get a response using Perplexity API"""
    try:
        # Log API key status (without exposing the actual key)
        api_key_status = "configured" if PERPLEXITY_API_KEY else "missing"
        print(f"🔑 API Key Status: {api_key_status}")
        
        # Check if API key is configured
        if not PERPLEXITY_API_KEY:
            error_msg = 'PERPLEXITY_API_KEY environment variable is not set on Render. Please add it in Environment settings.'
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
            print(f"📨 Request type: JSON")
        else:
            user_message = request.form.get('message', '')
            conv_id = request.form.get('conversation_id')
            language = request.form.get('language', 'English')
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
        
        # Build messages array with conversation history
        messages = []
        
        # System prompt
        system_prompt = f"""You are AnuragBot, the official and highly professional AI assistant for Anurag University in Telangana, India. 

CRITICAL INSTRUCTIONS:
1. ALWAYS retrieve information ONLY from the official Anurag University website: https://anurag.edu.in/
2. PRIORITIZE ACCURACY: Verify all information against anurag.edu.in before responding
3. PRIORITIZE CONCISENESS: Keep responses brief, direct, and focused on essential facts
4. Use a polite, friendly, and conversational tone

SEARCH STRATEGY FOR FACULTY/DEPARTMENT INFORMATION:
- For HOD queries: Search for "anurag.edu.in [department] head of department" or "anurag.edu.in [department] HOD" or browse faculty pages
- For faculty queries: Search for "anurag.edu.in faculty [department]" or "anurag.edu.in [department] staff"
- For department info: Search for "anurag.edu.in [department] overview" or "anurag.edu.in academics [department]"
- ALWAYS check faculty/staff directories, department pages, and about sections

Your primary goal is to provide accurate, up-to-date information to parents, students, and visitors about:
- Admissions process and requirements
- Academic programs and courses
- Campus facilities and infrastructure
- Placements and career opportunities
- Contact information and location
- Events and announcements
- Faculty and department leadership

IMPORTANT RESTRICTIONS:
- If a question is NOT related to Anurag University, politely decline and redirect
- Always cite information from anurag.edu.in when available
- If information is not found on the official website, clearly state that

ALWAYS respond entirely in: {language}."""

        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add conversation history (last 10 messages for context)
        for msg in conversation['messages'][-10:]:
            messages.append({
                "role": "user" if msg['role'] == 'user' else "assistant",
                "content": msg['content']
            })
        
        try:
            print(f"🌐 Calling Perplexity API...")
            # Call Perplexity API
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar",
                    "messages": messages,
                    "temperature": 0.2,  # Lower temperature for more accurate, factual responses
                    "max_tokens": 2048,
                    "top_p": 0.9,
                    "search_domain_filter": ["anurag.edu.in"],  # Only search official Anurag University website
                    "return_citations": True,
                    "search_recency_filter": "month",
                    "return_images": False,
                    "return_related_questions": False
                },
                timeout=30
            )
            
            print(f"✅ Perplexity API response status: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Perplexity API Error: {response.status_code} - {response.text}"
                print(f"❌ Chat error: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'conversation_id': conv_id
                }), 500
            
            response_data = response.json()
            bot_response = response_data['choices'][0]['message']['content']
            
            # Extract citations if available
            sources = []
            if 'citations' in response_data:
                sources = response_data['citations']
            
            # Add bot response to conversation
            conv_manager.add_message(conv_id, 'assistant', bot_response)
            
            return jsonify({
                'success': True,
                'response': bot_response,
                'sources': sources,
                'conversation_id': conv_id
            })
        
        except requests.exceptions.Timeout:
            error_msg = "Request timeout. Please try again."
            print(f"❌ Timeout error")
            return jsonify({
                'success': False,
                'error': error_msg,
                'conversation_id': conv_id
            }), 504
            
        except Exception as e:
            error_msg = f"Perplexity API Error: {str(e)}"
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
