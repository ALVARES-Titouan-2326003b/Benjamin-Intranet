"""
Tests pour le module ai_summary.py (app technique)
Tests de l'analyse de documents juridiques via API Groq
"""
import pytest
import json

from unittest.mock import Mock, patch
from requests.exceptions import HTTPError, Timeout, ConnectionError


@pytest.fixture
def sample_document_text():
    """Texte de document juridique de test"""
    return """
    CONTRAT DE RÉSERVATION VEFA

    Entre les soussignés :
    - Vendeur : SCI IMMOBILIER PRO
    - Acquéreur : M. Jean DUPONT

    ARTICLE 1 - OBJET
    Le présent contrat a pour objet la réservation d'un appartement T3 situé...

    ARTICLE 2 - PRIX
    Le prix de vente s'élève à 250 000 € (deux cent cinquante mille euros).
    Un dépôt de garantie de 5% soit 12 500 € est exigé.

    ARTICLE 3 - DATES IMPORTANTES
    - Date de signature : 15 janvier 2024
    - Date de livraison prévue : 30 juin 2025
    - Date limite de rétractation : 25 janvier 2024

    ARTICLE 4 - CONDITIONS SUSPENSIVES
    Le présent contrat est conclu sous les conditions suspensives suivantes :
    - Obtention d'un prêt immobilier de 200 000 €
    - Obtention du permis de construire

    ARTICLE 5 - PÉNALITÉS
    En cas de retard de livraison, une pénalité de 100 € par jour sera appliquée.

    ARTICLE 6 - DÉLAIS
    Le délai de rétractation est de 10 jours.
    Le délai de réalisation des travaux est de 18 mois.
    """


@pytest.fixture
def sample_short_text():
    """Texte court pour test de chunks"""
    return "Ceci est un texte court de moins de 12000 caractères."


@pytest.fixture
def sample_long_text():
    """Texte long pour test de découpage en chunks"""
    base_text = "Article " * 100 + ".\n"
    return base_text * 30


@pytest.fixture
def valid_api_response():
    """Réponse API Groq valide"""
    return {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "resume": "- Prix de vente : 250 000 €\n- Dépôt de garantie : 12 500 €\n- Appartement T3\n- Livraison prévue juin 2025",
                    "prix": "250 000 € + dépôt 12 500 €",
                    "dates": "Signature : 15/01/2024, Livraison : 30/06/2025",
                    "conditions_suspensives": "Prêt 200 000 €, Permis de construire",
                    "penalites": "100 € par jour de retard",
                    "delais": "Rétractation : 10 jours, Travaux : 18 mois",
                    "clauses_importantes": [
                        "- Prix de vente : 250 000 €",
                        "- Livraison prévue juin 2025"
                    ]
                })
            }
        }]
    }


@pytest.fixture
def invalid_json_response():
    """Réponse API avec JSON invalide"""
    return {
        "choices": [{
            "message": {
                "content": "Ceci n'est pas du JSON valide { malformed"
            }
        }]
    }


@pytest.fixture
def mock_groq_api_success(valid_api_response):
    """Mock de l'API Groq avec succès"""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_api_response
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_groq_api_rate_limit():
    """Mock de l'API Groq avec rate limiting (429)"""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_groq_api_timeout():
    """Mock de l'API Groq avec timeout"""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Timeout("Request timeout")
        yield mock_post


@pytest.fixture
def mock_groq_api_connection_error():
    """Mock de l'API Groq avec erreur de connexion"""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = ConnectionError("Connection failed")
        yield mock_post


