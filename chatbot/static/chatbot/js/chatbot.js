function toggleChat() {
    const container = document.getElementById('chatbot-container');
    const toggle = document.getElementById('chatbot-toggle');
    
    if (container.classList.contains('hidden')) {
        container.classList.remove('hidden');
        toggle.style.display = 'none';
    } else {
        container.classList.add('hidden');
        toggle.style.display = 'flex';
    }
}

function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Afficher le message utilisateur
    addMessage(message, 'user');
    input.value = '';
    
    // Indicateur de frappe
    showTypingIndicator();
    
    // Envoyer la requête au serveur
    fetch('/chatbot/query/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message
        })
    })
    .then(response => response.json())
    .then(data => {
        hideTypingIndicator();
        if (data.success) {
            addMessage(data.response, 'bot');
        } else {
            addMessage('Désolé, une erreur s\'est produite. Veuillez réessayer.', 'bot');
        }
    })
}

function addMessage(text, sender) {
    const messagesContainer = document.getElementById('chatbot-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = sender === 'user' ? 'user-message' : 'bot-message';
    messageDiv.textContent = text;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'typing-indicator';
    indicator.className = 'bot-message';
    indicator.innerHTML = 'Assistant écrit...';
    
    document.getElementById('chatbot-messages').appendChild(indicator);
    document.getElementById('chatbot-messages').scrollTop = 
        document.getElementById('chatbot-messages').scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// Envoyer message avec Entrée
document.addEventListener('DOMContentLoaded', function() {
    const input = document.getElementById('message-input');
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
    }
});
