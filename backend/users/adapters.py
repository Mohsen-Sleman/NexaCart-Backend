import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger(__name__)

class GoogleSocialAccountAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.is_verified = True
        
        return user