"""
Tests pour le module chatbot.legifrance
Tests des fonctions d'intégration avec l'API Légifrance
"""
import pytest

from unittest.mock import patch, Mock


from chatbot.legifrance import (
    _get_legifrance_token,
    _normalize_query,
    legifrance_search_generic,
    format_legifrance_context,
    _token_cache,
)




class TestGetLegifranceToken:
    """Tests pour la fonction _get_legifrance_token"""

    def setup_method(self):
        """Réinitialiser le cache avant chaque test"""
        _token_cache["access_token"] = None
        _token_cache["expires_at"] = 0

    @patch('chatbot.legifrance.CLIENT_ID', 'test_client_id')
    @patch('chatbot.legifrance.CLIENT_SECRET', 'test_secret')
    @patch('chatbot.legifrance.requests.post')
    @patch('time.time')
    def test_first_call_fetches_token(self, mock_time, mock_post):
        """Teste que le premier appel récupère un nouveau token"""
        mock_time.return_value = 1000.0


        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token_12345',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response

        token = _get_legifrance_token()

        assert token == 'new_token_12345'
        assert _token_cache['access_token'] == 'new_token_12345'
        assert _token_cache['expires_at'] == 1000.0 + 3600


        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'client_id' in call_args[1]['data']
        assert call_args[1]['data']['client_id'] == 'test_client_id'

    @patch('chatbot.legifrance.CLIENT_ID', 'test_client_id')
    @patch('chatbot.legifrance.CLIENT_SECRET', 'test_secret')
    @patch('chatbot.legifrance.requests.post')
    @patch('time.time')
    def test_cached_token_reused(self, mock_time, mock_post):
        """Teste que le token en cache est réutilisé s'il est encore valide"""
        mock_time.return_value = 1000.0


        _token_cache['access_token'] = 'cached_token_abc'
        _token_cache['expires_at'] = 2000.0

        token = _get_legifrance_token()

        assert token == 'cached_token_abc'

        mock_post.assert_not_called()

    @patch('chatbot.legifrance.CLIENT_ID', 'test_client_id')
    @patch('chatbot.legifrance.CLIENT_SECRET', 'test_secret')
    @patch('chatbot.legifrance.requests.post')
    @patch('time.time')
    def test_expired_token_refreshed(self, mock_time, mock_post):
        """Teste qu'un token expiré est rafraîchi"""
        mock_time.return_value = 2000.0


        _token_cache['access_token'] = 'old_expired_token'
        _token_cache['expires_at'] = 1500.0


        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'refreshed_token_xyz',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response

        token = _get_legifrance_token()

        assert token == 'refreshed_token_xyz'
        assert _token_cache['access_token'] == 'refreshed_token_xyz'
        mock_post.assert_called_once()

    @patch('chatbot.legifrance.CLIENT_ID', 'test_client_id')
    @patch('chatbot.legifrance.CLIENT_SECRET', 'test_secret')
    @patch('chatbot.legifrance.requests.post')
    @patch('time.time')
    def test_token_near_expiry_refreshed(self, mock_time, mock_post):
        """Teste qu'un token proche de l'expiration (< 60s) est rafraîchi"""
        mock_time.return_value = 2000.0


        _token_cache['access_token'] = 'almost_expired_token'
        _token_cache['expires_at'] = 2020.0


        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token_after_margin',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response

        token = _get_legifrance_token()

        assert token == 'new_token_after_margin'
        mock_post.assert_called_once()

    @patch('chatbot.legifrance.CLIENT_ID', None)
    @patch('chatbot.legifrance.CLIENT_SECRET', 'test_secret')
    def test_missing_client_id_raises_error(self):
        """Teste qu'un CLIENT_ID manquant lève une erreur"""
        with pytest.raises(RuntimeError) as exc_info:
            _get_legifrance_token()

        assert 'LEGIFRANCE_CLIENT_ID' in str(exc_info.value)

    @patch('chatbot.legifrance.CLIENT_ID', 'test_client_id')
    @patch('chatbot.legifrance.CLIENT_SECRET', None)
    def test_missing_client_secret_raises_error(self):
        """Teste qu'un CLIENT_SECRET manquant lève une erreur"""
        with pytest.raises(RuntimeError) as exc_info:
            _get_legifrance_token()

        assert 'LEGIFRANCE_CLIENT_SECRET' in str(exc_info.value)

    @patch('chatbot.legifrance.CLIENT_ID', 'test_client_id')
    @patch('chatbot.legifrance.CLIENT_SECRET', 'test_secret')
    @patch('chatbot.legifrance.requests.post')
    def test_oauth_request_failure(self, mock_post):
        """Teste la gestion d'erreur quand l'appel OAuth échoue"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("OAuth Error 401")
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            _get_legifrance_token()

        assert 'OAuth Error 401' in str(exc_info.value)

    @patch('chatbot.legifrance.CLIENT_ID', 'test_client_id')
    @patch('chatbot.legifrance.CLIENT_SECRET', 'test_secret')
    @patch('chatbot.legifrance.requests.post')
    @patch('time.time')
    def test_default_expires_in_when_missing(self, mock_time, mock_post):
        """Teste que expires_in par défaut est 3600s si absent de la réponse"""
        mock_time.return_value = 1000.0


        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'token_no_expiry'
        }
        mock_post.return_value = mock_response

        token = _get_legifrance_token()

        assert token == 'token_no_expiry'
        assert _token_cache['expires_at'] == 1000.0 + 3600




class TestNormalizeQuery:
    """Tests pour la fonction _normalize_query"""

    def test_basic_string(self):
        """Teste la normalisation d'une chaîne simple"""
        result = _normalize_query("hello world")
        assert result == "hello world"

    def test_removes_accents(self):
        """Teste la suppression des accents"""
        result = _normalize_query("Café français")
        assert result == "Cafe francais"

    def test_removes_cedilla(self):
        """Teste la suppression de cédille"""
        result = _normalize_query("Ça va")
        assert result == "Ca va"

    def test_multiple_accents(self):
        """Teste avec plusieurs types d'accents"""
        result = _normalize_query("Élève à l'école")
        assert result == "Eleve a l'ecole"

    def test_strips_whitespace(self):
        """Teste le strip des espaces en début/fin"""
        result = _normalize_query("  hello world  ")
        assert result == "hello world"

    def test_empty_string(self):
        """Teste avec une chaîne vide"""
        result = _normalize_query("")
        assert result == ""

    def test_whitespace_only(self):
        """Teste avec uniquement des espaces"""
        result = _normalize_query("   ")
        assert result == ""

    def test_unicode_normalization(self):
        """Teste la normalisation complète Unicode"""

        result = _normalize_query("École")
        assert result == "Ecole"

    def test_special_characters_preserved(self):
        """Teste que les caractères spéciaux non-diacritiques sont préservés"""
        result = _normalize_query("Article L. 123-4")
        assert "L." in result
        assert "123-4" in result




