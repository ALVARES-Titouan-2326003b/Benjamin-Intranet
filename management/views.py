"""
Vues pour la partie administrative - Gestion des emails et relances
VERSION OAUTH2 : Passe request.user aux fonctions email_manager
"""
from datetime import timezone

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .email_manager import fetch_new_emails, get_sent_emails, get_email_summary, send_email_reply
from .modelsadm import Utilisateur, Modele_Relance, Temps_Relance, Activites
import json
from celery import Celery


# Données temporaires pour l'authentification
TEMP_USERS = {
    'antoine': {
        'password': '1234',
        'pole': 'administratif'
    },
}


def login_view(request):
    """Page de connexion"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Vérification des credentials
        if username in TEMP_USERS and TEMP_USERS[username]['password'] == password:
            # Stockage du pôle en session
            request.session['user_pole'] = TEMP_USERS[username]['pole']
            request.session['username'] = username

            # Redirection vers le pôle correspondant
            pole = TEMP_USERS[username]['pole']
            return redirect(pole)
        else:
            # Identifiants incorrects
            return render(request, 'registration/login.html', {'error': 'Identifiants incorrects'})

    return render(request, 'registration/login.html')


def administratif_view(request):
    """
    Page du pôle administratif - LOGIQUE INVERSÉE : affiche les emails ENVOYÉS
    VERSION OAUTH2 : Récupère les emails de l'utilisateur connecté
    """
    # Vérifications de session désactivées pour le développement
    # if 'user_pole' not in request.session:
    #     return redirect('login')
    # if request.session['user_pole'] != 'administratif':
    #     return redirect('login')

    # ⭐ MODIFICATION OAUTH2 : Récupère l'utilisateur connecté
    user = request.user

    # Récupération des emails à chaque chargement de page
    # ⭐ MODIFICATION OAUTH2 : Passe user à fetch_new_emails
    fetch_new_emails(user)

    # Récupère les 20 derniers emails ENVOYÉS (au lieu des emails reçus)
    # ⭐ MODIFICATION OAUTH2 : Passe user à get_sent_emails
    emails = get_sent_emails(user, limit=20)

    # Formate les emails pour l'affichage
    emails_data = [get_email_summary(email) for email in emails]

    return render(request, 'management.html', {
        'pole_name': 'Administratif',
        'emails': emails_data,
    })


@require_http_methods(["POST"])
def send_reply_view(request):
    """
    API endpoint pour envoyer une relance à un destinataire
    VERSION OAUTH2 : N'utilise plus Message.objects car les IDs sont des IDs Gmail (strings)
    Retourne une réponse JSON
    """
    try:
        # Récupère les données du formulaire
        data = json.loads(request.body)

        email_id = data.get('email_id')
        message_text = data.get('message')
        to_email = data.get('to_email')
        subject = data.get('subject')

        if not email_id or not message_text:
            return JsonResponse({
                'success': False,
                'message': 'Données manquantes'
            }, status=400)

        if not to_email or not subject:
            return JsonResponse({
                'success': False,
                'message': 'Destinataire ou sujet manquant'
            }, status=400)

        # ⭐ MODIFICATION OAUTH2 : Récupère l'utilisateur connecté
        user = request.user

        # Envoie la relane
        # ⭐ MODIFICATION OAUTH2 : Passe user à send_email_reply
        result = send_email_reply(
            to_email=to_email,
            subject=subject,
            message_text=message_text,
            original_message_id=email_id,  # Gmail ID (pour référence uniquement)
            user=user
        )

        return JsonResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Erreur : {str(e)}'
        }, status=500)




@require_http_methods(["POST"])
def generate_auto_message_view(request):
    """
    Génère un message pré-rempli basé sur les infos de la table Modele_Relance
    INCHANGÉ : Ne nécessite pas de modification pour OAuth2

    LOGIQUE DE LIAISON :
    1. Email.to_header → Utilisateur.email
    2. Utilisateur.id → Modele_Relance.utilisateur

    Structure des tables :
    - Utilisateurs : id (PK), email, nom, prenom
    - Modele_Relance : utilisateur (PK, FK → Utilisateurs.id), message, objet

    Returns:
        JsonResponse: {'success': bool, 'message': str, 'objet': str (optionnel)}
    """
    try:
        # 1. Récupère et valide les données de la requête
        data = json.loads(request.body)
        email_id = data.get('email_id')

        if not email_id:
            return JsonResponse({
                'success': False,
                'message': 'ID email manquant'
            }, status=400)

        print(f"\n{'='*60}")
        print(f"🚀 DÉBUT generate_auto_message_view()")
        print(f"   email_id: {email_id}")
        print(f"{'='*60}")

        # 2. Récupère l'email envoyé depuis django-mailbox
        from django_mailbox.models import Message
        original_email = Message.objects.get(id=email_id)
        destinataire_email = original_email.to_header

        print(f"\n📧 Email original récupéré")
        print(f"   to_header: {destinataire_email}")

        # 3. Cherche l'utilisateur par email dans la table Utilisateurs
        print(f"\n🔍 Recherche utilisateur dans Utilisateurs...")
        print(f"   WHERE email = '{destinataire_email}'")

        utilisateur = Utilisateur.objects.get(email=destinataire_email)

        print(f"✅ Utilisateur trouvé !")
        print(f"   Utilisateur.id: '{utilisateur.id}'")
        print(f"   Utilisateur.prenom: {utilisateur.prenom}")
        print(f"   Utilisateur.nom: {utilisateur.nom}")
        print(f"   Utilisateur.email: {utilisateur.email}")

        # 4. Cherche le modèle de relance avec Modele_Relance.utilisateur = Utilisateur.id
        print(f"\n🔍 Recherche modèle de relance dans Modele_Relance...")
        print(f"   WHERE utilisateur = '{utilisateur.id}'")
        print(f"   (Modele_Relance.utilisateur doit correspondre à Utilisateur.id)")

        modele_relance = Modele_Relance.objects.get(utilisateur=utilisateur.id)

        print(f"✅ Modèle de relance trouvé !")
        print(f"   Modele_Relance.utilisateur: '{modele_relance.utilisateur}'")
        print(f"   Modele_Relance.metier: {modele_relance.metier}")
        print(f"   Modele_Relance.pole: {modele_relance.pole}")

        if modele_relance.objet:
            print(f"   Modele_Relance.objet: {modele_relance.objet}")
        else:
            print(f"   Modele_Relance.objet: (vide)")

        if modele_relance.message:
            print(f"   Modele_Relance.message: {modele_relance.message[:100]}...")
        else:
            print(f"   Modele_Relance.message: (vide)")

        # 5. Prépare le message personnalisé
        message_template = modele_relance.message if modele_relance.message else "Message de relance par défaut"
        objet_email = modele_relance.objet if modele_relance.objet else None

        # 6. Construit la réponse JSON
        response_data = {
            'success': True,
            'message': message_template
        }

        # Ajoute l'objet si disponible
        if objet_email:
            response_data['objet'] = objet_email

        print(f"\n✅✅✅ Message généré avec succès !")
        print(f"{'='*60}\n")

        return JsonResponse(response_data)

    except Message.DoesNotExist:
        print(f"\n❌ Email introuvable (ID: {email_id})")
        print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': 'Email introuvable'
        }, status=404)

    except Utilisateur.DoesNotExist:
        print(f"\n❌ Utilisateur non trouvé")
        print(f"   Email recherché: {destinataire_email}")
        print(f"   Aucun utilisateur dans la table Utilisateurs avec cet email")
        print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Utilisateur non trouvé pour {destinataire_email}'
        }, status=404)

    except Modele_Relance.DoesNotExist:
        print(f"\n❌ Modèle de relance non trouvé")
        print(f"   Utilisateur.id: '{utilisateur.id}'")
        print(f"   Aucun enregistrement dans Modele_Relance avec utilisateur = '{utilisateur.id}'")
        print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Aucun modèle de relance trouvé pour cet utilisateur'
        }, status=404)

    except Exception as e:
        print(f"\n❌❌❌ ERREUR INATTENDUE : {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_calendar_activities(request):
    """
    API endpoint pour récupérer les activités du calendrier
    INCHANGÉ : Ne nécessite pas de modification pour OAuth2

    Paramètres GET :
    - month : numéro du mois (1-12)
    - year : année (ex: 2025)

    Retourne :
    - Liste des activités avec leurs détails pour affichage dans le calendrier
    """
    try:
        # Récupérer les paramètres (par défaut = mois/année actuels)
        from datetime import datetime  # ← Import local pour éviter conflit
        now = datetime.now()  # ← Utilise datetime.now() au lieu de timezone.now()
        month = int(request.GET.get('month', now.month))
        year = int(request.GET.get('year', now.year))

        print(f"\n{'=' * 60}")
        print(f"📅 API Calendar Activities - Requête pour {month}/{year}")
        print(f"{'=' * 60}")

        # Calculer les dates de début et fin du mois
        start_date = datetime(year, month, 1)

        # Fin du mois = début du mois suivant
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        print(f"📊 Période : {start_date.date()} → {end_date.date()}")

        # Récupérer les activités du mois depuis la BD
        activites = Activites.objects.filter(
            date__gte=start_date,
            date__lt=end_date
        ).values('id', 'dossier', 'type', 'pole', 'date', 'commentaire')

        print(f"📊 Activités trouvées : {activites.count()}")

        # Formater les données pour JSON
        activites_list = []
        for act in activites:
            activites_list.append({
                'id': act['id'],
                'dossier': act['dossier'],
                'type': act['type'],
                'pole': act['pole'],
                'date': act['date'].strftime('%Y-%m-%d'),
                'commentaire': act['commentaire'] or ''
            })
            print(f"   - {act['date'].strftime('%Y-%m-%d')} : {act['type']} - {act['dossier']}")

        print(f"{'=' * 60}\n")

        return JsonResponse({
            'success': True,
            'activites': activites_list,
            'month': month,
            'year': year
        })

    except Exception as e:
        print(f"\n❌ Erreur API Calendar Activities : {e}")
        import traceback
        traceback.print_exc()
        print(f"{'=' * 60}\n")

        return JsonResponse({
            'success': False,
            'message': f'Erreur : {str(e)}'
        }, status=500)