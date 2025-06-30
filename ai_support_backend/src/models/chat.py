from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class ChatInteraction(db.Model):
    """Model for storing chat interactions"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=True)
    response_type = db.Column(db.String(50), nullable=False)  # 'answered' or 'contact_requested'
    data_source_url = db.Column(db.String(500), nullable=True)  # URL of scraped data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatInteraction {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_message': self.user_message,
            'bot_response': self.bot_response,
            'response_type': self.response_type,
            'data_source_url': self.data_source_url,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class ContactRequest(db.Model):
    """Model for storing contact requests when questions can't be answered"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    question = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')  # 'pending', 'responded', 'closed'
    admin_notified = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ContactRequest {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'name': self.name,
            'email': self.email,
            'question': self.question,
            'status': self.status,
            'admin_notified': self.admin_notified,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class KnowledgeBase(db.Model):
    """Model for storing scraped knowledge base data"""
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False, unique=True)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    last_scraped = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<KnowledgeBase {self.url}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'content': self.content,
            'last_scraped': self.last_scraped.isoformat() if self.last_scraped else None,
            'is_active': self.is_active
        }

