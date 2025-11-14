from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from management.email_manager import fetch_new_emails, get_sent_emails, get_email_summary, send_email_reply
from management.models import Utilisateur, Relance
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
    """Page du pôle administratif - LOGIQUE INVERSÉE : affiche les emails ENVOYÉS"""
    # Vérifications de session désactivées pour le développement
    # if 'user_pole' not in request.session:
    #     return redirect('login')
    # if request.session['user_pole'] != 'administratif':
    #     return redirect('login')

    # Récupération des emails à chaque chargement de page
    fetch_new_emails()

    # Récupère les 20 derniers emails ENVOYÉS (au lieu des emails reçus)
    emails = get_sent_emails(limit=20)

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
    Adapté pour les emails ENVOYÉS (on relance le destinataire original)
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

        # Récupère l'email original (qu'on a envoyé)
        from django_mailbox.models import Message
        original_email = Message.objects.get(id=email_id)

        # CHANGEMENT : On relance le destinataire (to_header) au lieu de l'expéditeur (from_header)
        to_email = original_email.to_header  # Le destinataire de notre email original
        subject = original_email.subject or "(Sans objet)"

        # Envoie la relance
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


@require_http_methods(["POST"])
def generate_auto_message_view(request):
    """
    Génère un message pré-rempli basé sur les infos de la table Relance

    Logique :
    1. Récupère l'email du destinataire depuis Message.to_header
    2. Cherche l'utilisateur dans la table Utilisateurs par email
    3. Cherche la relance associée à cet utilisateur (Relance.utilisateur = Utilisateur.id)
    4. Retourne le message pré-fait : "test message prefait pour verification"

    Returns:
        JsonResponse: {'success': bool, 'message': str}
    """
    try:
        # Récupère les données
        data = json.loads(request.body)
        email_id = data.get('email_id')

        if not email_id:
            return JsonResponse({
                'success': False,
                'message': 'ID email manquant'
            }, status=400)

        # 1. Récupère l'email envoyé
        from django_mailbox.models import Message
        original_email = Message.objects.get(id=email_id)
        destinataire_email = original_email.to_header

        # 2. Cherche l'utilisateur par email
        utilisateur = Utilisateur.objects.get(email=destinataire_email)

        # 3. Cherche la relance pour cet utilisateur
        relance = Relance.objects.get(utilisateur=utilisateur.id)

        # 4. Génère le message pré-fait (pour vérification)
        message_template = "test message prefait pour verification"

        return JsonResponse({
            'success': True,
            'message': message_template
        })

    except Message.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Email introuvable'
        }, status=404)
    except Utilisateur.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f'Utilisateur non trouvé pour {destinataire_email}'
        }, status=404)
    except Relance.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Aucune relance trouvée pour cet utilisateur'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def generate_auto_message_view(request):
    """
    API endpoint pour générer automatiquement un message pré-rempli
    Basé sur les infos de la table Relance associée à l'utilisateur destinataire
    Retourne une réponse JSON avec le message généré
    """
    try:
        # Récupère les données du formulaire
        data = json.loads(request.body)
        email_id = data.get('email_id')

        if not email_id:
            return JsonResponse({
                'success': False,
                'message': 'ID email manquant'
            }, status=400)

        # 1. Récupère l'email envoyé
        from django_mailbox.models import Message
        original_email = Message.objects.get(id=email_id)
        destinataire_email = original_email.to_header

        # 2. Cherche l'utilisateur par email
        from management.models import Utilisateur, Relance

        utilisateur = Utilisateur.objects.get(email=destinataire_email)

        # 3. Cherche la relance pour cet utilisateur
        relance = Relance.objects.get(utilisateur=utilisateur.id)

        # 4. Génère le message pré-fait
        message_template = "test message prefait pour verification"

        return JsonResponse({
            'success': True,
            'message': message_template
        })

    except Message.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Email introuvable'
        }, status=404)
    except Utilisateur.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Utilisateur introuvable'
        }, status=404)
    except Relance.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Relance introuvable'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)