class TestTextUtilities:
    """Tests des fonctions utilitaires de traitement de texte"""

    def test_normalize_text_removes_extra_spaces(self):
        """Test que _normalize_text supprime les espaces multiples"""
        from technique.services.ai_summary import _normalize_text

        text = "Ceci    est   un    texte    avec     espaces"
        result = _normalize_text(text)

        assert "    " not in result
        assert "   " not in result
        assert "  " not in result
        assert result == "Ceci est un texte avec espaces"

    def test_normalize_text_removes_empty_lines(self):
        """Test que _normalize_text supprime les lignes vides"""
        from technique.services.ai_summary import _normalize_text

        text = "Ligne 1\n\n\n\nLigne 2\n\n\nLigne 3"
        result = _normalize_text(text)

        assert "\n\n" not in result
        assert result.count("\n") == 2
        assert result == "Ligne 1\nLigne 2\nLigne 3"

    def test_normalize_text_handles_carriage_returns(self):
        """Test que _normalize_text gère les retours chariot"""
        from technique.services.ai_summary import _normalize_text

        text = "Ligne 1\r\nLigne 2\rLigne 3"
        result = _normalize_text(text)

        assert "\r" not in result
        assert result == "Ligne 1\nLigne 2\nLigne 3"

    def test_normalize_text_handles_none(self):
        """Test que _normalize_text gère None"""
        from technique.services.ai_summary import _normalize_text

        result = _normalize_text(None)
        assert result == ""

    def test_normalize_text_handles_empty_string(self):
        """Test que _normalize_text gère les chaînes vides"""
        from technique.services.ai_summary import _normalize_text

        result = _normalize_text("")
        assert result == ""

        result = _normalize_text("   \n\n  \t  \n  ")
        assert result == ""

    def test_estimate_tokens_basic(self):
        """Test de l'estimation du nombre de tokens"""
        from technique.services.ai_summary import _estimate_tokens


        text = "a" * 100
        result = _estimate_tokens(text)

        assert result == 25

    def test_estimate_tokens_empty(self):
        """Test de l'estimation pour texte vide"""
        from technique.services.ai_summary import _estimate_tokens

        assert _estimate_tokens("") == 0
        assert _estimate_tokens(None) == 0

    def test_split_into_chunks_empty(self):
        """Test du découpage avec texte vide"""
        from technique.services.ai_summary import _split_into_chunks

        result = _split_into_chunks("")
        assert result == []

        result = _split_into_chunks(None)
        assert result == []

    def test_split_into_chunks_short_text(self, sample_short_text):
        """Test du découpage avec texte court (1 seul chunk)"""
        from technique.services.ai_summary import _split_into_chunks

        result = _split_into_chunks(sample_short_text)

        assert len(result) == 1
        assert result[0] == sample_short_text

    def test_split_into_chunks_long_text(self, sample_long_text):
        """Test du découpage avec texte long (plusieurs chunks)"""
        from technique.services.ai_summary import _split_into_chunks

        result = _split_into_chunks(sample_long_text)

        assert len(result) >= 2
        assert len(result[0]) == 12000
        assert len(result[-1]) <= 12000
        assert "".join(result) == sample_long_text


class TestJsonParsing:
    """Tests de la fonction _parse_json_or_fallback"""

    def test_parse_valid_json(self):
        """Test du parsing avec JSON valide"""
        from technique.services.ai_summary import _parse_json_or_fallback

        valid_json = json.dumps({
            "resume": "Test resume",
            "prix": "100 000 €",
            "dates": "01/01/2024",
            "conditions_suspensives": "Prêt bancaire",
            "penalites": "50 € par jour",
            "delais": "30 jours",
            "clauses_importantes": ["Clause 1", "Clause 2"]
        })

        result = _parse_json_or_fallback(valid_json)

        assert result["resume"] == "Test resume"
        assert result["prix"] == "100 000 €"
        assert result["dates"] == "01/01/2024"
        assert len(result["clauses_importantes"]) == 2

    def test_parse_json_with_extra_text(self):
        """Test du parsing avec texte autour du JSON"""
        from technique.services.ai_summary import _parse_json_or_fallback

        text_with_json = """
        Voici l'analyse :
        {
            "resume": "Test",
            "prix": "1000",
            "dates": "",
            "conditions_suspensives": "",
            "penalites": "",
            "delais": "",
            "clauses_importantes": []
        }
        Fin de l'analyse.
        """

        result = _parse_json_or_fallback(text_with_json)

        assert result["resume"] == "Test"
        assert result["prix"] == "1000"

    def test_parse_invalid_json_fallback(self):
        """Test du fallback avec JSON invalide"""
        from technique.services.ai_summary import _parse_json_or_fallback

        invalid = "Ceci n'est pas du JSON { malformed }"
        result = _parse_json_or_fallback(invalid)

        assert "resume" in result
        assert "prix" in result
        assert "dates" in result
        assert "clauses_importantes" in result
        assert isinstance(result["clauses_importantes"], list)

        assert len(result["resume"]) <= 800

    def test_parse_json_missing_keys(self):
        """Test du parsing avec clés manquantes"""
        from technique.services.ai_summary import _parse_json_or_fallback

        incomplete_json = json.dumps({
            "resume": "Test",
            "prix": "1000"
        })

        result = _parse_json_or_fallback(incomplete_json)

        assert result["resume"] == "Test"
        assert result["prix"] == "1000"
        assert result["dates"] == ""
        assert result["conditions_suspensives"] == ""
        assert result["penalites"] == ""
        assert result["delais"] == ""
        assert result["clauses_importantes"] == []

    def test_parse_json_invalid_clauses_type(self):
        """Test avec clauses_importantes qui n'est pas une liste"""
        from technique.services.ai_summary import _parse_json_or_fallback

        invalid_clauses = json.dumps({
            "resume": "Test",
            "prix": "",
            "dates": "",
            "conditions_suspensives": "",
            "penalites": "",
            "delais": "",
            "clauses_importantes": "should be a list"
        })

        result = _parse_json_or_fallback(invalid_clauses)

        assert isinstance(result["clauses_importantes"], list)
        assert result["clauses_importantes"] == []

    def test_parse_json_normalizes_strings(self):
        """Test que le parsing normalise les chaînes"""
        from technique.services.ai_summary import _parse_json_or_fallback

        json_with_spaces = json.dumps({
            "resume": "Test    with   multiple    spaces\n\n\nand lines",
            "prix": "  100   €  ",
            "dates": "",
            "conditions_suspensives": "",
            "penalites": "",
            "delais": "",
            "clauses_importantes": []
        })

        result = _parse_json_or_fallback(json_with_spaces)

        assert "    " not in result["resume"]
        assert "   " not in result["prix"]


