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

function getCurrentTime() {
    return new Date().toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('chatbot-messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addMessage(text, sender, withCopy = false) {
    const messagesContainer = document.getElementById('chatbot-messages');

    const block = document.createElement('div');
    block.className = `message-block ${sender === 'user' ? 'user-block' : 'bot-block'}`;

    const messageDiv = document.createElement('div');
    messageDiv.className = sender === 'user' ? 'user-message' : 'bot-message';
    messageDiv.textContent = text;

    block.appendChild(messageDiv);

    if (sender === 'bot' && withCopy) {
        const actions = document.createElement('div');
        actions.className = 'message-actions';

        const copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = 'Copier';

        copyBtn.addEventListener('click', async function () {
            try {
                await navigator.clipboard.writeText(text);
                copyBtn.textContent = 'Copié';
                setTimeout(() => {
                    copyBtn.textContent = 'Copier';
                }, 1000);
            } catch (e) {
                copyBtn.textContent = 'Erreur';
                setTimeout(() => {
                    copyBtn.textContent = 'Copier';
                }, 1000);
            }
        });

        actions.appendChild(copyBtn);
        block.appendChild(actions);
    }

    const footer = document.createElement('div');
    footer.className = 'message-footer';
    footer.innerHTML = `
        <span>${sender === 'user' ? 'Vous' : 'Assistant'}</span>
        <span>${getCurrentTime()}</span>
    `;

    block.appendChild(footer);
    messagesContainer.appendChild(block);
    scrollToBottom();
}

function showTypingIndicator() {
    const messagesContainer = document.getElementById('chatbot-messages');

    const block = document.createElement('div');
    block.id = 'typing-indicator';
    block.className = 'message-block bot-block';

    block.innerHTML = `
        <div class="bot-message">Assistant écrit...</div>
        <div class="message-footer">
            <span>Assistant</span>
            <span>${getCurrentTime()}</span>
        </div>
    `;

    messagesContainer.appendChild(block);
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const message = input.value.trim();

    if (!message) return;

    addMessage(message, 'user');
    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;

    showTypingIndicator();

    try {
        const response = await fetch('/chatbot/query/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();
        hideTypingIndicator();

        if (data.success) {
            addMessage(data.response, 'bot', true);
        } else {
            addMessage(data.response || "Désolé, une erreur s'est produite.", 'bot', false);
        }
    } catch (error) {
        hideTypingIndicator();
        addMessage("Erreur réseau. Impossible de contacter le serveur.", 'bot', false);
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-init-time]').forEach(el => {
        el.textContent = getCurrentTime();
    });

    const input = document.getElementById('message-input');
    if (input) {
        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
    }
});