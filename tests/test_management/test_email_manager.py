"""
Tests pour le module email_manager
Tests des fonctions de gestion d'emails via Gmail API avec OAuth2
"""
import pytest
from django.utils import timezone
from unittest.mock import patch, MagicMock, Mock

from management.email_manager import (
    fetch_new_emails,
    get_sent_emails,
    send_email_reply,
    send_auto_relance,
    check_if_replies_exist,
    get_email_summary,
)
from management.modelsadm import OAuthToken


@pytest.mark.django_db
class TestFetchNewEmails:
    """Tests pour la récupération des nouveaux emails"""

    def test_fetch_without_oauth_token(self, authenticated_user):
        """
        Teste fetch_new_emails sans token OAuth
        Devrait retourner 0
        """
        result = fetch_new_emails(authenticated_user)

        assert result == 0
        assert not OAuthToken.objects.filter(user=authenticated_user).exists()

    def test_fetch_with_oauth_token(self, authenticated_user, oauth_token, mock_gmail_service):
        """
        Teste fetch_new_emails avec un token OAuth valide
        Devrait retourner le nombre de messages trouvés
        """
        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                result = fetch_new_emails(authenticated_user)


                assert result == 2

    def test_fetch_with_api_error(self, authenticated_user, oauth_token):
        """
        Teste fetch_new_emails quand l'API Gmail échoue
        Devrait retourner 0 et ne pas crasher
        """
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.side_effect = Exception("API Error")

        with patch('management.oauth_utils.build', return_value=mock_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                result = fetch_new_emails(authenticated_user)

                assert result == 0


@pytest.mark.django_db
class TestGetSentEmails:
    """Tests pour la récupération des emails envoyés"""

    def test_get_sent_emails_without_token(self, authenticated_user):
        """
        Teste get_sent_emails sans token OAuth
        Devrait retourner une liste vide
        """
        result = get_sent_emails(authenticated_user, limit=10)

        assert result == []
        assert isinstance(result, list)

    def test_get_sent_emails_with_token(self, authenticated_user, oauth_token, mock_gmail_service):
        """
        Teste get_sent_emails avec un token OAuth valide
        Devrait retourner une liste d'emails avec détails
        """
        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                with patch('management.email_manager.check_if_replies_exist', return_value=set()):
                    result = get_sent_emails(authenticated_user, limit=10)

                    assert isinstance(result, list)
                    assert len(result) > 0

                    first_email = result[0]
                    assert 'id' in first_email
                    assert 'subject' in first_email
                    assert 'to' in first_email
                    assert 'date' in first_email
                    assert 'status' in first_email
                    assert 'status_emoji' in first_email
                    assert 'status_text' in first_email

    def test_get_sent_emails_with_replied_status(
        self,
        authenticated_user,
        oauth_token,
        mock_gmail_service
    ):
        """
        Teste get_sent_emails avec des emails ayant reçu une réponse
        Le statut devrait être 'replied'
        """
        replied_threads = {'thread_001'}

        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                with patch(
                    'management.email_manager.check_if_replies_exist',
                    return_value=replied_threads
                ):
                    result = get_sent_emails(authenticated_user, limit=10)


                    first_email = result[0]
                    assert first_email['status'] == 'replied'
                    assert first_email['status_emoji'] == '✅'
                    assert first_email['status_text'] == 'Répondu'

    def test_get_sent_emails_with_api_error(self, authenticated_user, oauth_token):
        """
        Teste get_sent_emails quand l'API Gmail échoue
        Devrait retourner une liste vide et ne pas crasher
        """
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.side_effect = Exception("API Error")

        with patch('management.oauth_utils.build', return_value=mock_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                result = get_sent_emails(authenticated_user, limit=10)

                assert result == []




@pytest.mark.django_db
class TestSendEmailReply:
    """Tests pour l'envoi de réponses par email"""

    def test_send_reply_without_oauth_token(self, authenticated_user):
        """
        Teste send_email_reply sans token OAuth
        Devrait retourner success=False avec message d'erreur
        """
        result = send_email_reply(
            to_email='test@example.com',
            subject='Test Subject',
            message_text='Test message',
            original_message_id='msg_001',
            user=authenticated_user
        )

        assert result['success'] is False
        assert 'synchroniser' in result['message'].lower()

    def test_send_reply_with_oauth_token(
        self,
        authenticated_user,
        oauth_token,
        mock_gmail_service
    ):
        """
        Teste send_email_reply avec un token OAuth valide
        Devrait retourner success=True
        """
        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                result = send_email_reply(
                    to_email='client@example.com',
                    subject='Test Subject',
                    message_text='Ceci est une réponse de test',
                    original_message_id='msg_001',
                    user=authenticated_user
                )

                assert result['success'] is True
                assert 'succès' in result['message'].lower()

    def test_send_reply_adds_re_prefix(
        self,
        authenticated_user,
        oauth_token,
        mock_gmail_service
    ):
        """
        Teste que send_email_reply ajoute 'Re:' au sujet s'il n'existe pas
        """
        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                with patch('management.oauth_utils.send_email_via_gmail_api') as mock_send:
                    mock_send.return_value = {'success': True, 'message_id': 'sent_001'}

                    send_email_reply(
                        to_email='client@example.com',
                        subject='Original Subject',
                        message_text='Reply message',
                        original_message_id='msg_001',
                        user=authenticated_user
                    )

                    call_args = mock_send.call_args
                    subject_sent = call_args[0][2]
                    assert subject_sent.startswith('Re:')

    def test_send_reply_with_api_error(self, authenticated_user, oauth_token):
        """
        Teste send_email_reply quand l'API Gmail échoue
        Devrait retourner success=False
        """
        with patch('management.oauth_utils.send_email_via_gmail_api') as mock_send:
            mock_send.return_value = {
                'success': False,
                'error': 'Gmail API Error'
            }

            result = send_email_reply(
                to_email='client@example.com',
                subject='Test Subject',
                message_text='Test message',
                original_message_id='msg_001',
                user=authenticated_user
            )

            assert result['success'] is False
            assert 'erreur' in result['message'].lower()




@pytest.mark.django_db
class TestSendAutoRelance:
    """Tests pour l'envoi de relances automatiques"""

    def test_send_auto_relance_with_custom_subject(
        self,
        authenticated_user,
        oauth_token,
        mock_gmail_service
    ):
        """
        Teste send_auto_relance avec un objet personnalisé
        Devrait utiliser l'objet personnalisé + ': relance automatique'
        """
        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                with patch('management.oauth_utils.send_email_via_gmail_api') as mock_send:
                    mock_send.return_value = {'success': True, 'message_id': 'sent_001'}

                    send_auto_relance(
                        to_email='client@example.com',
                        subject='Original Subject',
                        message_text='Relance message',
                        objet_custom='Dossier Important',
                        original_message_id='msg_001',
                        user=authenticated_user
                    )


                    call_args = mock_send.call_args
                    subject_sent = call_args[0][2]
                    assert 'Dossier Important' in subject_sent
                    assert 'relance automatique' in subject_sent

    def test_send_auto_relance_without_custom_subject(
        self,
        authenticated_user,
        oauth_token,
        mock_gmail_service
    ):
        """
        Teste send_auto_relance sans objet personnalisé
        Devrait utiliser le sujet original + ': relance automatique'
        """
        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                with patch('management.oauth_utils.send_email_via_gmail_api') as mock_send:
                    mock_send.return_value = {'success': True, 'message_id': 'sent_001'}

                    send_auto_relance(
                        to_email='client@example.com',
                        subject='Original Subject',
                        message_text='Relance message',
                        objet_custom=None,
                        original_message_id='msg_001',
                        user=authenticated_user
                    )

                    call_args = mock_send.call_args
                    subject_sent = call_args[0][2]
                    assert 'Original Subject' in subject_sent
                    assert 'relance automatique' in subject_sent


@pytest.mark.django_db
class TestCheckIfRepliesExist:
    """Tests pour la vérification de réponses reçues"""

    def test_check_replies_without_oauth_token(self, authenticated_user):
        """
        Teste check_if_replies_exist sans token OAuth
        Devrait retourner un set vide et ne pas crasher
        """

        result = check_if_replies_exist(authenticated_user)

        assert isinstance(result, set)
        assert len(result) == 0

    def test_check_replies_with_oauth_token(
        self,
        authenticated_user,
        oauth_token,
        mock_gmail_service
    ):
        """
        Teste check_if_replies_exist avec un token OAuth valide
        Devrait retourner un set de thread_ids
        """
        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                result = check_if_replies_exist(authenticated_user)

                assert isinstance(result, set)

                assert len(result) == 2
                assert 'thread_001' in result
                assert 'thread_002' in result

    def test_check_replies_with_api_error(self, authenticated_user, oauth_token):
        """
        Teste check_if_replies_exist quand l'API Gmail échoue
        Devrait retourner un set vide et ne pas crasher
        """
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.side_effect = Exception("API Error")

        with patch('management.oauth_utils.build', return_value=mock_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                result = check_if_replies_exist(authenticated_user)

                assert isinstance(result, set)
                assert len(result) == 0




@pytest.mark.django_db
class TestGetEmailSummary:
    """Tests pour le formatage de résumé d'email"""

    def test_get_email_summary_with_dict(self):
        """
        Teste get_email_summary avec un dictionnaire
        Devrait retourner le dictionnaire tel quel
        """
        email_dict = {
            'id': 'msg_001',
            'subject': 'Test Subject',
            'to': 'client@example.com',
            'date': timezone.now(),
            'status': 'pending'
        }

        result = get_email_summary(email_dict)

        assert result == email_dict
        assert result['id'] == 'msg_001'
        assert result['subject'] == 'Test Subject'

    def test_get_email_summary_with_object(self):
        """
        Teste get_email_summary avec un objet (fallback)
        Devrait retourner un dictionnaire formaté
        """

        mock_email = Mock()
        mock_email.id = 'msg_002'
        mock_email.subject = 'Mock Subject'
        mock_email.from_header = 'sender@example.com'
        mock_email.to_header = 'recipient@example.com'
        mock_email.processed = timezone.now()

        result = get_email_summary(mock_email)

        assert isinstance(result, dict)
        assert result['id'] == 'msg_002'
        assert result['subject'] == 'Mock Subject'
        assert result['from'] == 'sender@example.com'
        assert result['to'] == 'recipient@example.com'
        assert result['status'] == 'pending'