class TestGroqApiCall:
    """Tests de la fonction _call_groq_chunk"""

    def test_call_groq_success(self, mock_groq_api_success):
        """Test d'un appel API réussi"""
        from technique.services.ai_summary import _call_groq_chunk

        chunk_text = "Test document chunk"
        result = _call_groq_chunk(chunk_text)

        assert mock_groq_api_success.called
        assert "resume" in result
        assert "prix" in result
        assert "clauses_importantes" in result
        assert isinstance(result["clauses_importantes"], list)

    def test_call_groq_with_correct_payload(self, mock_groq_api_success):
        """Test que le payload envoyé est correct"""
        from technique.services.ai_summary import _call_groq_chunk, SYSTEM_CHUNK, MODEL

        chunk_text = "Test chunk"
        _call_groq_chunk(chunk_text)

        call_args = mock_groq_api_success.call_args
        payload = call_args.kwargs['json']

        assert payload['model'] == MODEL
        assert payload['temperature'] == 0.1
        assert payload['max_tokens'] == 900
        assert len(payload['messages']) == 2
        assert payload['messages'][0]['role'] == 'system'
        assert payload['messages'][0]['content'] == SYSTEM_CHUNK
        assert payload['messages'][1]['role'] == 'user'
        assert payload['messages'][1]['content'] == chunk_text

    def test_call_groq_invalid_json_response(self, invalid_json_response):
        """Test avec une réponse JSON invalide de l'API"""
        from technique.services.ai_summary import _call_groq_chunk

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = invalid_json_response
            mock_post.return_value = mock_response

            chunk_text = "Test chunk"
            result = _call_groq_chunk(chunk_text)

            assert "resume" in result
            assert "clauses_importantes" in result


