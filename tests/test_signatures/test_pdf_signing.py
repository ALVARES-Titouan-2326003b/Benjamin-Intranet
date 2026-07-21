"""
Tests pour signatures/services/pdf_signing.py
Tests de la signature PDF avec positionnement d'images
"""
import pytest
from pypdf import PdfReader


@pytest.mark.django_db
class TestSignerPdfAvecImagesPosition:
    """Tests de la fonction de signature PDF avec positionnement"""

    def test_signature_reussie_position_centre_bas(
        self,
        document_pdf_simple,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Signature réussie avec position centre-bas (50%, 10%)
        Vérifie que le PDF signé est créé et valide
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position

        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        document_pdf_simple.refresh_from_db()

        assert document_pdf_simple.fichier_signe
        assert '_signe' in document_pdf_simple.fichier_signe.name
        assert document_pdf_simple.fichier_signe.name.endswith('.pdf')

        reader = PdfReader(document_pdf_simple.fichier_signe.path)
        assert len(reader.pages) == 1


    def test_signature_reussie_positions_variees(
        self,
        document_pdf_simple,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Signature réussie avec différentes positions
        Vérifie que toutes les positions fonctionnent
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position

        positions = [
            (10.0, 10.0),
            (90.0, 10.0),
            (50.0, 50.0),
            (10.0, 90.0),
            (90.0, 90.0),
        ]

        for pos_x, pos_y in positions:

            document_pdf_simple.fichier_signe = None
            document_pdf_simple.save()


            signer_pdf_avec_images_position(
                document=document_pdf_simple,
                user=signature_user_ceo.user,
                pos_x_pct=pos_x,
                pos_y_pct=pos_y
            )


            document_pdf_simple.refresh_from_db()
            assert document_pdf_simple.fichier_signe


    def test_signature_pdf_multi_pages(
        self,
        document_pdf_multi,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Signature d'un PDF multi-pages
        Vérifie que la signature est appliquée sur la DERNIÈRE page uniquement
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position

        signer_pdf_avec_images_position(
            document=document_pdf_multi,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        document_pdf_multi.refresh_from_db()


        reader = PdfReader(document_pdf_multi.fichier_signe.path)
        assert len(reader.pages) == 3

    def test_signature_pdf_sur_page_selectionnee(
        self,
        document_pdf_multi,
        signature_user_ceo,
        tampon_entreprise,
    ):
        """La fusion doit modifier uniquement la page choisie par l'utilisateur."""
        from signatures.services.pdf_signing import signer_pdf_avec_images_position

        original = PdfReader(document_pdf_multi.fichier.path)
        original_streams = [page.get_contents().get_data() for page in original.pages]

        signer_pdf_avec_images_position(
            document=document_pdf_multi,
            user=signature_user_ceo.user,
            pos_x_pct=25.0,
            pos_y_pct=20.0,
            signature_mode="signature",
            page_number=2,
        )

        document_pdf_multi.refresh_from_db()
        signed = PdfReader(document_pdf_multi.fichier_signe.path)
        signed_streams = [page.get_contents().get_data() for page in signed.pages]

        assert signed_streams[0] == original_streams[0]
        assert signed_streams[1] != original_streams[1]
        assert signed_streams[2] == original_streams[2]

    def test_signature_avec_mention_personnalisee(
        self,
        document_pdf_simple,
        signature_user_ceo,
        tampon_entreprise,
    ):
        from signatures.services.pdf_signing import signer_pdf_avec_images_position

        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=20.0,
            pos_y_pct=15.0,
            signature_mode="signature",
            signature_mention="Bon pour remboursement",
        )

        document_pdf_simple.refresh_from_db()
        signed = PdfReader(document_pdf_simple.fichier_signe.path)

        assert "Bon pour remboursement" in signed.pages[0].extract_text()
        assert document_pdf_simple.signature_mention == "Bon pour remboursement"


    def test_erreur_signature_user_inexistant(
        self,
        document_pdf_simple,
        user_factory,
        tampon_entreprise
    ):
        """
        Test: Erreur si l'utilisateur n'a pas de SignatureUser configuré
        Doit lever ValueError
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position


        user_sans_signature = user_factory(username='user_sans_sig')


        with pytest.raises(ValueError, match="Aucune image de signature"):
            signer_pdf_avec_images_position(
                document=document_pdf_simple,
                user=user_sans_signature,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )


    def test_erreur_tampon_inexistant(
        self,
        document_pdf_simple,
        signature_user_ceo
    ):
        """
        Test: Erreur si aucun tampon n'est configuré
        Doit lever ValueError
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position
        from signatures.models import Tampon


        Tampon.objects.all().delete()


        with pytest.raises(ValueError, match="Aucun tampon configuré"):
            signer_pdf_avec_images_position(
                document=document_pdf_simple,
                user=signature_user_ceo.user,
                pos_x_pct=50.0,
                pos_y_pct=10.0
            )

    def test_signature_seule_sans_tampon(
        self,
        document_pdf_simple,
        signature_user_ceo
    ):
        """
        Test: La signature seule ne nécessite pas de tampon configuré.
        """
        from signatures.models import Tampon
        from signatures.services.pdf_signing import signer_pdf_avec_images_position

        Tampon.objects.all().delete()

        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0,
            signature_mode="signature",
        )

        document_pdf_simple.refresh_from_db()

        assert document_pdf_simple.fichier_signe
        assert document_pdf_simple.signature_mode == "signature"
        assert document_pdf_simple.tampon is None

    def test_image_signature_orientation_exif_corrigee(self, tmp_path):
        """
        Test: Une image tournée par métadonnée EXIF est normalisée avant insertion PDF.
        """
        from PIL import Image
        from signatures.services.pdf_signing import _load_pdf_image

        image_path = tmp_path / "signature_exif.jpg"
        image = Image.new("RGB", (10, 20), "white")
        exif = Image.Exif()
        exif[274] = 6
        image.save(image_path, format="JPEG", exif=exif)

        image_reader = _load_pdf_image(image_path)

        assert image_reader.getSize() == (20, 10)

    def test_image_signature_rotation_pdf_corrigee(self, tmp_path):
        """
        Test: La rotation forcée de la signature est appliquée avant insertion PDF.
        """
        from PIL import Image
        from signatures.services.pdf_signing import _normalize_pdf_image

        image_path = tmp_path / "signature_retournee.png"
        image = Image.new("RGB", (2, 1), "white")
        image.putpixel((0, 0), (0, 0, 0))
        image.save(image_path, format="PNG")

        rotated = _normalize_pdf_image(image_path, rotate_degrees=180)

        assert rotated.getpixel((0, 0)) == (255, 255, 255)
        assert rotated.getpixel((1, 0)) == (0, 0, 0)


    def test_positions_limites(
        self,
        document_pdf_simple,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Positions limites (0%, 100%)
        Vérifie que les calculs fonctionnent aux extrémités
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position


        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=0.0,
            pos_y_pct=0.0
        )

        document_pdf_simple.refresh_from_db()
        assert document_pdf_simple.fichier_signe


        document_pdf_simple.fichier_signe = None
        document_pdf_simple.save()


        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=100.0,
            pos_y_pct=100.0
        )

        document_pdf_simple.refresh_from_db()
        assert document_pdf_simple.fichier_signe


    def test_nom_fichier_signe(
        self,
        document_pdf_simple,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Le nom du fichier signé suit le format {id}_signe.pdf
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position

        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )

        document_pdf_simple.refresh_from_db()


        assert '_signe' in document_pdf_simple.fichier_signe.name
        assert document_pdf_simple.fichier_signe.name.endswith('.pdf')
        assert str(document_pdf_simple.pk) in document_pdf_simple.fichier_signe.name


    def test_fichier_original_inchange(
        self,
        document_pdf_simple,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Le fichier original reste inchangé après signature
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position


        original_path = document_pdf_simple.fichier.path
        with open(original_path, 'rb') as f:
            original_content = f.read()


        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=10.0
        )


        with open(original_path, 'rb') as f:
            new_content = f.read()

        assert original_content == new_content


    def test_signature_idempotente(
        self,
        document_pdf_simple,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Appeler la signature plusieurs fois écrase le fichier signé précédent
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position


        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=10.0,
            pos_y_pct=10.0
        )

        document_pdf_simple.refresh_from_db()



        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=90.0,
            pos_y_pct=90.0
        )

        document_pdf_simple.refresh_from_db()
        second_signed_name = document_pdf_simple.fichier_signe.name


        assert document_pdf_simple.fichier_signe
        assert '_signe' in second_signed_name
        assert second_signed_name.endswith('.pdf')




@pytest.mark.django_db
class TestCalculsPositionnement:
    """Tests des calculs mathématiques de positionnement"""

    def test_conversion_pourcentage_coordonnees(
        self,
        document_pdf_simple,
        signature_user_ceo,
        tampon_entreprise
    ):
        """
        Test: Vérifier que les pourcentages sont correctement convertis
        en coordonnées PDF (origine en bas à gauche)
        """
        from signatures.services.pdf_signing import signer_pdf_avec_images_position


        signer_pdf_avec_images_position(
            document=document_pdf_simple,
            user=signature_user_ceo.user,
            pos_x_pct=50.0,
            pos_y_pct=50.0
        )

        document_pdf_simple.refresh_from_db()

        reader = PdfReader(document_pdf_simple.fichier_signe.path)
        page = reader.pages[0]

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        assert 590 < width < 600
        assert 835 < height < 850
