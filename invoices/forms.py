from django import forms
from uuid import uuid4
from datetime import datetime, time
from django.utils import timezone
from django.db import connection
from django.contrib.auth.models import User

from technique.models import TechnicalProject
from .models import Facture, Entreprise, Fournisseur, Client, PieceJointe, ActeurExterne


def get_enum_labels(enum_name: str) -> list[str]:
    """Retourne la liste des labels d'un type ENUM PostgreSQL."""
    with connection.cursor() as cur:
        cur.execute(f"SELECT unnest(enum_range(NULL::{enum_name}))")
        rows = cur.fetchall()
    return [r[0] for r in rows]

def build_choices(labels: list[str]) -> list[tuple[str, str]]:
    """Construit des tuples (value, label_affiche) pour un <select>."""
    return [(label, label) for label in labels]

def normalize_label(s: str) -> str:
    """Normalisation légère pour comparer proprement des labels."""
    import unicodedata
    import re
    if not s:
        return s
    s_no_acc = ''.join(c for c in unicodedata.normalize('NFD', s)
                       if unicodedata.category(c) != 'Mn')
    s_no_acc = s_no_acc.lower().strip()
    s_no_acc = s_no_acc.replace('_', ' ')
    s_no_acc = re.sub(r'\s+', ' ', s_no_acc)
    return s_no_acc

def best_match(value: str, enum_labels: list[str]) -> str | None:
    """Retourne le label ENUM dont la version normalisée matche la valeur."""
    val_norm = normalize_label(value)
    for lab in enum_labels:
        if normalize_label(lab) == val_norm:
            return lab
    return None


def ensure_dossier_exists(reference: str) -> None:
    """
    Crée une ligne dans "Dossier" si elle n'existe pas encore.
    Respecte l'ENUM 'type_dossier' (colonne 'type').
    Colonnes : reference, type, frais_eng, fais_payes, frais_rest, total_estim, pdf
    """
    if not reference:
        return

    # 1) Valeur valide de l'ENUM type_dossier
    try:
        type_labels = get_enum_labels("type_dossier")
    except Exception:
        type_labels = []

    def pick_default_type(labels: list[str]) -> str | None:
        for pref in ("Technique", "Administratif"):
            x = best_match(pref, labels)
            if x:
                return x
        return labels[0] if labels else None

    type_value = pick_default_type(type_labels)
    if not type_value:
        raise ValueError(
            "Aucune valeur valide pour l’ENUM type_dossier. "
            "Vérifie l’existence du type ENUM 'type_dossier' en base."
        )

    # 2) Upsert minimal
    with connection.cursor() as cur:
        cur.execute('SELECT 1 FROM "Dossier" WHERE reference=%s', [reference])
        if cur.fetchone():
            return
        cur.execute(
            '''
            INSERT INTO "Dossier"(reference, type, frais_eng, frais_payes, frais_rest, total_estim)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            [reference, type_value, 0, 0, 0, 0]
        )


# --- Formulaire ------------------------------------------------------------------

class FactureForm(forms.ModelForm):
    """
    Formulaire de création/édition de facture.

    Attributes:
        fournisseur_input (str): Nom du fournisseur
        client_input (str): Nom du client (entreprise)
        collaborateur (ModelChoiceField): Collaborateur assigné
        echeance (DateField): Date d'échéance
        statut (ChoiceField): Statut de la facture
    """
    fournisseur_input = forms.CharField(label="Fournisseur", required=True)
    client_input = forms.CharField(label="Client (Entreprise)", required=False)

    dossier = forms.ModelChoiceField(
        queryset=TechnicalProject.objects.all(),
        required=True,
        label="Dossier",
    )

    collaborateur = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, groups__name="COLLABORATEUR").order_by('last_name', 'first_name'),
        required=False,
        label="Collaborateur (Assigner)"
    )

    echeance = forms.DateField(
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
        label="Échéance",
    )

    statut = forms.ChoiceField(choices=Facture.STATUS, required=True)

    class Meta:
        model = Facture
        fields = ["dossier", "montant", "statut", "echeance", "titre", "collaborateur"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Statut : utilise directement les choices du modèle
        self.fields["statut"].choices = Facture.STATUS

        # Pré-remplir l'échéance avec la date existante (mode édition)
        if self.instance.echeance:
            try:
                current = timezone.localtime(self.instance.echeance)
            except Exception:
                current = self.instance.echeance
            self.fields["echeance"].initial = current.date()

        # Pré-remplir les champs texte (mode édition)
        if self.instance.pk:
            if self.instance.fournisseur_id:
                self.fields["fournisseur_input"].initial = self.instance.fournisseur_id
            if self.instance.client_id:
                self.fields["client_input"].initial = self.instance.client_id
            if self.instance.dossier_id:
                self.fields["dossier"].initial = self.instance.dossier_id

        # Ajoute la classe CSS Bootstrap à tous les champs
        for field in self.fields.values():
            current_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{current_class} form-control".strip()

    def clean_echeance(self):
        e = self.cleaned_data.get("echeance")
        if not e:
            return e
        # Midi pour éviter les décalages de timezone
        dt = datetime.combine(e, time(12, 0))
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def save(self, commit=True):
        """
        Enregistre la facture avec logique métier :
        - Création auto de l'ID "FAC-XXXXXXXX"
        - Création/récupération du fournisseur et du client
        - Gestion de l'échéance avec timezone
        """
        inst = super().save(commit=False)

        # ----- Fournisseur -----
        f_text = (self.cleaned_data.get("fournisseur_input") or "").strip()
        acteur_f, _ = ActeurExterne.objects.get_or_create(id=f_text)
        fournisseur, _ = Fournisseur.objects.get_or_create(
            id=acteur_f,
            defaults={"nom": f_text},
        )
        inst.fournisseur = fournisseur

        # ----- Client -----
        c_text = (self.cleaned_data.get("client_input") or "").strip() or "DIVERS"
        c_nom = c_text if c_text != "DIVERS" else "Divers"

        acteur_c, _ = ActeurExterne.objects.get_or_create(id=c_text)
        client, _ = Client.objects.get_or_create(id=acteur_c)
        Entreprise.objects.get_or_create(id=client, defaults={"nom": c_nom})
        inst.client = client

        # ----- ID facture auto si nouvelle -----
        if not inst.pk:
            inst.id = f"FAC-{uuid4().hex[:8].upper()}"

        if commit:
            inst.save()

        return inst


# --- Pièce jointe (PDF) ----------------------------------------------------

class PieceJointeForm(forms.ModelForm):
    """
    Formulaire de pièce jointe (PDF uniquement, 10 Mo max).
    """
    fichier = forms.FileField(
        label="Joindre la facture (PDF)",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "application/pdf"}),
    )

    class Meta:
        model = PieceJointe
        fields = ["fichier"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_fichier(self):
        f = self.cleaned_data.get("fichier")
        if not f:
            return f
        valid_types = {"application/pdf", "application/x-pdf", "application/octet-stream"}
        if getattr(f, "content_type", "") not in valid_types and not (f.name or "").lower().endswith(".pdf"):
            raise forms.ValidationError("Le fichier doit être un PDF.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Le fichier dépasse 10 Mo.")
        return f