class TestSummarizeDocument:
    """Tests de la fonction principale summarize_document"""

    def test_summarize_empty_document(self):
        """Test avec document vide"""
        from technique.services.ai_summary import summarize_document

        result = summarize_document("")

        assert result["resume"] == ""
        assert result["prix"] == "Non identifié"
        assert result["dates"] == "Non identifié"
        assert result["conditions_suspensives"] == "Non identifié"
        assert result["penalites"] == "Non identifié"
        assert result["delais"] == "Non identifié"
        assert result["clauses_importantes"] == []

    def test_summarize_none_document(self):
        """Test avec document None"""
        from technique.services.ai_summary import summarize_document

        result = summarize_document(None)

        assert result["resume"] == ""
        assert result["prix"] == "Non identifié"

    @patch('time.sleep')
    def test_summarize_short_document(self, mock_sleep, sample_short_text, mock_groq_api_success):
        """Test avec document court (1 seul chunk)"""
        from technique.services.ai_summary import summarize_document

        result = summarize_document(sample_short_text)


        assert mock_groq_api_success.call_count == 1


        assert "resume" in result
        assert "prix" in result
        assert "clauses_importantes" in result
        assert mock_sleep.call_count == 0

    @patch('time.sleep')
    def test_summarize_long_document(self, mock_sleep, sample_long_text, mock_groq_api_success):
        """Test avec document long (plusieurs chunks)"""
        from technique.services.ai_summary import summarize_document

        result = summarize_document(sample_long_text)


        assert mock_groq_api_success.call_count >= 2
        expected_sleeps = mock_groq_api_success.call_count - 1
        assert mock_sleep.call_count == expected_sleeps

    @patch('time.sleep')
    def test_summarize_merges_results(self, mock_sleep, sample_long_text):
        """Test que les résultats de plusieurs chunks sont fusionnés"""
        from technique.services.ai_summary import summarize_document

        responses = [
            {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "resume": "- Info chunk 1",
                            "prix": "100 €",
                            "dates": "01/01/2024",
                            "conditions_suspensives": "Condition 1",
                            "penalites": "Pénalité 1",
                            "delais": "Délai 1",
                            "clauses_importantes": ["- Info chunk 1"]
                        })
                    }
                }]
            },
            {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "resume": "- Info chunk 2",
                            "prix": "200 €",
                            "dates": "02/02/2024",
                            "conditions_suspensives": "Condition 2",
                            "penalites": "Pénalité 2",
                            "delais": "Délai 2",
                            "clauses_importantes": ["- Info chunk 2"]
                        })
                    }
                }]
            }
        ]

        with patch('requests.post') as mock_post:
            mock_responses = []
            for resp in responses:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = resp
                mock_responses.append(mock_response)

            mock_post.side_effect = mock_responses

            result = summarize_document(sample_long_text)


            assert "chunk 1" in result["resume"].lower()
            assert "chunk 2" in result["resume"].lower()
            assert "100" in result["prix"] and "200" in result["prix"]

    @patch('time.sleep')
    def test_summarize_removes_invalid_clauses(self, mock_sleep, sample_short_text):
        """Test que les clauses non présentes dans le resume sont supprimées"""
        from technique.services.ai_summary import summarize_document

        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "resume": "- Clause présente\n- Autre info",
                        "prix": "1000 €",
                        "dates": "",
                        "conditions_suspensives": "",
                        "penalites": "",
                        "delais": "",
                        "clauses_importantes": [
                            "- Clause présente",
                            "- Clause absente"
                        ]
                    })
                }
            }]
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = api_response
            mock_post.return_value = mock_response

            result = summarize_document(sample_short_text)
            assert len(result["clauses_importantes"]) == 1
            assert "- Clause présente" in result["clauses_importantes"]
            assert "- Clause absente" not in result["clauses_importantes"]

    @patch('time.sleep')
    def test_summarize_removes_duplicate_clauses(self, mock_sleep, sample_short_text):
        """Test que les clauses en double sont supprimées"""
        from technique.services.ai_summary import summarize_document

        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "resume": "- Clause 1\n- Clause 2\n- Clause 1",
                        "prix": "",
                        "dates": "",
                        "conditions_suspensives": "",
                        "penalites": "",
                        "delais": "",
                        "clauses_importantes": [
                            "- Clause 1",
                            "- Clause 2",
                            "- Clause 1"
                        ]
                    })
                }
            }]
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = api_response
            mock_post.return_value = mock_response

            result = summarize_document(sample_short_text)
            assert len(result["clauses_importantes"]) == 2
            assert result["clauses_importantes"].count("- Clause 1") == 1

    def test_summarize_truncates_resume(self, sample_short_text):
        """Test que le resume est tronqué à MAX_RESUME_CHARS"""
        from technique.services.ai_summary import summarize_document, MAX_RESUME_CHARS
        long_resume = "A" * (MAX_RESUME_CHARS + 1000)

        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "resume": long_resume,
                        "prix": "",
                        "dates": "",
                        "conditions_suspensives": "",
                        "penalites": "",
                        "delais": "",
                        "clauses_importantes": []
                    })
                }
            }]
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = api_response
            mock_post.return_value = mock_response

            result = summarize_document(sample_short_text)

            assert len(result["resume"]) <= MAX_RESUME_CHARS

    @patch('time.sleep')
    def test_summarize_handles_chunk_error_gracefully(self, mock_sleep, sample_long_text):
        """Test que l'erreur sur un chunk n'empêche pas le traitement des autres"""
        from technique.services.ai_summary import summarize_document

        responses = [
            {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "resume": "- Info chunk 1",
                            "prix": "100 €",
                            "dates": "",
                            "conditions_suspensives": "",
                            "penalites": "",
                            "delais": "",
                            "clauses_importantes": []
                        })
                    }
                }]
            },

            None
        ]

        with patch('requests.post') as mock_post:
            mock_post.side_effect = [
                Mock(status_code=200, json=lambda: responses[0]),
                ConnectionError("Network error")
            ]

            result = summarize_document(sample_long_text)

            assert "chunk 1" in result["resume"].lower()
            assert result["prix"] == "100 €"


