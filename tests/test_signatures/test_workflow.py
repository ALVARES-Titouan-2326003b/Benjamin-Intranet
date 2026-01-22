"""
Tests pour signatures/services/workflow.py
Tests du workflow de signature des documents
"""
import pytest


from signatures.services.workflow import init_workflow




def import_workflow_module():
    """Importe le module workflow de manière flexible"""
    try:
        from signatures.services import workflow
        return workflow
    except ImportError:
        try:
            from signatures import workflow
            return workflow
        except ImportError:
            import sys
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if base_dir not in sys.path:
                sys.path.insert(0, base_dir)
            from signatures.services import workflow
            return workflow




@pytest.mark.django_db
class TestInitWorkflow:
    """Tests de la fonction init_workflow()"""

    def test_init_workflow_cree_historique_upload(self, document_workflow):
        """
        Test: init_workflow() crée bien une entrée d'historique "upload"
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        assert HistoriqueSignature.objects.count() == 0

        workflow.init_workflow(document_workflow)

        assert HistoriqueSignature.objects.count() == 1

        historique = HistoriqueSignature.objects.first()
        assert historique.document == document_workflow
        assert historique.statut == "upload"
        assert historique.commentaire == "Document ajouté"


    def test_init_workflow_idempotent(self, document_workflow):
        """
        Test: Appeler init_workflow() plusieurs fois crée plusieurs entrées
        (pas idempotent - c'est voulu pour tracer chaque action)
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        workflow.init_workflow(document_workflow)
        assert HistoriqueSignature.objects.count() == 1

        workflow.init_workflow(document_workflow)
        assert HistoriqueSignature.objects.count() == 2

        historiques = HistoriqueSignature.objects.all()
        for h in historiques:
            assert h.statut == "upload"




@pytest.mark.django_db
class TestLancerSignature:
    """Tests de la fonction lancer_signature()"""

    def test_lancer_signature_cree_historique_en_attente(self, document_workflow):
        """
        Test: lancer_signature() crée une entrée "en_attente"
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        assert HistoriqueSignature.objects.count() == 0

        workflow.lancer_signature(document_workflow)

        assert HistoriqueSignature.objects.count() == 1

        historique = HistoriqueSignature.objects.first()
        assert historique.document == document_workflow
        assert historique.statut == "en_attente"
        assert "attente de signature" in historique.commentaire.lower()


    def test_workflow_complet_upload_puis_lancer(self, document_workflow):
        """
        Test: Workflow typique - init puis lancer
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        workflow.init_workflow(document_workflow)
        workflow.lancer_signature(document_workflow)

        assert HistoriqueSignature.objects.count() == 2

        historiques = HistoriqueSignature.objects.order_by('date_action')

        assert historiques[0].statut == "upload"

        assert historiques[1].statut == "en_attente"


@pytest.mark.django_db
class TestSignerDocumentAvecPosition:
    """Tests de la fonction signer_document_avec_position()"""

    def test_signature_reussie_cree_historique_signe(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Signature réussie crée un historique "signe"
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        workflow.signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        assert HistoriqueSignature.objects.count() == 1

        historique = HistoriqueSignature.objects.first()
        assert historique.document == document_workflow
        assert historique.statut == "signe"
        assert "signé" in historique.commentaire.lower()
        assert "placement manuel" in historique.commentaire.lower()


    def test_signature_erreur_cree_historique_erreur(
        self,
        document_workflow,
        user_factory,
        tampon_entreprise
    ):
        """
        Test: Erreur lors de la signature crée un historique "erreur"
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        user_sans_signature = user_factory(username='user_sans_sig')

        with pytest.raises(ValueError):
            workflow.signer_document_avec_position(
                document=document_workflow,
                user=user_sans_signature,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        assert HistoriqueSignature.objects.count() == 1

        historique = HistoriqueSignature.objects.first()
        assert historique.document == document_workflow
        assert historique.statut == "erreur"
        assert "Erreur lors de la signature" in historique.commentaire


    def test_workflow_complet_avec_signature(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Workflow complet - init → lancer → signer
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        workflow.init_workflow(document_workflow)
        workflow.lancer_signature(document_workflow)
        workflow.signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        assert HistoriqueSignature.objects.count() == 3

        historiques = HistoriqueSignature.objects.order_by('date_action')

        assert historiques[0].statut == "upload"
        assert historiques[1].statut == "en_attente"
        assert historiques[2].statut == "signe"


    def test_signature_document_verifie_fichier_signe_cree(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Après signature, le fichier signé doit être créé
        """
        workflow = import_workflow_module()

        assert not document_workflow.fichier_signe

        workflow.signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        document_workflow.refresh_from_db()
        assert document_workflow.fichier_signe
        assert '_signe' in document_workflow.fichier_signe.name
        assert document_workflow.fichier_signe.name.endswith('.pdf')


@pytest.mark.django_db
class TestGestionErreurs:
    """Tests de la gestion d'erreurs dans le workflow"""

    def test_erreur_tampon_manquant_trace_historique(
        self,
        document_workflow,
        signature_user_ceo
    ):
        """
        Test: Si le tampon est manquant, l'erreur est tracée
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature, Tampon

        Tampon.objects.all().delete()

        with pytest.raises(ValueError, match="Aucun tampon"):
            workflow.signer_document_avec_position(
                document=document_workflow,
                user=signature_user_ceo.user,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        historique = HistoriqueSignature.objects.first()
        assert historique.statut == "erreur"
        assert "Aucun tampon" in historique.commentaire


    def test_erreur_signature_user_manquant_trace_historique(
        self,
        document_workflow,
        user_factory,
        tampon_entreprise
    ):
        """
        Test: Si SignatureUser est manquant, l'erreur est tracée
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        user_sans_sig = user_factory(username='no_sig_user')

        with pytest.raises(ValueError, match="Aucune image de signature"):
            workflow.signer_document_avec_position(
                document=document_workflow,
                user=user_sans_sig,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        historique = HistoriqueSignature.objects.first()
        assert historique.statut == "erreur"
        assert "Aucune image de signature" in historique.commentaire


    def test_multiple_erreurs_cree_multiple_historiques(
        self,
        document_workflow,
        user_factory,
        tampon_entreprise
    ):
        """
        Test: Plusieurs tentatives échouées créent plusieurs historiques d'erreur
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        user_sans_sig = user_factory(username='no_sig_user')

        with pytest.raises(ValueError):
            workflow.signer_document_avec_position(
                document=document_workflow,
                user=user_sans_sig,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        with pytest.raises(ValueError):
            workflow.signer_document_avec_position(
                document=document_workflow,
                user=user_sans_sig,
                pos_x_pct=70.0,
                pos_y_pct=20.0
            )

        assert HistoriqueSignature.objects.count() == 2

        historiques = HistoriqueSignature.objects.all()
        for h in historiques:
            assert h.statut == "erreur"

@pytest.mark.django_db
class TestWorkflowIntegration:
    """Tests d'intégration du workflow complet"""

    def test_scenario_nominal_complet(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Scénario nominal complet du début à la fin
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature


        workflow.init_workflow(document_workflow)

        workflow.lancer_signature(document_workflow)

        workflow.signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        assert HistoriqueSignature.objects.count() == 3

        historiques = list(HistoriqueSignature.objects.order_by('date_action'))
        assert historiques[0].statut == "upload"
        assert historiques[1].statut == "en_attente"
        assert historiques[2].statut == "signe"

        document_workflow.refresh_from_db()
        assert document_workflow.fichier_signe

        assert document_workflow.fichier

    def test_scenario_avec_erreur_puis_reussite(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise,
        user_factory
    ):
        """
        Test: Tentative échouée suivie d'une tentative réussie
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        workflow.init_workflow(document_workflow)

        workflow.lancer_signature(document_workflow)

        user_sans_sig = user_factory(username='temp_user')
        with pytest.raises(ValueError):
            workflow.signer_document_avec_position(
                document=document_workflow,
                user=user_sans_sig,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        workflow.signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        assert HistoriqueSignature.objects.count() == 4

        historiques = list(HistoriqueSignature.objects.order_by('date_action'))
        assert historiques[0].statut == "upload"
        assert historiques[1].statut == "en_attente"
        assert historiques[2].statut == "erreur"
        assert historiques[3].statut == "signe"

        document_workflow.refresh_from_db()
        assert document_workflow.fichier_signe


    def test_historique_conserve_ordre_chronologique(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: L'historique conserve l'ordre chronologique
        """
        workflow = import_workflow_module()
        from signatures.models import HistoriqueSignature

        workflow.init_workflow(document_workflow)
        workflow.lancer_signature(document_workflow)
        workflow.signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        historiques = list(HistoriqueSignature.objects.order_by('date_action'))

        for i in range(len(historiques) - 1):
            assert historiques[i].date_action <= historiques[i + 1].date_action


        assert HistoriqueSignature.objects.count() == 0

        init_workflow(document_workflow)

        assert HistoriqueSignature.objects.count() == 1

        historique = HistoriqueSignature.objects.first()
        assert historique.document == document_workflow
        assert historique.statut == "upload"
        assert historique.commentaire == "Document ajouté"


    def test_init_workflow_idempotent(self, document_workflow):
        """
        Test: Appeler init_workflow() plusieurs fois crée plusieurs entrées
        (pas idempotent - c'est voulu pour tracer chaque action)
        """
        from signatures.services.workflow import init_workflow
        from signatures.models import HistoriqueSignature

        init_workflow(document_workflow)
        assert HistoriqueSignature.objects.count() == 1

        init_workflow(document_workflow)
        assert HistoriqueSignature.objects.count() == 2

        historiques = HistoriqueSignature.objects.all()
        for h in historiques:
            assert h.statut == "upload"


@pytest.mark.django_db
class TestLancerSignature:
    """Tests de la fonction lancer_signature()"""

    def test_lancer_signature_cree_historique_en_attente(self, document_workflow):
        """
        Test: lancer_signature() crée une entrée "en_attente"
        """
        from signatures.services.workflow import lancer_signature
        from signatures.models import HistoriqueSignature

        assert HistoriqueSignature.objects.count() == 0
        lancer_signature(document_workflow)
        assert HistoriqueSignature.objects.count() == 1

        historique = HistoriqueSignature.objects.first()
        assert historique.document == document_workflow
        assert historique.statut == "en_attente"
        assert "attente de signature" in historique.commentaire.lower()


    def test_workflow_complet_upload_puis_lancer(self, document_workflow):
        """
        Test: Workflow typique - init puis lancer
        """
        from signatures.services.workflow import init_workflow, lancer_signature
        from signatures.models import HistoriqueSignature

        init_workflow(document_workflow)
        lancer_signature(document_workflow)

        assert HistoriqueSignature.objects.count() == 2

        historiques = HistoriqueSignature.objects.order_by('date_action')

        assert historiques[0].statut == "upload"

        assert historiques[1].statut == "en_attente"

@pytest.mark.django_db
class TestSignerDocumentAvecPosition:
    """Tests de la fonction signer_document_avec_position()"""

    def test_signature_reussie_cree_historique_signe(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Signature réussie crée un historique "signe"
        """
        from signatures.services.workflow import signer_document_avec_position
        from signatures.models import HistoriqueSignature

        signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        assert HistoriqueSignature.objects.count() == 1

        historique = HistoriqueSignature.objects.first()
        assert historique.document == document_workflow
        assert historique.statut == "signe"
        assert "signé" in historique.commentaire.lower()
        assert "placement manuel" in historique.commentaire.lower()


    def test_signature_erreur_cree_historique_erreur(
        self,
        document_workflow,
        user_factory,
        tampon_entreprise
    ):
        """
        Test: Erreur lors de la signature crée un historique "erreur"
        """
        from signatures.services.workflow import signer_document_avec_position
        from signatures.models import HistoriqueSignature

        user_sans_signature = user_factory(username='user_sans_sig')

        with pytest.raises(ValueError):
            signer_document_avec_position(
                document=document_workflow,
                user=user_sans_signature,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        assert HistoriqueSignature.objects.count() == 1

        historique = HistoriqueSignature.objects.first()
        assert historique.document == document_workflow
        assert historique.statut == "erreur"
        assert "Erreur lors de la signature" in historique.commentaire


    def test_workflow_complet_avec_signature(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Workflow complet - init → lancer → signer
        """
        from signatures.services.workflow import (
            init_workflow,
            lancer_signature,
            signer_document_avec_position
        )
        from signatures.models import HistoriqueSignature

        init_workflow(document_workflow)
        lancer_signature(document_workflow)
        signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        assert HistoriqueSignature.objects.count() == 3

        historiques = HistoriqueSignature.objects.order_by('date_action')

        assert historiques[0].statut == "upload"
        assert historiques[1].statut == "en_attente"
        assert historiques[2].statut == "signe"


@pytest.mark.django_db
class TestGestionErreurs:
    """Tests de la gestion d'erreurs dans le workflow"""

    def test_erreur_tampon_manquant_trace_historique(
        self,
        document_workflow,
        signature_user_ceo
    ):
        """
        Test: Si le tampon est manquant, l'erreur est tracée
        """
        from signatures.services.workflow import signer_document_avec_position
        from signatures.models import HistoriqueSignature, Tampon

        Tampon.objects.all().delete()

        with pytest.raises(ValueError, match="Aucun tampon"):
            signer_document_avec_position(
                document=document_workflow,
                user=signature_user_ceo.user,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        historique = HistoriqueSignature.objects.first()
        assert historique.statut == "erreur"
        assert "Aucun tampon" in historique.commentaire


    def test_erreur_signature_user_manquant_trace_historique(
        self,
        document_workflow,
        user_factory,
        tampon_entreprise
    ):
        """
        Test: Si SignatureUser est manquant, l'erreur est tracée
        """
        from signatures.services.workflow import signer_document_avec_position
        from signatures.models import HistoriqueSignature

        user_sans_sig = user_factory(username='no_sig_user')

        with pytest.raises(ValueError, match="Aucune image de signature"):
            signer_document_avec_position(
                document=document_workflow,
                user=user_sans_sig,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        historique = HistoriqueSignature.objects.first()
        assert historique.statut == "erreur"
        assert "Aucune image de signature" in historique.commentaire


    def test_multiple_erreurs_cree_multiple_historiques(
        self,
        document_workflow,
        user_factory,
        tampon_entreprise
    ):
        """
        Test: Plusieurs tentatives échouées créent plusieurs historiques d'erreur
        """
        from signatures.services.workflow import signer_document_avec_position
        from signatures.models import HistoriqueSignature

        user_sans_sig = user_factory(username='no_sig_user')

        with pytest.raises(ValueError):
            signer_document_avec_position(
                document=document_workflow,
                user=user_sans_sig,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        with pytest.raises(ValueError):
            signer_document_avec_position(
                document=document_workflow,
                user=user_sans_sig,
                pos_x_pct=70.0,
                pos_y_pct=20.0
            )

        assert HistoriqueSignature.objects.count() == 2

        historiques = HistoriqueSignature.objects.all()
        for h in historiques:
            assert h.statut == "erreur"


@pytest.mark.django_db
class TestWorkflowIntegration:
    """Tests d'intégration du workflow complet"""

    def test_scenario_nominal_complet(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Scénario nominal complet du début à la fin
        """
        from signatures.services.workflow import (
            init_workflow,
            lancer_signature,
            signer_document_avec_position
        )
        from signatures.models import HistoriqueSignature

        init_workflow(document_workflow)

        lancer_signature(document_workflow)

        signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )


        assert HistoriqueSignature.objects.count() == 3

        historiques = list(HistoriqueSignature.objects.order_by('date_action'))
        assert historiques[0].statut == "upload"
        assert historiques[1].statut == "en_attente"
        assert historiques[2].statut == "signe"

        document_workflow.refresh_from_db()
        assert document_workflow.fichier_signe

        assert document_workflow.fichier


    def test_scenario_avec_erreur_puis_reussite(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise,
        user_factory
    ):
        """
        Test: Tentative échouée suivie d'une tentative réussie
        """
        from signatures.services.workflow import (
            init_workflow,
            lancer_signature,
            signer_document_avec_position
        )
        from signatures.models import HistoriqueSignature

        init_workflow(document_workflow)

        lancer_signature(document_workflow)

        user_sans_sig = user_factory(username='temp_user')
        with pytest.raises(ValueError):
            signer_document_avec_position(
                document=document_workflow,
                user=user_sans_sig,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

        signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        assert HistoriqueSignature.objects.count() == 4

        historiques = list(HistoriqueSignature.objects.order_by('date_action'))
        assert historiques[0].statut == "upload"
        assert historiques[1].statut == "en_attente"
        assert historiques[2].statut == "erreur"
        assert historiques[3].statut == "signe"

        document_workflow.refresh_from_db()
        assert document_workflow.fichier_signe


    def test_historique_conserve_ordre_chronologique(
        self,
        document_workflow,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: L'historique conserve l'ordre chronologique
        """
        from signatures.services.workflow import (
            init_workflow,
            lancer_signature,
            signer_document_avec_position
        )
        from signatures.models import HistoriqueSignature

        init_workflow(document_workflow)
        lancer_signature(document_workflow)
        signer_document_avec_position(
            document=document_workflow,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        historiques = list(HistoriqueSignature.objects.order_by('date_action'))

        for i in range(len(historiques) - 1):
            assert historiques[i].date_action <= historiques[i + 1].date_action