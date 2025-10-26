"""
Database models for AnuragBot using SQLAlchemy
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()

class Conversation(db.Model):
    """Conversation model for storing chat sessions"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False, default='New Conversation')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_messages=True):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
        if include_messages:
            data['messages'] = [msg.to_dict() for msg in self.messages]
        return data


class Message(db.Model):
    """Message model for storing individual messages"""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime)
    
    # File attachment info
    file_name = db.Column(db.String(255))
    file_type = db.Column(db.String(50))  # MIME type
    
    # Metadata for sources, etc.
    metadata = db.Column(db.JSON, default={})
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'edited': self.edited,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'file': {
                'name': self.file_name,
                'type': self.file_type
            } if self.file_name else None,
            'metadata': self.metadata,
        }


class FileAttachment(db.Model):
    """File attachment model for tracking uploaded files"""
    __tablename__ = 'file_attachments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = db.Column(db.String(36), db.ForeignKey('messages.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # MIME type
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    storage_path = db.Column(db.String(500), nullable=False)  # local or S3 path
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'uploaded_at': self.uploaded_at.isoformat(),
        }


class MessageSource(db.Model):
    """Model for tracking sources/citations in responses"""
    __tablename__ = 'message_sources'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = db.Column(db.String(36), db.ForeignKey('messages.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    uri = db.Column(db.String(500), nullable=False)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'title': self.title,
            'uri': self.uri,
        }
