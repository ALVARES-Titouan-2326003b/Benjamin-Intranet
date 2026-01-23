/**
 * ============================================
 * GESTION DES EMAILS - RELANCES AUTOMATIQUES
 * ============================================
 */

// ============================================
// CHARGEMENT DES DONNÉES
// ============================================

let emailsData = {};

document.addEventListener('DOMContentLoaded', function() {
    // Charger les données emails depuis le script JSON
    const emailsScript = document.getElementById('emails-data');
    if (emailsScript) {
        try {
            emailsData = JSON.parse(emailsScript.textContent);
            console.log('📧 Emails chargés:', Object.keys(emailsData).length);
        } catch (e) {
            console.error('Erreur chargement emails:', e);
        }
    }

    // Attacher l'événement sur le champ email-select
    const emailInput = document.getElementById('email-select');
    if (emailInput) {
        emailInput.addEventListener('input', showReplyForm);
        emailInput.addEventListener('change', showReplyForm);
    }
});

// ============================================
// AFFICHAGE DU FORMULAIRE
// ============================================

/**
 * Affiche le formulaire de réponse si l'email sélectionné est valide
 */
function showReplyForm() {
    const input = document.getElementById('email-select');
    const form = document.getElementById('reply-form');
    const status = document.getElementById('reply-status');
    const errorMsg = document.getElementById('email-error');

    const selectedSubject = input.value.trim();

    // Si le champ est vide
    if (!selectedSubject) {
        form.style.display = 'none';
        errorMsg.style.display = 'none';
        return;
    }

    // Vérifier si l'email existe dans les données
    if (emailsData[selectedSubject]) {
        const email = emailsData[selectedSubject];

        // Extraire le sujet sans la date (tout avant la dernière parenthèse)
        const subjectOnly = email.subject;

        // Remplir les informations du destinataire
        document.getElementById('reply-to').textContent = email.to;
        document.getElementById('reply-subject').textContent = 'Re: ' + subjectOnly;
        document.getElementById('reply-message').value = '';

        // Afficher le formulaire et cacher l'erreur
        form.style.display = 'block';
        errorMsg.style.display = 'none';
        status.style.display = 'none';
    } else {
        // Email invalide : cacher le formulaire et afficher l'erreur
        form.style.display = 'none';
        errorMsg.style.display = 'block';
    }
}

// ============================================
// AUTO-GÉNÉRATION DU MESSAGE
// ============================================

/**
 * Auto-génère un message personnalisé basé sur les données de la BD
 * Appelle l'API /api/generate-message/ avec l'email_id
 */
function autoGenerate() {
    const input = document.getElementById('email-select');
    const selectedSubject = input.value.trim();
    const textarea = document.getElementById('reply-message');
    const status = document.getElementById('reply-status');
    const autoBtn = document.querySelector('.auto-btn');

    // Vérifier que l'email existe
    if (!emailsData[selectedSubject]) {
        alert('Veuillez d\'abord sélectionner un email valide');
        return;
    }

    const email_id = emailsData[selectedSubject].id;

    // Désactiver pendant le chargement
    textarea.value = 'Génération en cours...';
    textarea.disabled = true;
    autoBtn.disabled = true;
    autoBtn.textContent = '⏳ Génération...';

    const csrftoken = getCookie('csrftoken');

    // Appel API
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
        textarea.disabled = false;
        autoBtn.disabled = false;
        autoBtn.textContent = '🤖 Auto-générer le message';

        if (data.success) {
            textarea.value = data.message;

            status.style.display = 'block';
            status.className = 'success';
            status.textContent = '✅ Message généré automatiquement';

            setTimeout(() => {
                status.style.display = 'none';
            }, 3000);
        } else {
            textarea.value = '';
            status.style.display = 'block';
            status.className = 'error';
            status.textContent = '❌ ' + data.message;
        }
    })
    .catch(error => {
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

// ============================================
// ENVOI DE LA RÉPONSE
// ============================================

/**
 * Envoie la relance à l'email sélectionné
 */
function sendReply() {
    const input = document.getElementById('email-select');
    const selectedSubject = input.value.trim();
    const message = document.getElementById('reply-message').value.trim();
    const status = document.getElementById('reply-status');
    const btn = document.querySelector('.send-btn');

    // Validation 1 : Email valide ?
    if (!emailsData[selectedSubject]) {
        alert('⚠️ Veuillez sélectionner un email valide dans la liste');
        return;
    }

    // Validation 2 : Message non vide ?
    if (!message) {
        alert('⚠️ Veuillez écrire un message');
        return;
    }

    const email = emailsData[selectedSubject];
    const to_email = email.to;
    const subject = email.subject;
    const email_id = email.id;

    console.log('Envoi email vers:', to_email, 'sujet:', subject);

    // Désactiver le bouton pendant l'envoi
    btn.disabled = true;
    btn.textContent = 'Envoi en cours...';

    const csrftoken = getCookie('csrftoken');

    fetch('/api/send-reply/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            email_id: email_id,
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

            // Recharger la page après 2 secondes
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

// ============================================
// UTILITAIRES
// ============================================

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