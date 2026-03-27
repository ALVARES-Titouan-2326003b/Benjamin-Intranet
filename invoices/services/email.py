from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth.models import User

def get_internal_recipients(pole_name=None):
    """
    Récupère les emails des utilisateurs du groupe correspondant au pôle.
    
    Mapping:
    - Technique -> POLE_TECHNIQUE
    - Administratif -> POLE_ADMINISTRATIF
    - Comptabilite et Finance -> POLE_FINANCIER
    - (Defaut) -> POLE_FINANCIER
    """
    # Mapping Pôle (DB) -> Groupe (Django)
    # Les clés doivent correspondre aux valeurs de l'ENUM 'poles' en base
    # On utilise best_match ou un mapping approximatif si besoin, mais ici on fait simple
    
    mapping = {
        "Technique": "POLE_TECHNIQUE",
        "Administratif": "POLE_ADMINISTRATIF",
        "Comptabilite et Finance": "POLE_FINANCIER"
    }
    
    # Détermination du groupe cible
    target_group = mapping.get(pole_name, "POLE_FINANCIER") # Fallback sur Finance
    
    print(f"🔍 Pôle: '{pole_name}' -> Groupe Cible: '{target_group}'")

    # Récupérer les utilisateurs du groupe cible qui ont un email
    group_users = User.objects.filter(groups__name=target_group).exclude(email='')
    
    # Créer un set pour éviter les doublons
    emails = set()
    for u in group_users:
        emails.add(u.email)

    return list(emails)

def send_invoice_status_email(facture, old_status, new_status):
    """
    Envoie un email de notification lors du changement de statut d'une facture.
    Envoie par défaut aux utilisateurs du pôle financier.
    """
    # Envoi par défaut au pôle financier (qui gère les factures)
    recipients = get_internal_recipients("Comptabilite et Finance")
    if not recipients:
        print("⚠️ Aucun destinataire trouvé pour la notification de changement de statut de facture.")
        return

    sujet = f"Mise à jour facture {facture.id} : Statut changé"
    
    # Construction du nom du client (Entreprise)
    client_name = str(facture.client) if facture.client else "Client Inconnu"

    # Construction du lien
    from django.urls import reverse
    relative_link = reverse('invoices:detail', args=[facture.pk])
    full_link = f"{settings.SITE_URL}{relative_link}"

    corps = (
        f"Bonjour,\n\n"
        f"Le statut de la facture {facture.id} pour le client {client_name} "
        f"a changé.\n\n"
        f"Ancien statut : {old_status}\n"
        f"Nouveau statut : {new_status}\n\n"
        f"Voir la facture : {full_link}\n\n"
        f"Cordialement,\n"
        f"L'intranet Benjamin Immobilier"
    )

    try:
        email = EmailMessage(
            subject=sujet,
            body=corps,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        email.send()
        print(f"Email de changement de statut envoyé pour la facture {facture.id} à {recipients}")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de changement de statut : {e}")
