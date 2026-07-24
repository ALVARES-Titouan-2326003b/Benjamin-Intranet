from django.shortcuts import render
from django.utils import timezone
from axes.models import AccessAttempt
from axes.helpers import get_client_ip_address, get_cool_off
import math


def _format_duration(total_seconds):
    """Retourne une durée lisible en français."""
    total_seconds = max(0, int(round(total_seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []

    if hours:
        parts.append(f"{hours} heure" + ("s" if hours > 1 else ""))
    if minutes:
        parts.append(f"{minutes} minute" + ("s" if minutes > 1 else ""))
    if seconds and not hours:
        parts.append(f"{seconds} seconde" + ("s" if seconds > 1 else ""))

    return " ".join(parts) or "quelques secondes"

def custom_lockout_response(request, response=None, credentials=None):
    """
    Bloque l'utilisateur pendant un temps après un certain nombre d'échecs
    de connexion
    """
    context = {}
    
    # Obtenir le nom d'utilisateur
    username = None
    if credentials:
        username = credentials.get('username')
    
    if not username:
        username = request.POST.get('username')
        
    # On obtient l'IP
    client_ip = get_client_ip_address(request)

    # Permet de pas relancer le compteur de 1h si l'utilisateur retente de se connecter
    attempt = None
    if username and client_ip:
        attempt = AccessAttempt.objects.filter(username=username, ip_address=client_ip).order_by('attempt_time').first()
    elif client_ip:
         attempt = AccessAttempt.objects.filter(ip_address=client_ip).order_by('attempt_time').first()
         
    if attempt:
        # Calcule le temps restant
        cooloff_delta = get_cool_off(request)
        if cooloff_delta:
            lockout_time = attempt.attempt_time
            unlock_time = lockout_time + cooloff_delta
            remaining = unlock_time - timezone.now()
            
            if remaining.total_seconds() > 0:
                total_seconds = max(1, math.ceil(remaining.total_seconds()))
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                
                context['remaining_minutes'] = minutes
                context['remaining_seconds'] = total_seconds
                context['remaining_hours'] = hours

    cooloff_delta = get_cool_off(request)
    if cooloff_delta:
        context['cooloff_time_str'] = _format_duration(
            cooloff_delta.total_seconds()
        )

    return render(request, 'locked_out.html', context)


def get_axes_username(request, credentials=None):
    """
    On récupère le nom d'utilisateur
    """
    # Vérificatione de l'identification
    if credentials and 'username' in credentials:
        return credentials['username']

    # Admin
    if request and 'username' in request.POST:
        return request.POST.get('username')
    
    # django-two-factor-auth
    if request and 'auth-username' in request.POST:
        return request.POST.get('auth-username')
        
    return None
