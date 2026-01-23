from signatures.models import Document, HistoriqueSignature
from .pdf_signing import signer_pdf_avec_images_position


def init_workflow(document: Document):
    """
    Initialise le workflow d'un document

    Args:
        document (Document): Document
    """
    HistoriqueSignature.objects.create(
        document=document,
        statut="upload",
        commentaire="Document ajouté",
    )


def lancer_signature(document: Document):
    """
    Enregistre l'envoie d'une signature

    Args:
        document (Document): Document
    """
    HistoriqueSignature.objects.create(
        document=document,
        statut="en_attente",
        commentaire="Document en attente de signature.",
    )


def signer_document_avec_position(document: Document, user, pos_x_pct: float, pos_y_pct: float):
    """
    Signature avec placement interactif

    Args:
        document (Document): Document à signer
        user (User): Utilisateur qui signe le document
        pos_x_pct (float): Position x en pourcentage
        pos_y_pct (float): Position y en pourcentage
    """
    try:
        signer_pdf_avec_images_position(document, user, pos_x_pct, pos_y_pct)
    except Exception as e:
        HistoriqueSignature.objects.create(
            document=document,
            statut="erreur",
            commentaire=f"Erreur lors de la signature : {e}",
        )
        raise

    HistoriqueSignature.objects.create(
        document=document,
        statut="signe",
        commentaire="Document signé après placement manuel.",
    )
