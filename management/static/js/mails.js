function showReplyForm() {
    const select = document.getElementById('email-select');
    const form = document.getElementById('reply-form');
    const status = document.getElementById('reply-status');

    if (select.value) {
        const option = select.options[select.selectedIndex];
        const from = option.getAttribute('data-from');
        const subject = option.getAttribute('data-subject');

        document.getElementById('reply-to').textContent = from;
        document.getElementById('reply-subject').textContent = 'Re: ' + subject;
        document.getElementById('reply-message').value = '';

        form.style.display = 'block';
        status.style.display = 'none';
    } else {
        form.style.display = 'none';
    }
}

function sendReply() {
    const select = document.getElementById('email-select');
    const message = document.getElementById('reply-message').value.trim();
    const status = document.getElementById('reply-status');
    const btn = document.querySelector('.send-btn');

    if (!message) {
        alert('Veuillez écrire un message');
        return;
    }

    // Désactive le bouton pendant l'envoi
    btn.disabled = true;
    btn.textContent = 'Envoi en cours...';

    // Récupère le token CSRF
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

    fetch('/api/send-reply/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            email_id: select.value,
            message: message
        })
    })
    .then(response => response.json())
    .then(data => {
        status.style.display = 'block';

        if (data.success) {
            status.className = 'success';
            status.textContent = '✅ ' + data.message;

            // Réinitialise le formulaire après 2 secondes
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            status.className = 'error';
            status.textContent = '❌ ' + data.message;
            btn.disabled = false;
            btn.textContent = 'Envoyer 📨';
        }
    })
    .catch(error => {
        status.style.display = 'block';
        status.className = 'error';
        status.textContent = '❌ Erreur réseau: ' + error;
        btn.disabled = false;
        btn.textContent = 'Envoyer 📨';
    });
}

// Fonction pour récupérer le cookie CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}