class TestIntegration:
    """Tests d'intégration bout-en-bout"""

    @patch('time.sleep')
    def test_full_document_analysis(self, mock_sleep, sample_document_text):
        """Test complet d'analyse d'un document"""
        from technique.services.ai_summary import summarize_document

        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "resume": "- Prix de vente : 250 000 €\n- Dépôt de garantie : 12 500 €\n- Appartement T3\n- Livraison prévue juin 2025\n- Conditions suspensives : prêt et permis",
                        "prix": "250 000 € (prix de vente) + 12 500 € (dépôt 5%)",
                        "dates": "Signature : 15/01/2024 ; Livraison : 30/06/2025 ; Rétractation : 25/01/2024",
                        "conditions_suspensives": "Obtention prêt 200 000 € ; Obtention permis de construire",
                        "penalites": "100 € par jour de retard de livraison",
                        "delais": "Rétractation : 10 jours ; Travaux : 18 mois",
                        "clauses_importantes": [
                            "- Prix de vente : 250 000 €",
                            "- Livraison prévue juin 2025",
                            "- Conditions suspensives : prêt et permis"
                        ]
                    })
                }
            }]
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = api_response
            mock_post.return_value = mock_response

            result = summarize_document(sample_document_text)

            assert "250 000" in result["prix"]
            assert "2024" in result["dates"]
            assert "prêt" in result["conditions_suspensives"].lower()
            assert "100 €" in result["penalites"]
            assert "10 jours" in result["delais"]
            assert len(result["clauses_importantes"]) > 0


class TestEdgeCases:
    """Tests des cas limites"""

    def test_summarize_whitespace_only(self):
        """Test avec document contenant uniquement des espaces"""
        from technique.services.ai_summary import summarize_document

        result = summarize_document("   \n\n\t\t   ")

        assert result["resume"] == ""
        assert result["prix"] == "Non identifié"

    def test_summarize_special_characters(self, sample_short_text):
        """Test avec caractères spéciaux dans le document"""
        from technique.services.ai_summary import summarize_document

        special_text = "Prix : 1€000 € • Date : 01/01/2024 — Clause © importante"

        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "resume": "Document avec caractères spéciaux",
                        "prix": "1€000 €",
                        "dates": "01/01/2024",
                        "conditions_suspensives": "",
                        "penalites": "",
                        "delais": "",
                        "clauses_importantes": []
                    })
                }
            }]
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = api_response
            mock_post.return_value = mock_response

            result = summarize_document(special_text)

            assert "€" in result["prix"]

    def test_empty_api_response_fields(self, sample_short_text):
        """Test avec réponse API contenant des champs vides"""
        from technique.services.ai_summary import summarize_document

        api_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "resume": "",
                        "prix": "",
                        "dates": "",
                        "conditions_suspensives": "",
                        "penalites": "",
                        "delais": "",
                        "clauses_importantes": []
                    })
                }
            }]
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = api_response
            mock_post.return_value = mock_response

            result = summarize_document(sample_short_text)

            assert result["prix"] == "Non identifié"
            assert result["dates"] == "Non identifié"