from .models import UserPreference

def theme_context(request):
    if request.user.is_authenticated:
        try:
            # We use hasattr to check for the reverse relation if it exists, 
            # or try/except DoesNotExist if we query explicitly.
            # The signal should have created it, but defensive programming is good.
            preference = request.user.preferences
            return {'current_theme': preference.theme}
        except UserPreference.DoesNotExist:
            return {'current_theme': 'light'}
    return {'current_theme': 'light'}
