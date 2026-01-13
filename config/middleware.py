import logging
import time

logger = logging.getLogger('audit')

class AuditLogMiddleware:
    """
    Middleware pour logger chaque action de modification (POST, PUT, DELETE)
    avec les 4 W : Who, When, What, Where.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Avant la vue (traitement de la requête)
        
        response = self.get_response(request)
        
        # Après la vue (une fois qu'on a la réponse, et l'utilisateur connecté)
        self.log_action(request, response)
        
        return response

    def log_action(self, request, response):
        # On ne logue que les méthodes de modification
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            user = request.user if hasattr(request, 'user') else 'Anonymous'
            user_display = f"{user.username} (ID: {user.pk})" if user.is_authenticated else "Anonymous"
            
            ip = self.get_client_ip(request)
            path = request.get_full_path()
            method = request.method
            status = response.status_code
            
            # Format:  Who | Where | What | Status
            log_message = f"ACTION: User '{user_display}' | IP: {ip} | {method} {path} | Status: {status}"
            logger.info(log_message)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
