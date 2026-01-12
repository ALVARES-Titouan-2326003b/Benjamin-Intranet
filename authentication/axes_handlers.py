from django.shortcuts import render
from django.utils import timezone
from axes.models import AccessAttempt
from axes.helpers import get_client_ip_address
from django.conf import settings
import datetime

def custom_lockout_response(request, response=None, credentials=None):
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
        cooloff_hours = getattr(settings, 'AXES_COOLOFF_TIME', 0)
        if cooloff_hours:
            lockout_time = attempt.attempt_time
            cooloff_delta = datetime.timedelta(hours=cooloff_hours)
            unlock_time = lockout_time + cooloff_delta
            remaining = unlock_time - timezone.now()
            
            if remaining.total_seconds() > 0:
                total_seconds = int(remaining.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                
                context['remaining_minutes'] = minutes
                context['remaining_seconds'] = int(remaining.total_seconds()) # nombre de s
                context['remaining_hours'] = hours
                
                # on le représente en string
                time_str = ""
                if hours > 0:
                    time_str += f"{hours} heure(s) "
                time_str += f"{minutes} minute(s)"
                context['remaining_time_str'] = time_str
                
    context['cooloff_time'] = getattr(settings, 'AXES_COOLOFF_TIME', None)

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
