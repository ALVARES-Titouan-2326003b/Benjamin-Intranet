from two_factor.views import LoginView
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

class CustomLoginView(LoginView):
    def post(self, *args, **kwargs):
        # Check if the "Resend" button was clicked
        if 'resend_code' in self.request.POST:
            try:
                # Check if we are in the token step
                if self.storage.current_step == 'token':
                    # Instead of validating the form again, check for user_pk in storage
                    user_pk = self.storage.data.get('user_pk')
                    
                    if user_pk:
                         from django.contrib.auth import get_user_model
                         User = get_user_model()
                         user = User.objects.get(pk=user_pk)
                    else:
                        user = None

                    if user:
                        # Find the backup or sms device. 
                        # Let's inspect available devices
                        for device in user.phonedevice_set.all():
                             if device.name == 'default':
                                 device.generate_challenge()
                                 messages.success(self.request, _("Un nouveau code a été envoyé."))
                                 break
                        else:
                            # If no specific phone found, try first available
                            devices = user.phonedevice_set.all()
                            if devices.exists():
                                devices[0].generate_challenge()
                                messages.success(self.request, _("Un nouveau code a été envoyé."))

            except Exception:
                messages.error(self.request, _("Erreur lors de l'envoi du code."))

            # Prevent redirect loop/reset by maintaining state and rendering directly
            # re-render the 'token' step.
            return self.render_goto_step('token')

        return super().post(*args, **kwargs) 
