"""
Vues pour la partie administrative - Gestion des emails et relances
VERSION MICROSOFT GRAPH API
CHANGEMENT PRINCIPAL : generate_auto_message_view ne utilise plus django_mailbox
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .email_manager import fetch_new_emails, get_sent_emails, get_email_summary, send_email_reply
from .modelsadm import Utilisateur, Modele_Relance, Temps_Relance, Activites
import json


# Donnees temporaires pour l'authentification
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

        # Verification des credentials
        if username in TEMP_USERS and TEMP_USERS[username]['password'] == password:
            # Stockage du pole en session
            request.session['user_pole'] = TEMP_USERS[username]['pole']
            request.session['username'] = username

            # Redirection vers le pole correspondant
            pole = TEMP_USERS[username]['pole']
            return redirect(pole)
        else:
            # Identifiants incorrects
            return render(request, 'registration/login.html', {'error': 'Identifiants incorrects'})

    return render(request, 'registration/login.html')


def administratif_view(request):
    """
    Page du pole administratif - Affiche les emails ENVOYES
    VERSION MICROSOFT GRAPH API
    """

    # Recupere l'utilisateur connecte
    user = request.user

    # Recuperation des emails a chaque chargement de page
    fetch_new_emails(user)

    # Recupere les 20 derniers emails ENVOYES
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
    API endpoint pour envoyer une relance a un destinataire
    VERSION MICROSOFT GRAPH API
    """
    try:
        # Recupere les donnees du formulaire
        data = json.loads(request.body)

        email_id = data.get('email_id')
        message_text = data.get('message')
        to_email = data.get('to_email')
        subject = data.get('subject')

        if not email_id or not message_text:
            return JsonResponse({
                'success': False,
                'message': 'Donnees manquantes'
            }, status=400)

        if not to_email or not subject:
            return JsonResponse({
                'success': False,
                'message': 'Destinataire ou sujet manquant'
            }, status=400)

        # Recupere l'utilisateur connecte
        user = request.user

        # Envoie la relance
        result = send_email_reply(
            to_email=to_email,
            subject=subject,
            message_text=message_text,
            original_message_id=email_id,
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
    Genere un message pre-rempli base sur les infos de la table Modele_Relance
    VERSION MICROSOFT GRAPH API - Ne depend plus de django_mailbox

    CHANGEMENT CRITIQUE :
    - AVANT (Gmail) : Recevait email_id, recuperait l'email depuis django_mailbox
    - APRES (Microsoft) : Recoit email_id ET to_email depuis le frontend

    LOGIQUE DE LIAISON :
    1. to_email (envoye par le frontend) -> Utilisateur.email
    2. Utilisateur.id -> Modele_Relance.utilisateur

    Returns:
        JsonResponse: {'success': bool, 'message': str, 'objet': str (optionnel)}
    """
    try:
        # 1. Recupere et valide les donnees de la requete
        data = json.loads(request.body)
        email_id = data.get('email_id')
        to_email = data.get('to_email')

        if not email_id:
            return JsonResponse({
                'success': False,
                'message': 'ID email manquant'
            }, status=400)

        if not to_email:
            return JsonResponse({
                'success': False,
                'message': 'Adresse email du destinataire manquante'
            }, status=400)

        print(f"\n{'='*60}")
        print(f"DEBUT generate_auto_message_view()")
        print(f"   email_id: {email_id}")
        print(f"   to_email: {to_email}")
        print(f"{'='*60}")

        destinataire_email = to_email

        # 2. Cherche l'utilisateur par email dans la table Utilisateurs
        print(f"\nRecherche utilisateur dans Utilisateurs...")
        print(f"   WHERE email = '{destinataire_email}'")

        utilisateur = Utilisateur.objects.get(email=destinataire_email)

        print(f"Utilisateur trouve !")
        print(f"   Utilisateur.id: '{utilisateur.id}'")
        print(f"   Utilisateur.prenom: {utilisateur.prenom}")
        print(f"   Utilisateur.nom: {utilisateur.nom}")
        print(f"   Utilisateur.email: {utilisateur.email}")

        # 3. Cherche le modele de relance avec Modele_Relance.utilisateur = Utilisateur.id
        print(f"\nRecherche modele de relance dans Modele_Relance...")
        print(f"   WHERE utilisateur = '{utilisateur.id}'")

        modele_relance = Modele_Relance.objects.get(utilisateur=utilisateur.id)

        print(f"Modele de relance trouve !")
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

        # 4. Prepare le message personnalise
        message_template = modele_relance.message if modele_relance.message else "Message de relance par defaut"
        objet_email = modele_relance.objet if modele_relance.objet else None

        # 5. Construit la reponse JSON
        response_data = {
            'success': True,
            'message': message_template
        }

        # Ajoute l'objet si disponible
        if objet_email:
            response_data['objet'] = objet_email

        print(f"\nMessage genere avec succes !")
        print(f"{'='*60}\n")

        return JsonResponse(response_data)

    except Utilisateur.DoesNotExist:
        print(f"\nUtilisateur non trouve")
        print(f"   Email recherche: {destinataire_email}")
        print(f"   Aucun utilisateur dans la table Utilisateurs avec cet email")
        print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Utilisateur non trouve pour {destinataire_email}'
        }, status=404)

    except Modele_Relance.DoesNotExist:
        print(f"\nModele de relance non trouve")
        print(f"   Utilisateur.id: '{utilisateur.id}'")
        print(f"   Aucun enregistrement dans Modele_Relance avec utilisateur = '{utilisateur.id}'")
        print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Aucun modele de relance trouve pour cet utilisateur'
        }, status=404)

    except Exception as e:
        print(f"\nERREUR INATTENDUE : {e}")
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
    API endpoint pour recuperer les activites du calendrier
    INCHANGE - Ne necessite pas de modification pour Microsoft Graph

    Parametres GET :
    - month : numero du mois (1-12)
    - year : annee (ex: 2025)

    Retourne :
    - Liste des activites avec leurs details pour affichage dans le calendrier
    """
    try:
        # Recuperer les parametres (par defaut = mois/annee actuels)
        from datetime import datetime
        now = datetime.now()
        month = int(request.GET.get('month', now.month))
        year = int(request.GET.get('year', now.year))

        print(f"\n{'=' * 60}")
        print(f"API Calendar Activities - Requete pour {month}/{year}")
        print(f"{'=' * 60}")

        # Calculer les dates de debut et fin du mois
        start_date = datetime(year, month, 1)

        # Fin du mois = debut du mois suivant
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        print(f"Periode : {start_date.date()} -> {end_date.date()}")

        # Recuperer les activites du mois depuis la BD
        activites = Activites.objects.filter(
            date__gte=start_date,
            date__lt=end_date
        ).values('id', 'dossier', 'type', 'pole', 'date', 'commentaire')

        print(f"Activites trouvees : {activites.count()}")

        # Formater les donnees pour JSON
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
        print(f"\nErreur API Calendar Activities : {e}")
        import traceback
        traceback.print_exc()
        print(f"{'=' * 60}\n")

        return JsonResponse({
            'success': False,
            'message': f'Erreur : {str(e)}'
        }, status=500)