/**
 * ============================================
 * GESTION DES EMAILS - RELANCES AUTOMATIQUES
 * VERSION MICROSOFT GRAPH API
 * ============================================
 */

/**
 * Affiche le formulaire de reponse lorsqu'un email est selectionne
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
        // Cache le formulaire si aucun email n'est selectionne
        form.style.display = 'none';
    }
}

/**
 * Auto-genere un message personnalise base sur les donnees de la BD
 * VERSION MICROSOFT GRAPH : Envoie to_email au backend
 * Appelle l'API /api/generate-message/ avec email_id ET to_email
 */
function autoGenerate() {
    const select = document.getElementById('email-select');
    const email_id = select.value;
    const textarea = document.getElementById('reply-message');
    const status = document.getElementById('reply-status');
    const autoBtn = document.querySelector('.auto-btn');

    if (!email_id) {
        alert('Veuillez d\'abord selectionner un email');
        return;
    }

    // CHANGEMENT MICROSOFT : Recuperer to_email depuis l'option selectionnee
    const selectedOption = select.options[select.selectedIndex];
    const to_email = selectedOption.getAttribute('data-to');

    if (!to_email) {
        alert('Erreur : adresse email du destinataire manquante');
        console.error('to_email manquant pour email_id:', email_id);
        return;
    }

    console.log('Auto-generation pour:', email_id, 'destinataire:', to_email);

    // Desactive le textarea et le bouton pendant le chargement
    textarea.value = 'Generation en cours...';
    textarea.disabled = true;
    autoBtn.disabled = true;
    autoBtn.textContent = '⏳ Generation...';

    // Recupere le token CSRF
    const csrftoken = getCookie('csrftoken');

    // Appel API pour generer le message
    // CHANGEMENT MICROSOFT : Ajout de to_email dans le body
    fetch('/api/generate-message/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            email_id: email_id,
            to_email: to_email  // NOUVEAU : Obligatoire pour Microsoft Graph
        })
    })
    .then(response => response.json())
    .then(data => {
        // Reactive le textarea et le bouton
        textarea.disabled = false;
        autoBtn.disabled = false;
        autoBtn.textContent = '🤖 Auto-generer le message';

        if (data.success) {
            // Remplit le textarea avec le message genere
            textarea.value = data.message;

            // Affiche un message de succes
            status.style.display = 'block';
            status.className = 'success';
            status.textContent = '✅ Message genere automatiquement';

            // Cache le message apres 3 secondes
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
        // Gestion des erreurs reseau
        textarea.disabled = false;
        autoBtn.disabled = false;
        autoBtn.textContent = '🤖 Auto-generer le message';
        textarea.value = '';

        status.style.display = 'block';
        status.className = 'error';
        status.textContent = '❌ Erreur reseau: ' + error;

        console.error('Erreur auto-generation:', error);
    });
}

/**
 * Envoie la relance a l'email selectionne
 */
function sendReply() {
    const select = document.getElementById('email-select');
    const message = document.getElementById('reply-message').value.trim();
    const status = document.getElementById('reply-status');
    const btn = document.querySelector('.send-btn');

    if (!message) {
        alert('Veuillez ecrire un message');
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

    // Desactive le bouton pendant l'envoi
    btn.disabled = true;
    btn.textContent = 'Envoi en cours...';

    // Recupere le token CSRF
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

            // Recharge la page apres 2 secondes
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
        status.textContent = '❌ Erreur reseau: ' + error;
        btn.disabled = false;
        btn.textContent = 'Envoyer 📨';

        console.error('Erreur envoi email:', error);
    });
}

/**
 * Recupere un cookie par son nom (necessaire pour le token CSRF)
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