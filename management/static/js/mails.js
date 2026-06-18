let conversationsData = {};

document.addEventListener('DOMContentLoaded', () => {
    const datalist = document.getElementById('email-datalist');
    if (datalist) {
        datalist.querySelectorAll('option').forEach(option => {
            conversationsData[option.value] = {
                id: option.dataset.id,
                to: option.dataset.to,
                subject: option.dataset.subject,
            };
        });
    }

    const input = document.getElementById('email-select');
    input?.addEventListener('input', showReplyForm);
    input?.addEventListener('change', showReplyForm);

    document.querySelectorAll('.gmail-status-select').forEach(select => {
        select.dataset.previous = select.value;
        select.addEventListener('change', updateConversationStatus);
    });
    document.querySelectorAll('.gmail-note-btn').forEach(button => {
        button.addEventListener('click', addConversationNote);
    });

    document
        .getElementById('sync-gmail-journal-btn')
        ?.addEventListener('click', syncGmailJournal);
});

function selectedConversation() {
    const value = document.getElementById('email-select')?.value.trim();
    return value ? conversationsData[value] : null;
}

function showReplyForm() {
    const input = document.getElementById('email-select');
    const form = document.getElementById('reply-form');
    const error = document.getElementById('email-error');
    const conversation = selectedConversation();

    if (!input?.value.trim()) {
        form.style.display = 'none';
        error.style.display = 'none';
        return;
    }
    if (!conversation) {
        form.style.display = 'none';
        error.style.display = 'block';
        return;
    }

    document.getElementById('reply-to').textContent = conversation.to;
    document.getElementById('reply-subject').textContent =
        conversation.subject.toLowerCase().startsWith('re:')
            ? conversation.subject
            : `Re: ${conversation.subject}`;
    document.getElementById('reply-message').value = '';
    document.getElementById('reply-status').style.display = 'none';
    form.style.display = 'block';
    error.style.display = 'none';
}

async function autoGenerate() {
    const conversation = selectedConversation();
    if (!conversation) {
        alert('Veuillez sélectionner une conversation valide.');
        return;
    }

    const textarea = document.getElementById('reply-message');
    const status = document.getElementById('reply-status');
    const button = document.querySelector('.auto-btn');
    textarea.value = 'Génération en cours...';
    textarea.disabled = true;
    button.disabled = true;

    try {
        const response = await fetch('/api/generate-message/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ conversation_id: conversation.id }),
        });
        const data = await response.json();
        textarea.value = data.success ? data.message : '';
        showStatus(status, data.success, data.success ? 'Message généré.' : data.message);
    } catch (error) {
        textarea.value = '';
        showStatus(status, false, `Erreur réseau : ${error}`);
    } finally {
        textarea.disabled = false;
        button.disabled = false;
    }
}

async function sendReply() {
    const conversation = selectedConversation();
    const message = document.getElementById('reply-message').value.trim();
    const status = document.getElementById('reply-status');
    const button = document.querySelector('.send-btn');
    if (!conversation || !message) {
        alert('Sélectionnez une conversation et saisissez un message.');
        return;
    }

    button.disabled = true;
    try {
        const response = await fetch('/api/send-reply/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                conversation_id: conversation.id,
                message: message,
            }),
        });
        const data = await response.json();
        showStatus(status, data.success, data.message);
        if (data.success) setTimeout(() => window.location.reload(), 800);
    } catch (error) {
        showStatus(status, false, `Erreur réseau : ${error}`);
    } finally {
        button.disabled = false;
    }
}

async function updateConversationStatus(event) {
    const select = event.currentTarget;
    const previous = select.dataset.previous || '';
    const response = await fetch(`/api/gmail-journal/${select.dataset.conversationId}/status/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ status: select.value }),
    });
    const data = await response.json();
    if (!data.success) {
        if (previous) select.value = previous;
        alert(data.message || 'Le statut n’a pas pu être modifié.');
        return;
    }
    select.dataset.previous = select.value;
}

async function addConversationNote(event) {
    const button = event.currentTarget;
    const id = button.dataset.conversationId;
    const input = document.querySelector(`.gmail-note-input[data-conversation-id="${id}"]`);
    const note = input.value.trim();
    if (!note) return;

    button.disabled = true;
    try {
        const response = await fetch(`/api/gmail-journal/${id}/notes/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ note }),
        });
        const data = await response.json();
        if (!data.success) {
            alert(data.message || 'La note n’a pas pu être ajoutée.');
            return;
        }
        const events = button.closest('.email-item').querySelector('.gmail-events');
        events.insertAdjacentHTML(
            'afterbegin',
            `<div>${escapeHtml(data.created_at)} · Note — ${escapeHtml(data.note)}</div>`,
        );
        input.value = '';
    } finally {
        button.disabled = false;
    }
}

async function syncGmailJournal(event) {
    const button = event.currentTarget;
    const status = document.getElementById('gmail-sync-status');
    const previousLabel = button.innerHTML;

    button.disabled = true;
    button.innerHTML = '<i class="bi bi-arrow-repeat"></i> Synchronisation...';
    if (status) {
        status.style.color = 'var(--text-secondary)';
        status.textContent = 'Synchronisation Gmail en cours...';
    }

    try {
        const response = await fetch('/api/gmail-journal/sync/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.message || 'Synchronisation impossible.');
        }
        if (status) {
            status.style.color = '#16a34a';
            status.textContent = `${data.synced || 0} conversation(s) synchronisée(s), ${data.replied || 0} réponse(s) détectée(s).`;
        }
        setTimeout(() => window.location.reload(), 700);
    } catch (error) {
        if (status) {
            status.style.color = '#dc2626';
            status.textContent = error.message || 'Synchronisation impossible.';
        }
        button.disabled = false;
        button.innerHTML = previousLabel;
    }
}

function showStatus(element, success, message) {
    element.style.display = 'block';
    element.className = success ? 'success' : 'error';
    element.textContent = `${success ? 'OK' : 'Erreur'} : ${message || ''}`;
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value || '';
    return div.innerHTML;
}

function getCookie(name) {
    const prefix = `${name}=`;
    for (const item of (document.cookie || '').split(';')) {
        const cookie = item.trim();
        if (cookie.startsWith(prefix)) return decodeURIComponent(cookie.slice(prefix.length));
    }
    return '';
}
