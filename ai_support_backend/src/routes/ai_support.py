from flask import Blueprint, jsonify, request, current_app
from src.models.chat import ChatInteraction, ContactRequest, KnowledgeBase, db
from src.services.ai_support import AISupport
import uuid
from datetime import datetime
import os

ai_support_bp = Blueprint('ai_support', __name__)

def get_ai_support_service():
    """Get AI support service instance"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    mail_instance = getattr(current_app, 'mail', None)
    return AISupport(openai_api_key=openai_api_key, mail_instance=mail_instance)

@ai_support_bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat interactions"""
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))
        knowledge_url = data.get('knowledge_url', '')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not knowledge_url:
            return jsonify({'error': 'Knowledge URL is required'}), 400
        
        ai_service = get_ai_support_service()
        
        # Check if we have cached knowledge for this URL
        knowledge_entry = KnowledgeBase.query.filter_by(url=knowledge_url, is_active=True).first()
        
        # If no cached knowledge or it's old (more than 1 hour), scrape again
        should_scrape = (
            not knowledge_entry or 
            (datetime.utcnow() - knowledge_entry.last_scraped).total_seconds() > 3600
        )
        
        if should_scrape:
            scrape_result = ai_service.scrape_webpage(knowledge_url)
            
            if not scrape_result['success']:
                return jsonify({
                    'error': 'Failed to access knowledge base',
                    'details': scrape_result.get('error', 'Unknown error')
                }), 500
            
            # Update or create knowledge base entry
            if knowledge_entry:
                knowledge_entry.content = scrape_result['content']
                knowledge_entry.title = scrape_result['title']
                knowledge_entry.last_scraped = datetime.utcnow()
            else:
                knowledge_entry = KnowledgeBase(
                    url=knowledge_url,
                    title=scrape_result['title'],
                    content=scrape_result['content'],
                    last_scraped=datetime.utcnow()
                )
                db.session.add(knowledge_entry)
            
            db.session.commit()
        
        # Extract relevant content for the question
        relevant_content = ai_service.extract_relevant_content(
            knowledge_entry.content, 
            user_message
        )
        
        # Process with AI
        ai_result = ai_service.process_with_ai(user_message, relevant_content)
        
        if not ai_result['success']:
            return jsonify({
                'error': 'AI processing failed',
                'details': ai_result.get('error', 'Unknown error')
            }), 500
        
        # Determine response type
        can_answer = ai_result.get('can_answer', True)
        response_type = 'answered' if can_answer else 'contact_requested'
        
        # Save chat interaction
        chat_interaction = ChatInteraction(
            session_id=session_id,
            user_message=user_message,
            bot_response=ai_result['response'] if can_answer else None,
            response_type=response_type,
            data_source_url=knowledge_url
        )
        db.session.add(chat_interaction)
        db.session.commit()
        
        response_data = {
            'session_id': session_id,
            'response': ai_result['response'],
            'can_answer': can_answer,
            'response_type': response_type
        }
        
        if not can_answer:
            response_data['contact_form_required'] = True
            response_data['message'] = "I don't have enough information to answer your question. Please provide your contact details so someone can help you."
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_support_bp.route('/contact', methods=['POST'])
def submit_contact():
    """Handle contact form submissions"""
    try:
        data = request.json
        session_id = data.get('session_id', '')
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        question = data.get('question', '').strip()
        
        # Validation
        if not all([session_id, name, email, question]):
            return jsonify({'error': 'All fields are required'}), 400
        
        ai_service = get_ai_support_service()
        
        if not ai_service.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Create contact request
        contact_request = ContactRequest(
            session_id=session_id,
            name=name,
            email=email,
            question=question
        )
        db.session.add(contact_request)
        db.session.commit()
        
        # Send admin notification
        admin_email = os.getenv('ADMIN_EMAIL')
        if admin_email:
            notification_result = ai_service.send_admin_notification(
                contact_request.to_dict(),
                admin_email
            )
            
            if notification_result['success']:
                contact_request.admin_notified = True
                db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your question. Someone will respond to you shortly.',
            'contact_id': contact_request.id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in contact endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_support_bp.route('/knowledge', methods=['GET'])
def get_knowledge_base():
    """Get knowledge base entries"""
    try:
        knowledge_entries = KnowledgeBase.query.filter_by(is_active=True).all()
        return jsonify([entry.to_dict() for entry in knowledge_entries])
        
    except Exception as e:
        current_app.logger.error(f"Error getting knowledge base: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_support_bp.route('/knowledge', methods=['POST'])
def add_knowledge_base():
    """Add new knowledge base URL"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Check if URL already exists
        existing = KnowledgeBase.query.filter_by(url=url).first()
        if existing:
            return jsonify({'error': 'URL already exists in knowledge base'}), 400
        
        ai_service = get_ai_support_service()
        
        # Scrape the URL
        scrape_result = ai_service.scrape_webpage(url)
        
        if not scrape_result['success']:
            return jsonify({
                'error': 'Failed to scrape URL',
                'details': scrape_result.get('error', 'Unknown error')
            }), 400
        
        # Create knowledge base entry
        knowledge_entry = KnowledgeBase(
            url=url,
            title=scrape_result['title'],
            content=scrape_result['content']
        )
        db.session.add(knowledge_entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Knowledge base entry added successfully',
            'entry': knowledge_entry.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error adding knowledge base: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_support_bp.route('/contacts', methods=['GET'])
def get_contact_requests():
    """Get contact requests (admin endpoint)"""
    try:
        status = request.args.get('status', 'all')
        
        query = ContactRequest.query
        if status != 'all':
            query = query.filter_by(status=status)
        
        contact_requests = query.order_by(ContactRequest.timestamp.desc()).all()
        return jsonify([req.to_dict() for req in contact_requests])
        
    except Exception as e:
        current_app.logger.error(f"Error getting contact requests: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_support_bp.route('/contacts/<int:contact_id>', methods=['PUT'])
def update_contact_status(contact_id):
    """Update contact request status"""
    try:
        data = request.json
        status = data.get('status', '').strip()
        
        if status not in ['pending', 'responded', 'closed']:
            return jsonify({'error': 'Invalid status'}), 400
        
        contact_request = ContactRequest.query.get_or_404(contact_id)
        contact_request.status = status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contact status updated successfully',
            'contact': contact_request.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating contact status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_support_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'AI Support Agent'
    })

