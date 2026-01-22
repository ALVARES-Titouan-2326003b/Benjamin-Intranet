"""
Tests pour le module authentication.axes_handlers
Tests des gestionnaires de verrouillage de compte (django-axes)
"""
import pytest
from datetime import timedelta
from django.test import RequestFactory
from django.utils import timezone
from unittest.mock import Mock


from authentication.axes_handlers import (
    get_axes_username,
)




@pytest.fixture
def request_factory():
    """Factory pour créer des requêtes HTTP"""
    return RequestFactory()


@pytest.fixture
def mock_access_attempt():
    """Mock d'un AccessAttempt"""
    attempt = Mock()
    attempt.username = 'testuser'
    attempt.ip_address = '192.168.1.100'
    attempt.attempt_time = timezone.now() - timedelta(minutes=30)
    return attempt




class TestGetAxesUsername:
    """Tests pour la fonction get_axes_username"""

    def test_username_from_credentials(self, request_factory):
        """Teste la récupération depuis credentials (priorité haute)"""
        request = request_factory.post('/login/')
        credentials = {'username': 'user_from_creds'}

        result = get_axes_username(request, credentials)

        assert result == 'user_from_creds'

    def test_username_from_post(self, request_factory):
        """Teste la récupération depuis request.POST (fallback 1)"""
        request = request_factory.post('/login/', {'username': 'user_from_post'})

        result = get_axes_username(request)

        assert result == 'user_from_post'

    def test_username_from_auth_username(self, request_factory):
        """Teste la récupération depuis auth-username (2FA) (fallback 2)"""
        request = request_factory.post('/login/', {'auth-username': 'user_from_2fa'})

        result = get_axes_username(request)

        assert result == 'user_from_2fa'

    def test_credentials_priority_over_post(self, request_factory):
        """Teste que credentials a priorité sur POST"""
        request = request_factory.post('/login/', {'username': 'user_from_post'})
        credentials = {'username': 'user_from_creds'}

        result = get_axes_username(request, credentials)

        assert result == 'user_from_creds'

    def test_post_priority_over_auth_username(self, request_factory):
        """Teste que username POST a priorité sur auth-username"""
        request = request_factory.post('/login/', {
            'username': 'user_from_post',
            'auth-username': 'user_from_2fa'
        })

        result = get_axes_username(request)

        assert result == 'user_from_post'

    def test_returns_none_when_no_username(self, request_factory):
        """Teste le retour None quand aucun username n'est trouvé"""
        request = request_factory.post('/login/')

        result = get_axes_username(request)

        assert result is None

    def test_empty_credentials_dict(self, request_factory):
        """Teste avec credentials vide"""
        request = request_factory.post('/login/')


        result = get_axes_username(request)

        assert result is None

    def test_credentials_without_username_key(self, request_factory):
        """Teste avec credentials sans clé 'username'"""
        request = request_factory.post('/login/', {'username': 'fallback_user'})
        result = get_axes_username(request)

        assert result == 'fallback_user'

    def test_none_request(self):
        """Teste avec request = None"""
        result = get_axes_username(None, credentials={'username': 'user_creds'})

        assert result == 'user_creds'

    def test_none_request_and_credentials(self):
        """Teste avec request = None et credentials = None"""
        result = get_axes_username(None, None)

        assert result is None