class TestLegifranceSearchGeneric:
    """Tests pour la fonction legifrance_search_generic"""

    @patch('chatbot.legifrance._get_legifrance_token')
    @patch('chatbot.legifrance.requests.post')
    def test_successful_search(self, mock_post, mock_token):
        """Teste une recherche réussie"""
        mock_token.return_value = 'valid_token_123'


        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'results': [
                {'id': '1', 'title': 'Loi test 1'},
                {'id': '2', 'title': 'Loi test 2'},
            ]
        }
        mock_post.return_value = mock_response

        result = legifrance_search_generic("code du travail")

        assert 'results' in result
        assert len(result['results']) == 2


        call_args = mock_post.call_args
        assert call_args[1]['headers']['Authorization'] == 'Bearer valid_token_123'

    @patch('chatbot.legifrance._get_legifrance_token')
    @patch('chatbot.legifrance.requests.post')
    def test_search_with_custom_fond(self, mock_post, mock_token):
        """Teste une recherche avec un fond personnalisé"""
        mock_token.return_value = 'valid_token_123'

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {'results': []}
        mock_post.return_value = mock_response

        legifrance_search_generic("test query", fond="CODE", page_size=10)


        call_args = mock_post.call_args
        body = call_args[1]['json']
        assert body['fond'] == 'CODE'
        assert body['recherche']['pageSize'] == 10

    @patch('chatbot.legifrance._get_legifrance_token')
    @patch('chatbot.legifrance.requests.post')
    def test_query_is_normalized(self, mock_post, mock_token):
        """Teste que la query est normalisée avant envoi"""
        mock_token.return_value = 'valid_token_123'

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {'results': []}
        mock_post.return_value = mock_response

        legifrance_search_generic("Café français")

        call_args = mock_post.call_args
        body = call_args[1]['json']
        query_sent = body['recherche']['champs'][0]['criteres'][0]['valeur']
        assert 'Cafe francais' == query_sent

    @patch('chatbot.legifrance._get_legifrance_token')
    @patch('chatbot.legifrance.requests.post')
    def test_api_error_raises_runtime_error(self, mock_post, mock_token):
        """Teste qu'une erreur API lève une RuntimeError"""
        mock_token.return_value = 'valid_token_123'

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            legifrance_search_generic("test query")

        assert '500' in str(exc_info.value)
        assert 'Erreur Légifrance' in str(exc_info.value)

    @patch('chatbot.legifrance._get_legifrance_token')
    @patch('chatbot.legifrance.requests.post')
    def test_timeout_handled(self, mock_post, mock_token):
        """Teste la gestion du timeout"""
        mock_token.return_value = 'valid_token_123'

        import requests
        mock_post.side_effect = requests.Timeout("Request timed out")

        with pytest.raises(requests.Timeout):
            legifrance_search_generic("test query")

    @patch('chatbot.legifrance._get_legifrance_token')
    @patch('chatbot.legifrance.requests.post')
    def test_empty_results(self, mock_post, mock_token):
        """Teste une recherche sans résultats"""
        mock_token.return_value = 'valid_token_123'

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {'results': []}
        mock_post.return_value = mock_response

        result = legifrance_search_generic("query avec aucun résultat")

        assert result['results'] == []




