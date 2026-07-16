# Cahier des charges informatique pole financier et comptabilité – Benjamin Immobilier

**Objectif global :** Modernisation et automatisation des processus du pôle financier et administratif via des outils numériques et intelligents.

Note de cadrage : les nouveaux besoins du pôle finance ajoutent un module de **transmission de factures** accessible à tous les collaborateurs. L’objectif est de centraliser la soumission des factures, d’éviter les envois dispersés par e-mail et de fiabiliser le traitement comptable grâce à des champs structurés, des alertes doublons et des notifications automatiques.

## Point 1 – Suivi des paiements de factures via un intranet

**Objectif :** Permettre aux collaborateurs de consulter en temps réel le statut des factures traitées par le pôle financier.

### Spécifications fonctionnelles

- Création d’un portail intranet web.
- Gestion des rôles :
  - Tout utilisateur connecté : création / transmission de factures et consultation de ses propres factures.
  - Pôle Administratif : création et gestion des projets auxquels les factures peuvent être rattachées.
  - Pôle Financier : validation, correction, changement de statut, paiement et archivage des factures.
  - CEO / superadmin : droits complets, dont modification du statut des factures.
- Gestion des statuts de factures : Reçue, En cours, Payée, Refusée, Archivées.
- Filtres disponibles : par société, dossier / affaire, montant, date, statut, service.
- Téléversement de justificatifs et factures PDF.
- Notifications automatiques par e-mail ou via Teams/Slack.

### Transmission de factures

Le portail doit proposer un parcours dédié à la transmission de factures, sous forme d’assistant en plusieurs étapes :

1. Facture : informations principales et pièces jointes.
2. Contexte : affectation interne, société concernée, dossier / affaire concerné et commentaire pour la comptabilité.
3. Validation : récapitulatif avant envoi.

Les champs attendus pour une facture sont notamment :

- prestataire / fournisseur ;
- numéro de facture ;
- date de facture ;
- montant TTC ;
- échéance de paiement ;
- date de soumission automatique ;
- pièce(s) jointe(s), avec prise en charge PDF, JPG, PNG et Excel ;
- nom du demandeur ;
- service / département du demandeur ;
- société concernée ;
- dossier / affaire concerné ;
- priorité de traitement : Normal, Urgent, Critique ;
- commentaire libre à destination de la comptabilité.

La création d’une facture doit être ouverte à n’importe quel utilisateur connecté, sans restriction au seul pôle financier. Le pôle financier et le CEO / superadmin conservent en revanche les droits de validation, correction, changement de statut, paiement et archivage.

Les dossiers archivés ne doivent pas être proposés comme dossiers rattachables à une facture.

### Notifications et circuit d’information

- À chaque création, transmission ou rattachement d’une facture, une notification e-mail doit être envoyée au pôle finance.
- Rudy doit également être destinataire de ces notifications.
- Les destinataires doivent idéalement être configurables afin d’éviter de coder une adresse en dur.
- La notification doit contenir au minimum : fournisseur, numéro de facture, société, dossier / affaire, montant, échéance, demandeur et lien vers la facture dans l’intranet.

### Contrôle des doublons

Le système doit alerter l’utilisateur et le pôle finance lorsqu’une facture potentiellement déjà existante est détectée.

Les critères de détection de doublon sont :

- même société ;
- même dossier / affaire ;
- même montant TTC ;
- même numéro de facture.

L’alerte doit intervenir dès la saisie ou au plus tard avant la validation finale. Elle ne doit pas forcément bloquer l’envoi, mais doit demander une confirmation explicite et tracer l’alerte pour le pôle finance.

### Spécifications techniques

- Technologies suggérées :
  - Frontend : React.js / Vue.js
  - Backend : Node.js ou Django
  - Base de données : PostgreSQL ou Firebase
  - Authentification : SSO entreprise ou gestion simple par e-mail/mot de passe
- Interfaces d’échange à documenter pour une éventuelle intégration future avec les outils de facturation.
- Hébergement : cloud (AWS, OVH, ou autre).

### Extension IA (phase 2)

- Assistant conversationnel pour interroger l’état d’une facture.
- Prévision automatique de date probable de paiement via modèle ML.

## Point 2 – Numérisation de la signature et automatisation du tampon

**Objectif :** Faciliter la validation des documents en remplaçant la signature manuelle du CEO par une signature électronique sécurisée.

### Spécifications fonctionnelles

- Numérisation du tampon entreprise et signature du CEO.
- Intégration d’un workflow de signature électronique certifié.
- Possibilité d’envoyer un document à signer via une interface simple.
- Validation par double authentification du CEO.
- Archivage des documents signés + journal des signatures.

### Spécifications techniques

- Solution SaaS à intégrer : Yousign, DocuSign, Universign, Adobe Sign…
- Intégration à une solution externe de signature à étudier ultérieurement si le besoin est confirmé.
- Technologies de l’interface : Bubble.io ou Vue.js/Node.js
- Stockage sécurisé (Cloud privé ou local RGPD)

### Extension IA

- Classification automatique des documents nécessitant une signature via OCR + NLP.

## Point 3 – Dashboard analytique & relances automatisées

**Objectif :** Créer une interface de visualisation financière et un moteur de relance automatisée selon les statuts des factures.

### Spécifications fonctionnelles

- Dashboard de visualisation :
  - Factures en attente, payées, en retard
  - Moyenne de traitement
  - Top 5 fournisseurs, dépenses par mois…
  - Évolution mensuelle des factures et montants engagés / payés
- Système de relances :
  - Relance automatique à J+X selon la date d’échéance
  - Envoi personnalisé (modèle mail ou PDF généré automatiquement)
  - Historique des relances envoyées
- Filtres d’analyse :
  - société ;
  - dossier / affaire ;
  - fournisseur ;
  - statut ;
  - période mensuelle.

### Spécifications techniques

- Dashboard : Power BI, Google Data Studio ou interface personnalisée
- Automatisation : Zapier / Make, ou Node.js / Python + SMTP / service mail
- Connexion à la base de données de factures
- Hébergement : Cloud sécurisé (type OVH ou AWS)

### Extension IA

- Génération de mails personnalisés via IA
- Détection de fournisseurs à risque
- Prévisions budgétaires basées sur les historiques

## Point 4 – Référentiel sociétés

**Objectif :** Centraliser la liste des sociétés utilisées dans les factures, filtres, tableaux de bord et tampons.

### Spécifications fonctionnelles

- Prévoir une liste de sociétés proposée dans les formulaires finance.
- Permettre le pré-enregistrement d’une société afin d’éviter les saisies libres incohérentes.
- Étudier une section dédiée aux sociétés dans le pôle finance.
- Afficher des statistiques par société lorsque les données sont disponibles : nombre de factures, montants engagés, montants payés, factures en retard et répartition par statut.
- Utiliser ce référentiel pour fiabiliser les filtres et les contrôles de doublons.

### Spécifications techniques

- Prévoir un modèle ou référentiel de sociétés réutilisable par les factures, les dossiers et les tampons.
- Conserver une compatibilité avec les factures existantes contenant déjà une société saisie en texte libre.

## Documents à collecter (pré-requis)

- Documentation Lockimmo utile aux exports éventuels
- Modèles de signature acceptés par la direction
- Liste des rôles/accès utilisateurs
- Modèle de relance actuel utilisé
- Liste des sociétés à proposer dans les formulaires finance
- Liste des dossiers / affaires rattachables à une facture
- Adresse e-mail ou groupe de diffusion du pôle finance
- Adresse e-mail de Rudy pour les notifications finance
