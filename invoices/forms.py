from django import forms
from uuid import uuid4
from datetime import datetime, time
from django.utils import timezone
from django.db import connection, models

from technique.models import TechnicalProject
from .models import ActeurExterne, Client, Entreprise, Facture, Fournisseur, PieceJointe, Societe


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
        echeance (DateField): Date d'échéance
        statut (ChoiceField): Statut de la facture
    """
    fournisseur_input = forms.CharField(label="Fournisseur", required=True)

    dossier = forms.ModelChoiceField(
        queryset=TechnicalProject.objects.all().order_by("reference", "name"),
        required=True,
        label="Dossier / affaire concerné",
    )

    echeance = forms.DateField(
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
        label="Échéance de paiement",
    )

    date_facture = forms.DateField(
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
        label="Date de facture",
    )

    statut = forms.ChoiceField(choices=Facture.STATUS, required=True)

    class Meta:
        model = Facture
        fields = [
            "numero_facture",
            "societe",
            "dossier",
            "montant",
            "statut",
            "date_facture",
            "echeance",
            "priorite",
            "commentaire_compta",
            "titre",
        ]
        widgets = {
            "commentaire_compta": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Statut : utilise directement les choices du modèle
        self.fields["statut"].choices = Facture.STATUS
        self.fields["montant"].label = "Montant TTC (€)"
        self.fields["numero_facture"].required = True
        self.fields["societe"].required = True
        active_companies = Societe.objects.filter(is_active=True)
        if self.instance.societe_id:
            active_companies = Societe.objects.filter(
                models.Q(is_active=True) | models.Q(pk=self.instance.societe_id)
            )
        self.fields["societe"].queryset = active_companies.order_by("nom")
        available_projects = TechnicalProject.objects.filter(archived_at__isnull=True)
        if self.instance.dossier_id:
            available_projects = TechnicalProject.objects.filter(
                models.Q(archived_at__isnull=True) | models.Q(pk=self.instance.dossier_id)
            )
        self.fields["dossier"].queryset = available_projects.order_by("reference", "name")

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
            if self.instance.dossier_id:
                self.fields["dossier"].initial = self.instance.dossier_id

        if self.instance.date_facture:
            self.fields["date_facture"].initial = self.instance.date_facture

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
        - Création/récupération du fournisseur et du client technique par défaut
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

        # ----- Client technique par défaut -----
        acteur_c, _ = ActeurExterne.objects.get_or_create(id="DIVERS")
        client, _ = Client.objects.get_or_create(id=acteur_c)
        Entreprise.objects.get_or_create(id=client, defaults={"nom": "Divers"})
        inst.client = client
        if inst.dossier_id:
            inst.affaire = str(inst.dossier)

        # ----- ID facture auto si nouvelle -----
        if not inst.pk:
            inst.id = f"FAC-{uuid4().hex[:8].upper()}"

        if commit:
            inst.save()

        return inst


class FactureFormCollaborateur(FactureForm):
    """
    Formulaire pour les utilisateurs non financiers.
    Ils peuvent créer/modifier leurs propres factures, sans modifier le statut ni le référent.
    """
    
    class Meta(FactureForm.Meta):
        fields = [
            "numero_facture",
            "societe",
            "dossier",
            "montant",
            "date_facture",
            "echeance",
            "priorite",
            "commentaire_compta",
            "titre",
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Supprimer le champ statut pour les collaborateurs
        if 'statut' in self.fields:
            del self.fields['statut']


class SocieteForm(forms.ModelForm):
    class Meta:
        model = Societe
        fields = ["nom", "is_active"]

    def clean_nom(self):
        nom = (self.cleaned_data.get("nom") or "").strip()
        duplicate = Societe.objects.filter(nom__iexact=nom)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("Une société portant ce nom existe déjà.")
        return nom


# --- Pièce jointe (PDF) ----------------------------------------------------

class PieceJointeForm(forms.ModelForm):
    """
    Formulaire de pièce jointe (PDF, image ou Excel, 10 Mo max).
    """
    fichier = forms.FileField(
        label="Joindre la facture",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png,.xls,.xlsx"}),
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
        valid_types = {
            "application/pdf",
            "application/x-pdf",
            "application/octet-stream",
            "image/jpeg",
            "image/png",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        valid_extensions = (".pdf", ".jpg", ".jpeg", ".png", ".xls", ".xlsx")
        if getattr(f, "content_type", "") not in valid_types and not (f.name or "").lower().endswith(valid_extensions):
            raise forms.ValidationError("Le fichier doit être un PDF, JPG, PNG ou Excel.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Le fichier dépasse 10 Mo.")
        return f
