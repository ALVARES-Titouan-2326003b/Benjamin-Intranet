/**
 * ============================================
 * GESTION DES EMAILS - RELANCES AUTOMATIQUES
 * ============================================
 */

/**
 * Affiche le formulaire de réponse lorsqu'un email est sélectionné
 */
function showReplyForm() {
    const select = document.getElementById('email-select');
    const form = document.getElementById('reply-form');
    const status = document.getElementById('reply-status');

    if (select.value) {
        const option = select.options[select.selectedIndex];
        const to = option.getAttribute('data-to');
        const subject = option.getAttribute('data-subject');

        // Remplit les informations du destinataire
        document.getElementById('reply-to').textContent = to;
        document.getElementById('reply-subject').textContent = 'Re: ' + subject;
        document.getElementById('reply-message').value = '';

        // Affiche le formulaire
        form.style.display = 'block';
        status.style.display = 'none';
    } else {
        // Cache le formulaire si aucun email n'est sélectionné
        form.style.display = 'none';
    }
}

/**
 * Auto-génère un message personnalisé basé sur les données de la BD
 * Appelle l'API /api/generate-message/ avec l'email_id
 */
function autoGenerate() {
    const select = document.getElementById('email-select');
    const email_id = select.value;
    const textarea = document.getElementById('reply-message');
    const status = document.getElementById('reply-status');
    const autoBtn = document.querySelector('.auto-btn');

    if (!email_id) {
        alert('Veuillez d\'abord sélectionner un email');
        return;
    }

    // Désactive le textarea et le bouton pendant le chargement
    textarea.value = 'Génération en cours...';
    textarea.disabled = true;
    autoBtn.disabled = true;
    autoBtn.textContent = '⏳ Génération...';

    // Récupère le token CSRF
    const csrftoken = getCookie('csrftoken');

    // Appel API pour générer le message
    fetch('/api/generate-message/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            email_id: email_id
        })
    })
    .then(response => response.json())
    .then(data => {
        // Réactive le textarea et le bouton
        textarea.disabled = false;
        autoBtn.disabled = false;
        autoBtn.textContent = '🤖 Auto-générer le message';

        if (data.success) {
            // Remplit le textarea avec le message généré
            textarea.value = data.message;

            // Affiche un message de succès
            status.style.display = 'block';
            status.className = 'success';
            status.textContent = '✅ Message généré automatiquement';

            // Cache le message après 3 secondes
            setTimeout(() => {
                status.style.display = 'none';
            }, 3000);
        } else {
            // Affiche l'erreur
            textarea.value = '';
            status.style.display = 'block';
            status.className = 'error';
            status.textContent = '❌ ' + data.message;
        }
    })
    .catch(error => {
        // Gestion des erreurs réseau
        textarea.disabled = false;
        autoBtn.disabled = false;
        autoBtn.textContent = '🤖 Auto-générer le message';
        textarea.value = '';

        status.style.display = 'block';
        status.className = 'error';
        status.textContent = '❌ Erreur réseau: ' + error;

        console.error('Erreur auto-génération:', error);
    });
}

/**
 * Envoie la relance à l'email sélectionné
 */
function sendReply() {
    const select = document.getElementById('email-select');
    const message = document.getElementById('reply-message').value.trim();
    const status = document.getElementById('reply-status');
    const btn = document.querySelector('.send-btn');

    if (!message) {
        alert('Veuillez écrire un message');
        return;
    }

    const selectedOption = select.options[select.selectedIndex];
    const to_email = selectedOption.getAttribute('data-to');
    const subject = selectedOption.getAttribute('data-subject');

    if (!to_email || !subject) {
        alert('Erreur : informations du destinataire manquantes');
        console.error('to_email:', to_email, 'subject:', subject);
        return;
    }

    console.log('Envoi email vers:', to_email, 'sujet:', subject);

    // Désactive le bouton pendant l'envoi
    btn.disabled = true;
    btn.textContent = 'Envoi en cours...';

    // Récupère le token CSRF
    const csrftoken = getCookie('csrftoken');

    fetch('/api/send-reply/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            email_id: select.value,
            message: message,
            to_email: to_email,
            subject: subject
        })
    })
    .then(response => response.json())
    .then(data => {
        status.style.display = 'block';

        if (data.success) {
            status.className = 'success';
            status.textContent = '✅ ' + data.message;

            // Recharge la page après 2 secondes
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

        console.error('Erreur envoi email:', error);
    });
}

/**
 * Récupère un cookie par son nom (nécessaire pour le token CSRF)
 * @param {string} name - Nom du cookie
 * @returns {string|null} - Valeur du cookie ou null
 */
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