from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from management.email_manager import fetch_new_emails, get_all_emails, get_email_summary, send_email_reply
import json

# Données temporaires pour l'authentification
TEMP_USERS = {
    'antoine': {
        'password': '1234',
        'pole': 'administratif'
    },
    # Ajouter d'autres utilisateurs de test si nécessaire
    # 'marie': {'password': '5678', 'pole': 'finance'},
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
    """Page du pôle administratif"""
    # Vérifications de session désactivées pour le développement
    # if 'user_pole' not in request.session:
    #     return redirect('login')
    # if request.session['user_pole'] != 'administratif':
    #     return redirect('login')

    # Récupération des emails à chaque chargement de page
    fetch_new_emails()

    # Récupère les 20 derniers emails
    emails = get_all_emails(limit=20)

    # Formate les emails pour l'affichage
    emails_data = [get_email_summary(email) for email in emails]

    return render(request, 'management.html', {
        'pole_name': 'Administratif',
        'emails': emails_data,
    })


@require_http_methods(["POST"])
def send_reply_view(request):
    """
    API endpoint pour envoyer une réponse à un email
    Retourne une réponse JSON
    """
    try:
        # Récupère les données du formulaire
        data = json.loads(request.body)

        email_id = data.get('email_id')
        message_text = data.get('message')

        if not email_id or not message_text:
            return JsonResponse({
                'success': False,
                'message': 'Données manquantes'
            }, status=400)

        # Récupère l'email original pour obtenir l'expéditeur et le sujet
        from django_mailbox.models import Message
        original_email = Message.objects.get(id=email_id)

        to_email = original_email.from_header
        subject = original_email.subject or "(Sans objet)"

        # Envoie la réponse
        result = send_email_reply(
            to_email=to_email,
            subject=subject,
            message_text=message_text,
            original_message_id=email_id
        )

        return JsonResponse(result)

    except Message.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Email introuvable'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)