class TestFormatLegifranceContext:
    """Tests pour la fonction format_legifrance_context"""

    def test_format_with_results_key(self):
        """Teste le formatage avec la clé 'results'"""
        search_result = {
            'results': [
                {
                    'nature': 'LOI',
                    'datePublication': '2024-01-15',
                    'title': 'Loi de finances 2024',
                    'nor': 'ECOX2400001L',
                    'cid': 'LEGITEXT000012345678'
                }
            ]
        }

        context = format_legifrance_context(search_result)

        assert 'LOI' in context
        assert 'Loi de finances 2024' in context
        assert 'ECOX2400001L' in context
        assert '2024-01-15' in context

    def test_format_with_results_list_key(self):
        """Teste le formatage avec la clé 'resultsList'"""
        search_result = {
            'resultsList': [
                {
                    'natureTexte': 'DECRET',
                    'dateVersion': '2024-02-01',
                    'titre': 'Décret test',
                    'nor': 'PRMX2400002D',
                    'idTexte': 'TEXT123456'
                }
            ]
        }

        context = format_legifrance_context(search_result)

        assert 'DECRET' in context
        assert 'Décret test' in context

    def test_format_with_missing_fields(self):
        """Teste le formatage avec des champs manquants (fallback)"""
        search_result = {
            'results': [
                {
                    'title': 'Texte sans métadonnées complètes'
                }
            ]
        }

        context = format_legifrance_context(search_result)


        assert '—' in context
        assert 'Texte sans métadonnées complètes' in context

    def test_format_respects_max_items(self):
        """Teste que max_items limite le nombre de résultats"""
        search_result = {
            'results': [
                {'title': f'Résultat {i}'} for i in range(10)
            ]
        }

        context = format_legifrance_context(search_result, max_items=3)


        assert 'Résultat 0' in context
        assert 'Résultat 1' in context
        assert 'Résultat 2' in context
        assert 'Résultat 3' not in context

    def test_format_empty_results(self):
        """Teste le formatage avec des résultats vides"""
        search_result = {'results': []}

        context = format_legifrance_context(search_result)


        assert 'Aperçu brut' in context or 'results' in context

    def test_format_no_structured_results(self):
        """Teste avec une réponse sans structure de résultats connue"""
        search_result = {
            'some_other_field': 'data',
            'metadata': {'count': 0}
        }

        context = format_legifrance_context(search_result)


        assert 'Aperçu brut' in context

    def test_format_with_alternative_field_names(self):
        """Teste le formatage avec des noms de champs alternatifs"""
        search_result = {
            'items': [
                {
                    'typeTexte': 'ORDONNANCE',
                    'date': '2024-03-01',
                    'textTitle': 'Ordonnance test',
                    'nor': 'JUST2400003X',
                    'textId': 'ORD987654'
                }
            ]
        }

        context = format_legifrance_context(search_result)

        assert 'ORDONNANCE' in context
        assert 'Ordonnance test' in context
        assert 'JUST2400003X' in context

    def test_format_handles_unicode(self):
        """Teste que le formatage gère correctement les caractères Unicode"""
        search_result = {
            'results': [
                {
                    'title': 'Loi sur l égalité femmes-hommes',
                    'nature': 'LOI',
                    'datePublication': '2024-01-01',
                    'nor': 'EGALX2400001L',
                    'cid': 'LEX123'
                }
            ]
        }

        context = format_legifrance_context(search_result)


        assert 'égalité' in context or 'egalite' in context
        assert 'femmes' in context and 'hommes' in context

    def test_format_multiple_results(self):
        """Teste le formatage de plusieurs résultats"""
        search_result = {
            'results': [
                {'title': 'Résultat 1', 'nature': 'LOI'},
                {'title': 'Résultat 2', 'nature': 'DECRET'},
                {'title': 'Résultat 3', 'nature': 'ARRETE'},
            ]
        }

        context = format_legifrance_context(search_result)

        assert 'Résultat 1' in context
        assert 'Résultat 2' in context
        assert 'Résultat 3' in context
        assert 'LOI' in context
        assert 'DECRET' in context