"""
AnuragBot Backend - Flask server with database persistence
Uses SQLAlchemy for conversation storage instead of in-memory
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
from datetime import datetime
import base64
import mimetypes
from PIL import Image
import google.generativeai as genai

# Import database and configuration
from models import db, Conversation, Message, FileAttachment, MessageSource
from config import get_config

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='../frontend/dist', static_folder='../frontend/dist')
app.config.from_object(get_config())

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Gemini AI Setup
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


# ==================== ROUTES ====================

@app.route('/')
def index():
    """Serve main application"""
    return render_template('index.html')


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for current user"""
    try:
        conversations = Conversation.query.all()
        return jsonify([conv.to_dict(include_messages=False) for conv in conversations]), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation"""
    try:
        data = request.get_json()
        title = data.get('title', 'New Conversation')
        
        conversation = Conversation(title=title)
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify(conversation.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/conversations/<conv_id>', methods=['GET'])
def get_conversation(conv_id):
    """Get a specific conversation with messages"""
    try:
        conversation = Conversation.query.get(conv_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify(conversation.to_dict(include_messages=True)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    """Delete a conversation and all its messages"""
    try:
        conversation = Conversation.query.get(conv_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        db.session.delete(conversation)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Conversation deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Send a message and get AI response with optional file attachment"""
    try:
        # Check API configuration
        if not API_KEY or API_KEY == 'your_gemini_api_key_here':
            return jsonify({
                'success': False,
                'error': 'API key not configured. Please set GEMINI_API_KEY in backend/.env'
            }), 500
        
        if not vision_model:
            return jsonify({
                'success': False,
                'error': 'Vision model not initialized. Check your API key.'
            }), 500
        
        # Get request data
        user_message = request.form.get('message', '')
        conv_id = request.form.get('conversation_id')
        language = request.form.get('language', 'English')
        
        if not conv_id:
            # Create new conversation if not provided
            conversation = Conversation(title=f"Chat {datetime.utcnow().isoformat()}")
            db.session.add(conversation)
            db.session.commit()
            conv_id = conversation.id
        else:
            conversation = Conversation.query.get(conv_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
        
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
                
                if len(file_content) > 10 * 1024 * 1024:  # 10MB limit
                    return jsonify({'success': False, 'error': 'File size exceeds 10MB'}), 400
                
                file_data = base64.standard_b64encode(file_content).decode('utf-8')
        
        # Store user message in database
        user_msg = Message(
            conversation_id=conv_id,
            role='user',
            content=user_message,
            file_name=file_name,
            file_type=file_mime_type
        )
        db.session.add(user_msg)
        db.session.commit()
        
        # System prompt
        system_prompt = f"""You are AnuragBot, the official and highly professional AI assistant for Anurag University in Telangana, India. 
You provide accurate, up-to-date information about admissions, academic programs, campus facilities, and student life.
You respond in a polite, friendly, and conversational tone.
Respond entirely in {language}.
If asked about topics unrelated to Anurag University, politely redirect the conversation."""
        
        # Build message content for AI
        message_content = [{'text': system_prompt + '\n\n' + user_message}]
        
        if file_data and file_mime_type:
            message_content.append({
                'inline_data': {
                    'mime_type': file_mime_type,
                    'data': file_data
                }
            })
        
        try:
            # Call Gemini AI
            response = vision_model.generate_content(
                message_content,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                ),
            )
            
            bot_response = response.text if response.text else "I apologize, but I could not generate a response. Please try again."
            
            # Store bot response in database
            bot_msg = Message(
                conversation_id=conv_id,
                role='assistant',
                content=bot_response,
            )
            db.session.add(bot_msg)
            
            # Update conversation timestamp
            conversation.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'response': bot_response,
                'conversation_id': conv_id,
                'sources': []
            }), 200
        
        except Exception as e:
            db.session.rollback()
            error_msg = f"Gemini API Error: {str(e)}"
            print(f"❌ Chat error: {error_msg}")
            
            # Store error response
            error_msg_short = str(e)[:100]
            bot_msg = Message(
                conversation_id=conv_id,
                role='assistant',
                content=f"Sorry, I encountered an error: {error_msg_short}"
            )
            db.session.add(bot_msg)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': error_msg,
                'conversation_id': conv_id
            }), 500
    
    except Exception as e:
        db.session.rollback()
        error_msg = f"Server error: {str(e)}"
        print(f"❌ Server error: {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/api/messages/<conv_id>/<msg_id>', methods=['PUT'])
def edit_message(conv_id, msg_id):
    """Edit a message"""
    try:
        data = request.get_json()
        new_content = data.get('content')
        
        message = Message.query.filter_by(id=msg_id, conversation_id=conv_id).first()
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        message.content = new_content
        message.edited = True
        message.edited_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': message.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/messages/<conv_id>/<msg_id>', methods=['DELETE'])
