# Cahier des charges informatique pole financier et comptabilité – Benjamin Immobilier

**Objectif global :** Modernisation et automatisation des processus du pôle financier et administratif via des outils numériques et intelligents.

## Point 1 – Suivi des paiements de factures via un intranet

**Objectif :** Permettre aux collaborateurs de consulter en temps réel le statut des factures traitées par le pôle financier.

### Spécifications fonctionnelles

- Création d’un portail intranet web.
- Gestion des rôles :
  - Collaborateur : création de factures et consultation de ses propres factures.
  - Pôle Administratif : création et gestion des projets auxquels les factures peuvent être rattachées.
  - Pôle Financier : modification exclusive de l’état des factures.
- Gestion des statuts de factures : Reçue, En cours, Payée, Refusée, Archivées.
- Filtres disponibles : par client, projet, montant, date, statut, service.
- Téléversement de justificatifs et factures PDF.
- Notifications automatiques par e-mail ou via Teams/Slack.

### Spécifications techniques

- Technologies suggérées :
  - Frontend : React.js / Vue.js
  - Backend : Node.js ou Django
  - Base de données : PostgreSQL ou Firebase
  - Authentification : SSO entreprise ou gestion simple par e-mail/mot de passe
- API REST pour intégration future avec outils de facturation.
- Hébergement : cloud (AWS, OVH, ou autre).

### Extension IA (phase 2)

- Assistant conversationnel pour interroger l’état d’une facture.
- Prévision automatique de date probable de paiement via modèle ML.

## Point 2 – Export Lockimmo vers Cegid Quadra au format ASCII

**Objectif :** Automatiser l’exportation des données de factures depuis Lockimmo vers le logiciel Cegid Quadra dans un format ASCII conforme.

### Spécifications fonctionnelles

- Extraction régulière (quotidienne/hebdomadaire) des données de factures depuis Lockimmo.
- Transformation des données au format ASCII attendu par Cegid Quadra.
- Dépôt automatique des fichiers dans un dossier surveillé ou envoi via API à Quadra.
- Tableau de bord de suivi des exports.

### Spécifications techniques

- Technologies suggérées :
  - Script Python (avec pandas) pour traitement et formatage
  - Utilisation des API de Lockimmo (si existante)
- Export ASCII avec règles métier (encodage, padding, séparateurs…)
- Journalisation des opérations (logs, erreurs)
- Interface CLI ou web légère pour déclencher manuellement si besoin

### Extension IA

- Vérification automatique de cohérence entre les champs.
- Alerte en cas de doublon ou anomalie détectée.

## Point 3 – Numérisation de la signature et automatisation du tampon

**Objectif :** Faciliter la validation des documents en remplaçant la signature manuelle du CEO par une signature électronique sécurisée.

### Spécifications fonctionnelles

- Numérisation du tampon entreprise et signature du CEO.
- Intégration d’un workflow de signature électronique certifié.
- Possibilité d’envoyer un document à signer via une interface simple.
- Validation par double authentification du CEO.
- Archivage des documents signés + journal des signatures.

### Spécifications techniques

- Solution SaaS à intégrer : Yousign, DocuSign, Universign, Adobe Sign…
- Intégration API pour automatiser les workflows de signature
- Technologies de l’interface : Bubble.io ou Vue.js/Node.js
- Stockage sécurisé (Cloud privé ou local RGPD)

### Extension IA

- Classification automatique des documents nécessitant une signature via OCR + NLP.

## Point 4 – Dashboard analytique & relances automatisées

**Objectif :** Créer une interface de visualisation financière et un moteur de relance automatisée selon les statuts des factures.

### Spécifications fonctionnelles

- Dashboard de visualisation :
  - Factures en attente, payées, en retard
  - Moyenne de traitement
  - Top 10 fournisseurs, dépenses par mois…
- Système de relances :
  - Relance automatique à J+X selon la date d’échéance
  - Envoi personnalisé (modèle mail ou PDF généré automatiquement)
  - Historique des relances envoyées

### Spécifications techniques

- Dashboard : Power BI, Google Data Studio ou interface personnalisée
- Automatisation : Zapier / Make, ou Node.js / Python + SMTP/API mail
- Connexion à la base de données de factures
- Hébergement : Cloud sécurisé (type OVH ou AWS)

### Extension IA

- Génération de mails personnalisés via IA
- Détection de fournisseurs à risque
- Prévisions budgétaires basées sur les historiques

## Documents à collecter (pré-requis)

- Accès/API de Lockimmo
- Documentation ASCII Cegid Quadra
- Modèles de signature acceptés par la direction
- Liste des rôles/accès utilisateurs
- Modèle de relance actuel utilisé
