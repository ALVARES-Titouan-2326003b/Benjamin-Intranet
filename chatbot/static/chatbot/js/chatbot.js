// Chargé depuis cdnjs, pas de dépendance locale.
(function loadMarked() {
    if (window.marked) return;
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/marked/9.1.6/marked.min.js';
    s.onload = () => {
        marked.setOptions({ breaks: true, gfm: true });
    };
    document.head.appendChild(s);
})();

// ── Icônes par type de route ──────────────────────────────────────────────────
const ROUTE_BADGE = {
    invoice:        { label: '💰 Facture',           color: '#1d4ed8', bg: '#dbeafe' },
    document:       { label: '📄 Document interne',  color: '#166534', bg: '#dcfce7' },
    legal:          { label: '⚖️ Juridique',          color: '#92400e', bg: '#fef3c7' },
    legal_fallback: { label: '⚖️ Juridique',          color: '#92400e', bg: '#fef3c7' },
};

// ── Toggle chatbot ────────────────────────────────────────────────────────────
function toggleChat() {
    const container = document.getElementById('chatbot-container');
    const toggle    = document.getElementById('chatbot-toggle');
    if (container.classList.contains('hidden')) {
        container.classList.remove('hidden');
        toggle.style.display = 'none';
    } else {
        container.classList.add('hidden');
        toggle.style.display = 'flex';
    }
}

// ── Envoi du message ──────────────────────────────────────────────────────────
function sendMessage() {
    const input   = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    input.value = '';
    showTypingIndicator();

    fetch('/chatbot/query/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
    })
    .then(r => r.json())
    .then(data => {
        hideTypingIndicator();
        if (data.success) {
            addMessage(data.response, 'bot', data.query_type);
        } else {
            addMessage('Désolé, une erreur s\'est produite. Veuillez réessayer.', 'bot');
        }
    })
    .catch(() => {
        hideTypingIndicator();
        addMessage('Erreur réseau. Veuillez réessayer.', 'bot');
    });
}

// ── Ajout d'un message ────────────────────────────────────────────────────────
function addMessage(text, sender, routeType) {
    const container = document.getElementById('chatbot-messages');
    const wrap      = document.createElement('div');
    wrap.className  = sender === 'user' ? 'user-message' : 'bot-message';

    if (sender === 'bot') {
        // Badge de route (optionnel)
        if (routeType && ROUTE_BADGE[routeType]) {
            const badge = ROUTE_BADGE[routeType];
            const badgeEl = document.createElement('div');
            badgeEl.style.cssText = (
                `display:inline-block; font-size:0.75rem; padding:2px 8px;
                 border-radius:10px; margin-bottom:6px; font-weight:500;
                 background:${badge.bg}; color:${badge.color};`
            );
            badgeEl.textContent = badge.label;
            wrap.appendChild(badgeEl);
        }

        // Rendu Markdown si disponible, sinon texte brut avec retours à la ligne
        const content = document.createElement('div');
        if (window.marked) {
            content.innerHTML = marked.parse(text);
        } else {
            content.style.whiteSpace = 'pre-wrap';
            content.textContent = text;
        }
        wrap.appendChild(content);
    } else {
        wrap.textContent = text;
    }

    container.appendChild(wrap);
    container.scrollTop = container.scrollHeight;
}

// ── Indicateur de frappe ──────────────────────────────────────────────────────
function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.id        = 'typing-indicator';
    indicator.className = 'bot-message';
    indicator.innerHTML = '<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
    document.getElementById('chatbot-messages').appendChild(indicator);
    document.getElementById('chatbot-messages').scrollTop =
        document.getElementById('chatbot-messages').scrollHeight;
}

function hideTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

// ── Touche Entrée ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('message-input');
    if (input) {
        input.addEventListener('keypress', e => {
            if (e.key === 'Enter') { e.preventDefault(); sendMessage(); }
        });
    }
});