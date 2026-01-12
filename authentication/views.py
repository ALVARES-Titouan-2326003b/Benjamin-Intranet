from two_factor.views import LoginView
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

class CustomLoginView(LoginView):
    def post(self, *args, **kwargs):
        # Check if the "Resend" button was clicked
        if 'resend_code' in self.request.POST:
            print(f"DEBUG: Resend code triggered. Current step: {self.storage.current_step}")
            try:
                if self.storage.current_step == 'token':
                    # Instead of validating the form again, check for user_pk in storage
                    # which is set by TwoFactorLoginView after the 'auth' step.
                    user_pk = self.storage.data.get('user_pk')
                    
                    if user_pk:
                         from django.contrib.auth import get_user_model
                         User = get_user_model()
                         user = User.objects.get(pk=user_pk)
                         print(f"DEBUG: Found user via user_pk: {user}")
                    else:
                        user = None
                        print("DEBUG: No user_pk in storage.")

                    if user:
                        # Find the backup or sms device. 
                        # This implies we need to know WHICH device matches the current challenge.
                        # Usually, `two_factor` stores this in `self.storage.data['challenge_device']`.
                        # But simpler: Re-initiating the token step logic might be best.
                        
                        # Let's inspect available devices
                        for device in user.phonedevice_set.all():
                            # If we have a phone device, try generating a challenge.
                            # Ideally we should filter by the one currently active.
                             if device.name == 'default': # Or iterate all?
                                 print(f"DEBUG: Generating challenge for {device}")
                                 device.generate_challenge()
                                 messages.success(self.request, _("Un nouveau code a été envoyé."))
                                 break
                        else:
                            # If no specific phone found (or name mismatch), try first available
                            devices = user.phonedevice_set.all()
                            if devices.exists():
                                print(f"DEBUG: Generating challenge for fallback device {devices[0]}")
                                devices[0].generate_challenge()
                                messages.success(self.request, _("Un nouveau code a été envoyé."))
                    else:
                        print("DEBUG: No user found in view?")

            except Exception as e:
                print(f"DEBUG: Error in resend: {e}")
                messages.error(self.request, _("Erreur lors de l'envoi du code."))

            # Prevent redirect loop/reset by maintaining state and rendering directly
            # re-render the 'token' step.
            return self.render_goto_step('token')

        return super().post(*args, **kwargs) 
