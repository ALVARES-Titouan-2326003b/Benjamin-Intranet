document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('oauth-status-container')) {
        loadOAuthStatus();
    }
});

function loadOAuthStatus() {
    fetch('/oauth/status/')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('oauth-status-container');
            if (!container) return;   // sécurité supplémentaire

            if (data.synchronized) {
                const tokenStatus = data.token_expired
                    ? '<span style="color:#f59e0b;"> Token expiré (sera renouvelé automatiquement)</span>'
                    : '<span style="color:#10b981;"> Token valide</span>';

                container.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap;">
                        <div style="flex:1; min-width:250px;">
                            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                                <i class="bi bi-check-circle-fill" style="color:#10b981; font-size:1.2rem;"></i>
                                <strong style="color:var(--text-main);">Boîte mail synchronisée</strong>
                            </div>
                            <div style="color:var(--text-secondary); font-size:0.9rem;">
                                <i class="bi bi-envelope"></i> ${data.email}
                            </div>
                            <div style="color:var(--text-secondary); font-size:0.85rem; margin-top:0.25rem;">
                                ${tokenStatus}
                            </div>
                        </div>
                        <div style="display:flex; gap:0.5rem;">
                            <button onclick="resyncMailbox()" class="btn btn-secondary" style="white-space:nowrap;">
                                <i class="bi bi-arrow-repeat"></i> Re-synchroniser
                            </button>
                            <button onclick="revokeOAuth()" class="btn btn-danger" style="white-space:nowrap;">
                                <i class="bi bi-x-circle"></i> Révoquer
                            </button>
                        </div>
                    </div>`;
            } else {
                container.innerHTML = `
                    <div style="text-align:center; padding:1rem;">
                        <div style="margin-bottom:1rem;">
                            <i class="bi bi-exclamation-triangle" style="font-size:2rem; color:#f59e0b;"></i>
                        </div>
                        <p style="color:var(--text-secondary); margin-bottom:1rem;">
                            Vous devez synchroniser votre boîte mail Microsoft pour envoyer et recevoir des emails.
                        </p>
                        <a href="/oauth/microsoft/" class="btn btn-primary"
                           style="display:inline-flex; align-items:center; gap:0.5rem;">
                            <i class="bi bi-microsoft"></i> Synchroniser avec Outlook
                        </a>
                    </div>`;
            }
        })
        .catch(error => {
            console.error('Erreur chargement statut OAuth:', error);
            const container = document.getElementById('oauth-status-container');
            if (!container) return;
            container.innerHTML = `
                <div style="text-align:center; padding:1rem; color:#dc2626;">
                    <i class="bi bi-exclamation-circle"></i> Erreur de chargement du statut
                </div>`;
        });
}

function resyncMailbox() {
    if (confirm('Re-synchroniser votre boîte mail ? Vous allez être redirigé vers Microsoft.')) {
        window.location.href = '/oauth/microsoft/';
    }
}

function revokeOAuth() {
    if (!confirm('Êtes-vous sûr de vouloir révoquer l\'accès à votre boîte mail ?')) return;

    fetch('/oauth/revoke/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('Accès révoqué avec succès');
            loadOAuthStatus();
        } else {
            alert('Erreur : ' + data.message);
        }
    })
    .catch(() => alert('Erreur lors de la révocation'));
}

function getCookie(name) {
    let value = null;
    if (document.cookie) {
        document.cookie.split(';').forEach(c => {
            c = c.trim();
            if (c.startsWith(name + '='))
                value = decodeURIComponent(c.slice(name.length + 1));
        });
    }
    return value;
}