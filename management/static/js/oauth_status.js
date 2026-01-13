/**
 * ============================================
 * GESTION DU STATUT OAUTH - SYNCHRONISATION GMAIL
 * ============================================
 *
 * Fichier : static/js/oauth_status.js
 *
 * Fonctions :
 * - loadOAuthStatus() : Charge et affiche le statut de synchronisation
 * - resyncMailbox() : Re-synchronise la boîte mail
 * - revokeOAuth() : Révoque l'accès OAuth
 */

// Charger le statut OAuth au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    loadOAuthStatus();
});

/**
 * Charge le statut OAuth depuis l'API et affiche le résultat
 */
function loadOAuthStatus() {
    fetch('/oauth/status/')  // ✅ CORRECTION : URL absolue depuis la racine
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('oauth-status-container');

            if (data.synchronized) {
                // Boîte mail synchronisée
                const tokenStatus = data.token_expired ?
                    '<span style="color: #f59e0b;">⚠️ Token expiré (sera renouvelé automatiquement)</span>' :
                    '<span style="color: #10b981;">✅ Token valide</span>';

                container.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 250px;">
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                                <i class="bi bi-check-circle-fill" style="color: #10b981; font-size: 1.2rem;"></i>
                                <strong style="color: var(--text-main);">Boîte mail synchronisée</strong>
                            </div>
                            <div style="color: var(--text-secondary); font-size: 0.9rem;">
                                <i class="bi bi-envelope"></i> ${data.email}
                            </div>
                            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.25rem;">
                                ${tokenStatus}
                            </div>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button onclick="resyncMailbox()" class="btn btn-secondary" style="white-space: nowrap;">
                                <i class="bi bi-arrow-repeat"></i> Re-synchroniser
                            </button>
                            <button onclick="revokeOAuth()" class="btn btn-danger" style="white-space: nowrap;">
                                <i class="bi bi-x-circle"></i> Révoquer
                            </button>
                        </div>
                    </div>
                `;
            } else {
                // Boîte mail non synchronisée
                container.innerHTML = `
                    <div style="text-align: center; padding: 1rem;">
                        <div style="margin-bottom: 1rem;">
                            <i class="bi bi-exclamation-triangle" style="font-size: 2rem; color: #f59e0b;"></i>
                        </div>
                        <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                            Vous devez synchroniser votre boîte mail Gmail pour envoyer et recevoir des emails.
                        </p>
                        <a href="/oauth/gmail/" class="btn btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">
                            <i class="bi bi-google"></i> Synchroniser avec Gmail
                        </a>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Erreur chargement statut OAuth:', error);
            const container = document.getElementById('oauth-status-container');
            container.innerHTML = `
                <div style="text-align: center; padding: 1rem; color: #dc2626;">
                    <i class="bi bi-exclamation-circle"></i> Erreur de chargement du statut
                </div>
            `;
        });
}

/**
 * Re-synchronise la boîte mail (redemarre le flux OAuth)
 */
function resyncMailbox() {
    if (confirm('Re-synchroniser votre boîte mail ? Vous allez être redirigé vers Google.')) {
        window.location.href = '/oauth/gmail/';  // ✅ CORRECTION : URL absolue
    }
}

/**
 * Révoque l'accès OAuth (supprime les tokens)
 */
function revokeOAuth() {
    if (confirm('Êtes-vous sûr de vouloir révoquer l\'accès à votre boîte mail ? Vous ne pourrez plus envoyer d\'emails.')) {
        const csrftoken = getCookie('csrftoken');

        fetch('/oauth/revoke/', {  // ✅ CORRECTION : URL absolue
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('✅ Accès révoqué avec succès');
                loadOAuthStatus(); // Recharger le statut
            } else {
                alert('❌ Erreur : ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erreur révocation:', error);
            alert('❌ Erreur lors de la révocation');
        });
    }
}

/**
 * Récupère un cookie par son nom (pour CSRF token)
 * Note : Cette fonction peut déjà exister dans mails.js
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