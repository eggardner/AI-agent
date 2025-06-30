import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from flask_mail import Message
from datetime import datetime, timedelta
import re
import logging

class AISupport:
    """AI Support service for handling chat interactions, web scraping, and email notifications"""
    
    def __init__(self, openai_api_key=None, mail_instance=None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.mail = mail_instance
        self.logger = logging.getLogger(__name__)
        
    def scrape_webpage(self, url):
        """Scrape content from a webpage"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Get title
            title = soup.title.string if soup.title else "No title"
            
            return {
                'success': True,
                'title': title.strip(),
                'content': text,
                'url': url
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
    
    def process_with_ai(self, user_question, knowledge_content, max_tokens=500):
        """Process user question with AI using scraped knowledge"""
        if not self.openai_client:
            return {
                'success': False,
                'error': 'OpenAI API key not configured'
            }
        
        try:
            # Create system prompt with knowledge base
            system_prompt = f"""You are a helpful customer support assistant. Use the following knowledge base to answer user questions accurately and helpfully.

Knowledge Base:
{knowledge_content}

Instructions:
- Answer questions based only on the information provided in the knowledge base
- If the information is not available in the knowledge base, respond with "I don't have enough information to answer that question. Let me connect you with someone who can help."
- Be concise but thorough in your responses
- Maintain a friendly and professional tone
- If you can answer the question, provide a complete and helpful response"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Check if AI couldn't answer the question
            cant_answer_phrases = [
                "I don't have enough information",
                "not available in the knowledge base",
                "I cannot find",
                "I don't know",
                "I'm not sure",
                "Let me connect you"
            ]
            
            can_answer = not any(phrase.lower() in ai_response.lower() for phrase in cant_answer_phrases)
            
            return {
                'success': True,
                'response': ai_response,
                'can_answer': can_answer
            }
            
        except Exception as e:
            self.logger.error(f"Error processing with AI: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_admin_notification(self, contact_request, admin_email):
        """Send email notification to administrator"""
        if not self.mail:
            return {
                'success': False,
                'error': 'Mail service not configured'
            }
        
        try:
            subject = f"New Support Request from {contact_request['name']}"
            
            body = f"""
A new support request has been submitted through the AI support agent.

Contact Details:
- Name: {contact_request['name']}
- Email: {contact_request['email']}
- Timestamp: {contact_request['timestamp']}

Question:
{contact_request['question']}

Please respond to this inquiry at your earliest convenience.

---
AI Support Agent
"""
            
            msg = Message(
                subject=subject,
                recipients=[admin_email],
                body=body
            )
            
            self.mail.send(msg)
            
            return {
                'success': True,
                'message': 'Admin notification sent successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Error sending admin notification: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def clean_text(self, text, max_length=5000):
        """Clean and truncate text for AI processing"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    def extract_relevant_content(self, content, question, max_length=3000):
        """Extract relevant content based on the question"""
        if not content or not question:
            return content
        
        # Simple keyword-based extraction
        question_words = set(question.lower().split())
        content_sentences = content.split('.')
        
        scored_sentences = []
        for sentence in content_sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
                
            sentence_words = set(sentence.lower().split())
            score = len(question_words.intersection(sentence_words))
            scored_sentences.append((score, sentence))
        
        # Sort by relevance score and take top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        relevant_content = ""
        for score, sentence in scored_sentences:
            if len(relevant_content) + len(sentence) > max_length:
                break
            relevant_content += sentence + ". "
        
        return relevant_content.strip() if relevant_content else content[:max_length]

