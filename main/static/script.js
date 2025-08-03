// A simple class to manage the chatbot's front-end logic.
class ChatManager {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.microphoneButton = document.getElementById('microphoneButton');
        this.optionsButton = document.getElementById('optionsButton');
        this.dropdownMenu = document.getElementById('dropdownMenu');
        this.viewMenuButton = document.getElementById('viewMenuButton');
        this.cancelOrderButton = document.getElementById('cancelOrderButton');
        this.restartOrderButton = document.getElementById('restartOrderButton');
        
        this.conversationHistory = [];
        this.sessionId = this.getOrCreateSessionId();
        this.isTyping = false;
        this.isSpeaking = false;
        this.isRecording = false;

        this.bindEvents();

        // Check for Speech Recognition API support
        window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (window.SpeechRecognition) {
            this.recognition = new window.SpeechRecognition();
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            this.recognition.onresult = (event) => this.handleRecognitionResult(event);
            this.recognition.onend = () => this.handleRecognitionEnd();
            this.recognition.onerror = (event) => console.error("Speech Recognition Error:", event.error);
        } else {
            this.microphoneButton.style.display = 'none'; // Hide button if not supported
        }
    }

    // Get or create a session ID from local storage
    getOrCreateSessionId() {
        let sessionId = localStorage.getItem('pizzaBahnSessionId');
        if (!sessionId) {
            sessionId = 'session-' + Date.now();
            localStorage.setItem('pizzaBahnSessionId', sessionId);
        }
        return sessionId;
    }

    bindEvents() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        this.microphoneButton.addEventListener('click', () => this.toggleSpeechToText());
        this.optionsButton.addEventListener('click', () => this.toggleDropdown());
        this.viewMenuButton.addEventListener('click', () => this.viewMenu());
        this.cancelOrderButton.addEventListener('click', () => this.cancelOrder());
        this.restartOrderButton.addEventListener('click', () => this.restartOrder());
    }

    toggleDropdown() {
        this.dropdownMenu.classList.toggle('visible');
    }
    
    toggleSpeechToText() {
        if (this.isRecording) {
            this.recognition.stop();
        } else {
            this.recognition.start();
            this.microphoneButton.classList.add('recording');
            this.isRecording = true;
        }
    }
    
    handleRecognitionResult(event) {
        const transcript = event.results[0][0].transcript;
        this.messageInput.value = transcript;
        this.sendMessage();
    }
    
    handleRecognitionEnd() {
        this.isRecording = false;
        this.microphoneButton.classList.remove('recording');
    }

    addMenuToChat(menuData) {
        const menuDisplayDiv = document.createElement('div');
        menuDisplayDiv.className = 'message bot-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content menu-display';
        
        // Pizzas
        contentDiv.innerHTML += `<h4>🍕 Pizzas</h4>`;
        contentDiv.innerHTML += this.createMenuTableFromData(menuData.pizzas, 'pizza');

        // Extras
        contentDiv.innerHTML += `<h4>🍞 Extras</h4>`;
        contentDiv.innerHTML += this.createMenuTableFromData(menuData.extras, 'extra');

        // Drinks
        contentDiv.innerHTML += `<h4>🥤 Drinks</h4>`;
        contentDiv.innerHTML += this.createMenuTableFromData(menuData.drinks, 'drink');

        menuDisplayDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(menuDisplayDiv);
        this.scrollToBottom();
    }

    createMenuTableFromData(items, type) {
        let tableHtml = `<table class="menu-table"><thead><tr>`;
        tableHtml += `<th>ID</th><th>Name</th><th>Price (€)</th><th>Type</th>`;
        tableHtml += `</tr></thead><tbody>`;
        
        items.forEach(item => {
            tableHtml += `<tr>`;
            tableHtml += `<td>${this.escapeHtml(item.id)}</td>`;
            tableHtml += `<td>${this.escapeHtml(item.name)}</td>`;
            tableHtml += `<td>€${item.price.toFixed(2)}</td>`;
            tableHtml += `<td>${this.escapeHtml(item.type || item.size || '')}</td>`;
            tableHtml += `</tr>`;
        });
        
        tableHtml += `</tbody></table>`;
        return tableHtml;
    }
    
    async sendMessage(messageText = null) {
        let userMessage = messageText || this.messageInput.value.trim();
        if (!userMessage) return;

        this.addMessageToChat('user', userMessage);
        this.messageInput.value = '';
        this.showTypingIndicator();

        const payload = {
            message: userMessage,
            history: this.conversationHistory,
            session_id: this.sessionId
        };
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            this.hideTypingIndicator();
            
            if (data.type === 'text') {
                this.addMessageToChat('bot', data.response);
                this.conversationHistory.push({ role: 'user', content: userMessage });
                this.conversationHistory.push({ role: 'bot', content: data.response });
            } else if (data.menu_data) {
                this.addMenuToChat(data.menu_data);
                // We don't add the menu to the conversation history
            } else {
                console.error("Unknown response type:", data.type);
            }

        } catch (error) {
            this.hideTypingIndicator();
            console.error('Error fetching chat response:', error);
            this.addMessageToChat('bot', "Sorry, I couldn't connect to the server. Please try again later.");
        }
    }

    async viewMenu() {
        this.toggleDropdown();
        this.showTypingIndicator();

        try {
            const response = await fetch('/api/menu');
            const data = await response.json();
            this.hideTypingIndicator();

            if (data.menu_data) {
                this.addMenuToChat(data.menu_data);
            } else {
                this.addMessageToChat('bot', "Sorry, I couldn't retrieve the menu right now.");
            }
        } catch (error) {
            this.hideTypingIndicator();
            console.error('Error fetching menu:', error);
            this.addMessageToChat('bot', "Sorry, I couldn't retrieve the menu right now.");
        }
    }

    async cancelOrder() {
        this.toggleDropdown();
        await this.sendMessage("cancel order");
    }

    async restartOrder() {
        this.toggleDropdown();
        await this.sendMessage("restart order");
    }

    addMessageToChat(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = this.escapeHtml(text);
        
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    

    showTypingIndicator() {
        this.hideTypingIndicator(); // Ensure only one is visible
        const typingIndicatorDiv = document.createElement('div');
        typingIndicatorDiv.id = 'typingIndicator';
        typingIndicatorDiv.className = 'message bot-message';
        typingIndicatorDiv.innerHTML = `
                <div class="message-content">
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
        this.chatMessages.appendChild(typingIndicatorDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    clearConversation() {
        // Clear chat messages except welcome message
        const messages = this.chatMessages.querySelectorAll('.message');
        messages.forEach(message => message.remove());
        
        // Clear conversation history
        this.conversationHistory = [];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// Initialize the chat when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.chatManager = new ChatManager();
});
