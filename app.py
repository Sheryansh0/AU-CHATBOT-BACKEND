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
        # Check if API key is configured
        if not PERPLEXITY_API_KEY:
            return jsonify({
                'success': False,
                'error': 'API key not configured. Please set PERPLEXITY_API_KEY in environment variables'
            }), 500
        
        user_message = request.form.get('message', '') or request.get_json().get('message', '')
        conv_id = request.form.get('conversation_id') or request.get_json().get('conversation_id') if request.is_json else request.form.get('conversation_id')
        language = request.form.get('language', 'English') or request.get_json().get('language', 'English') if request.is_json else 'English'
        
        if not conv_id:
            conv_id = conv_manager.create_conversation()
        
        # Add user message to conversation
        conv_manager.add_message(conv_id, 'user', user_message)
        
        # Get conversation history for context
        conversation = conv_manager.get_conversation(conv_id)
        
        # Build messages array with conversation history
        messages = []
        
        # System prompt
        system_prompt = f"""You are AnuragBot, the official and highly professional AI assistant for Anurag University in Telangana, India. 

PRIORITIZE CONCISENESS: Ensure all responses are brief, direct, and limited to only the essential facts. Respond in a very polite, friendly, and human-like conversational tone, avoiding technical jargon where possible.

Your primary goal is to provide accurate, up-to-date, and concise information to parents, students, and visitors regarding the university. Use search to verify all facts, especially for admissions, academic programs, and current events related to "Anurag University".

IMPORTANT: If the user asks a question that is NOT related to Anurag University (e.g., general knowledge, other universities, politics), you MUST politely decline the request by saying something like: "I apologize, but I am trained specifically to assist with queries related to Anurag University. Can I help you with information about our admissions, courses, or campus life?"

ALWAYS respond entirely in the requested language, which is: {language}."""

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
            # Call Perplexity API
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "top_p": 0.9,
                    "search_domain_filter": ["anurag.edu.in"],
                    "return_citations": True,
                    "search_recency_filter": "month"
                },
                timeout=30
            )
            
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