def delete_message(conv_id, msg_id):
    """Delete a message"""
    try:
        message = Message.query.filter_by(id=msg_id, conversation_id=conv_id).first()
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        db.session.delete(message)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Message deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/export', methods=['POST'])
def export_conversation():
    """Export conversation as markdown or JSON"""
    try:
        data = request.get_json()
        conv_id = data.get('conversation_id')
        export_format = data.get('format', 'markdown')
        
        conversation = Conversation.query.get(conv_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        if export_format == 'json':
            return jsonify(conversation.to_dict(include_messages=True)), 200
        
        # Markdown format
        markdown = f"# {conversation.title}\n\n"
        markdown += f"Created: {conversation.created_at.isoformat()}\n"
        markdown += f"Updated: {conversation.updated_at.isoformat()}\n\n"
        
        for msg in conversation.messages:
            role = "**User**" if msg.role == 'user' else "**Assistant**"
            markdown += f"{role} ({msg.timestamp.isoformat()}):\n{msg.content}\n\n"
        
        return jsonify({
            'content': markdown,
            'filename': f"{conversation.title}.md"
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/regenerate', methods=['POST'])
def regenerate_response():
    """Regenerate the last bot response"""
    try:
        data = request.get_json()
        conv_id = data.get('conversation_id')
        
        conversation = Conversation.query.get(conv_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Find last user message and remove last bot response
        messages = conversation.messages
        if len(messages) < 2:
            return jsonify({'error': 'No previous message to regenerate'}), 400
        
        # Remove last bot response if it exists
        if messages[-1].role == 'assistant':
            db.session.delete(messages[-1])
            db.session.commit()
        
        # Get last user message
        last_user_msg = None
        for msg in reversed(messages):
            if msg.role == 'user':
                last_user_msg = msg.content
                break
        
        if not last_user_msg:
            return jsonify({'error': 'No user message found'}), 400
        
        # Re-process the message through chat endpoint
        # Create a new request context for chat
        from werkzeug.datastructures import ImmutableMultiDict
        request.form = ImmutableMultiDict({
            'message': last_user_msg,
            'conversation_id': conv_id,
            'language': 'English'
        })
        
        return chat()
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected' if db.engine.execute("SELECT 1") else 'disconnected'
    }), 200


# ==================== DATABASE INITIALIZATION ====================

@app.shell_context_processor
def make_shell_context():
    """Add database models to Flask shell"""
    return {'db': db, 'Conversation': Conversation, 'Message': Message}


@app.before_request
def init_db():
    """Initialize database tables if they don't exist"""
    try:
        # This runs on first request - creates tables if needed
        if not hasattr(app, 'db_initialized'):
            db.create_all()
            app.db_initialized = True
    except Exception as e:
        print(f"⚠️ Database initialization error: {e}")


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("\n" + "="*60)
    print("🚀 AnuragBot Backend Starting...")
    print("="*60)
    print(f"📊 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🤖 AI Model: {'Enabled' if vision_model else 'Disabled'}")
    print(f"🔑 API Key: {'Configured' if API_KEY else 'Missing'}")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)
