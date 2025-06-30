class AISupportWidget {
    constructor(config = {}) {
        this.config = {
            apiBaseUrl: '/api',
            knowledgeUrl: '',
            sessionId: this.generateSessionId(),
            autoOpen: false,
            position: 'bottom-right',
            theme: 'default',
            ...config,
            ...window.AISupportConfig
        };
        
        this.isOpen = false;
        this.isLoading = false;
        this.currentQuestion = '';
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.hideNotificationBadge();
        
        if (this.config.autoOpen) {
            setTimeout(() => this.openChat(), 1000);
        }
    }
    
    bindEvents() {
        // Chat toggle
        document.getElementById('chat-toggle').addEventListener('click', () => {
            this.toggleChat();
        });
        
        // Close chat
        document.getElementById('close-chat').addEventListener('click', () => {
            this.closeChat();
        });
        
        // Chat form submission
        document.getElementById('chat-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Contact form events
        document.getElementById('close-contact-modal').addEventListener('click', () => {
            this.closeContactModal();
        });
        
        document.getElementById('cancel-contact').addEventListener('click', () => {
            this.closeContactModal();
        });
        
        document.getElementById('contact-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitContactForm();
        });
        
        // Success modal events
        document.getElementById('close-success-modal').addEventListener('click', () => {
            this.closeSuccessModal();
        });
        
        // Input events
        const messageInput = document.getElementById('message-input');
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Click outside to close modals
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('contact-modal')) {
                this.closeContactModal();
            }
            if (e.target.classList.contains('success-modal')) {
                this.closeSuccessModal();
            }
        });
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }
    
    openChat() {
        const chatWindow = document.getElementById('chat-window');
        chatWindow.style.display = 'flex';
        setTimeout(() => {
            chatWindow.classList.add('open');
        }, 10);
        this.isOpen = true;
        this.hideNotificationBadge();
        
        // Focus on input
        setTimeout(() => {
            document.getElementById('message-input').focus();
        }, 300);
    }
    
    closeChat() {
        const chatWindow = document.getElementById('chat-window');
        chatWindow.classList.remove('open');
        setTimeout(() => {
            chatWindow.style.display = 'none';
        }, 300);
        this.isOpen = false;
    }
    
    showNotificationBadge() {
        document.getElementById('notification-badge').style.display = 'flex';
    }
    
    hideNotificationBadge() {
        document.getElementById('notification-badge').style.display = 'none';
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message || this.isLoading) return;
        
        if (!this.config.knowledgeUrl) {
            this.showError('Knowledge URL not configured. Please contact the administrator.');
            return;
        }
        
        // Clear input and add user message
        messageInput.value = '';
        this.addMessage(message, 'user');
        this.currentQuestion = message;
        
        // Show typing indicator
        this.showTypingIndicator();
        this.setLoading(true);
        
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.config.sessionId,
                    knowledge_url: this.config.knowledgeUrl
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to get response');
            }
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            if (data.can_answer) {
                // AI could answer the question
                this.addMessage(data.response, 'bot');
            } else {
                // AI couldn't answer, show contact form
                this.addMessage(data.response || data.message, 'bot');
                setTimeout(() => {
                    this.showContactModal();
                }, 1000);
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('Sorry, I encountered an error. Please try again.');
            console.error('Chat error:', error);
        } finally {
            this.setLoading(false);
        }
    }
    
    addMessage(content, type) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = type === 'bot' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textP = document.createElement('p');
        textP.textContent = content;
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = this.formatTime(new Date());
        
        contentDiv.appendChild(textP);
        contentDiv.appendChild(timeSpan);
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    showTypingIndicator() {
        document.getElementById('typing-indicator').style.display = 'flex';
    }
    
    hideTypingIndicator() {
        document.getElementById('typing-indicator').style.display = 'none';
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        const sendBtn = document.getElementById('send-btn');
        const messageInput = document.getElementById('message-input');
        
        sendBtn.disabled = loading;
        messageInput.disabled = loading;
        
        if (loading) {
            sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        } else {
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    }
    
    showContactModal() {
        const modal = document.getElementById('contact-modal');
        const questionTextarea = document.getElementById('contact-question');
        
        // Pre-fill the question
        questionTextarea.value = this.currentQuestion;
        
        modal.style.display = 'flex';
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
        
        // Focus on name input
        setTimeout(() => {
            document.getElementById('contact-name').focus();
        }, 300);
    }
    
    closeContactModal() {
        const modal = document.getElementById('contact-modal');
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }
    
    async submitContactForm() {
        const name = document.getElementById('contact-name').value.trim();
        const email = document.getElementById('contact-email').value.trim();
        const question = document.getElementById('contact-question').value.trim();
        
        if (!name || !email || !question) {
            this.showError('Please fill in all required fields.');
            return;
        }
        
        if (!this.validateEmail(email)) {
            this.showError('Please enter a valid email address.');
            return;
        }
        
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/contact`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.config.sessionId,
                    name: name,
                    email: email,
                    question: question
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to submit contact form');
            }
            
            // Close contact modal and show success
            this.closeContactModal();
            this.showSuccessModal();
            
            // Clear form
            document.getElementById('contact-form').reset();
            
        } catch (error) {
            this.showError('Failed to submit your request. Please try again.');
            console.error('Contact form error:', error);
        }
    }
    
    showSuccessModal() {
        const modal = document.getElementById('success-modal');
        modal.style.display = 'flex';
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
    }
    
    closeSuccessModal() {
        const modal = document.getElementById('success-modal');
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }
    
    showError(message) {
        // Remove existing error messages
        const existingErrors = document.querySelectorAll('.error-message');
        existingErrors.forEach(error => error.remove());
        
        // Create error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        // Add to chat messages
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.appendChild(errorDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }
    
    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    formatTime(date) {
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    }
    
    // Public API methods
    setKnowledgeUrl(url) {
        this.config.knowledgeUrl = url;
    }
    
    open() {
        this.openChat();
    }
    
    close() {
        this.closeChat();
    }
    
    sendWelcomeMessage(message) {
        this.addMessage(message, 'bot');
    }
}

// Initialize widget when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.aiSupportWidget = new AISupportWidget();
});

// Export for external use
window.AISupportWidget = AISupportWidget;

