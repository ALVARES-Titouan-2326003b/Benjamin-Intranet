# Cahier des charges informatique pole financier et comptabilité – Benjamin Immobilier

**Objectif global :** Modernisation et automatisation des processus du pôle financier et administratif via des outils numériques et intelligents.

Note de cadrage : les nouveaux besoins du pôle finance ajoutent un module de **transmission de factures** accessible à tous les collaborateurs. L’objectif est de centraliser la soumission des factures, d’éviter les envois dispersés par e-mail et de fiabiliser le traitement comptable grâce à des champs structurés, des alertes doublons et des notifications automatiques.

## Point 1 – Suivi des paiements de factures via un intranet

**Objectif :** Permettre aux collaborateurs de consulter en temps réel le statut des factures traitées par le pôle financier.

### Spécifications fonctionnelles

- Création d’un portail intranet web.
- Gestion des rôles :
  - Tout utilisateur connecté : création / transmission de factures et consultation de ses propres factures.
  - Pôle Administratif : création et gestion des dossiers et des sociétés auxquels les factures peuvent être rattachées.
  - Pôle Financier : validation, correction et changement de statut des factures.
  - Superadministrateur : droits complets, dont modification du statut des factures.
- Rudy porte le rôle métier CEO et les pouvoirs de superadministration. Mégane reste membre du pôle administratif et reçoit le rôle transversal Assistante de direction : elle consulte tous les pôles et toutes les factures sans recevoir les privilèges techniques ni les droits de modification du pôle financier.
- Gestion des statuts de factures limitée à : Reçue et En attente.
- Filtres disponibles : par société, dossier / affaire, montant, date, statut et pôle.
- Téléversement obligatoire d'au moins une facture en pièce jointe, avec prise en charge des formats autorisés.
- Notifications automatiques par e-mail ou via Teams/Slack.
- Tri par défaut de la liste des factures selon leur date de création décroissante, avec possibilité d'inverser le tri.

Une nouvelle facture reçoit automatiquement le statut **Reçue**. Son passage au statut **En attente** est réservé au pôle financier et aux superadministrateurs. Les anciens statuts En cours, Payée, Refusée et Archivée sont retirés des formulaires, filtres, tableaux de bord et traitements.

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
- pièce(s) jointe(s) obligatoire(s), avec prise en charge PDF, JPG, PNG et Excel ;
- nom du demandeur ;
- pôle concerné ;
- société concernée ;
- dossier / affaire concerné ;
- priorité de traitement : Normal, Urgent, Critique ;
- commentaire libre à destination de la comptabilité.

La création d’une facture doit être ouverte à n’importe quel utilisateur connecté, sans restriction au seul pôle financier. Le pôle financier et les superadministrateurs conservent en revanche les droits de validation, correction et changement de statut.

Les dossiers archivés ne doivent pas être proposés comme dossiers rattachables à une facture.

Chaque facture doit obligatoirement être rattachée à une société issue du référentiel géré par le pôle administratif. Elle doit également être rattachée soit à un dossier existant, soit à l'option fonctionnelle **Divers**.

La société doit être sélectionnée avant le dossier. Le sélecteur de dossiers ne propose alors que les dossiers rattachés à cette société et le serveur refuse tout couple incohérent. Lorsque l’option **Divers** est utilisée, la société demeure obligatoire.

L'option Divers ne doit pas créer un faux dossier dans le référentiel. Lorsqu'elle est sélectionnée, un commentaire décrivant l'objet de la facture devient obligatoire.

Le formulaire ne doit pas pouvoir être validé sans pièce jointe correspondant à la facture.

### Notifications et circuit d’information

- À chaque création, transmission ou rattachement d’une facture, une notification e-mail doit être envoyée au pôle finance.
- Les superadministrateurs configurés doivent également être destinataires de ces notifications.
- Les destinataires doivent idéalement être configurables afin d’éviter de coder une adresse en dur.
- La notification doit contenir au minimum : fournisseur, numéro de facture, société, dossier / affaire ou mention Divers, montant, échéance, demandeur et lien vers la facture dans l’intranet.
- La facture doit obligatoirement être jointe à l'e-mail envoyé lors de sa création.
- Si la taille de la pièce jointe dépasse la limite autorisée par la messagerie, le système doit signaler l'échec d'envoi et conserver une notification visible pour le pôle finance. Une règle de remplacement par un lien sécurisé pourra être validée ultérieurement.

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
- Prévoir un index et un tri sur la date de création des factures.
- Aucun moteur de relance automatique fondé sur la date d'échéance n'est requis. La date d'échéance reste une information consultable et filtrable.

### Suivi Intranet vers Excel

L'intranet constitue la source officielle. Chaque facture créée ou modifiée dans
l'intranet doit ajouter ou mettre à jour la ligne correspondante dans le
classeur Excel historique. Les champs synchronisés sont ceux du formulaire de
facture et sont rapprochés des colonnes existantes par leur intitulé.

La synchronisation est strictement unidirectionnelle : une modification dans
Excel ne met pas à jour l'intranet. L'identifiant interne de la facture et un
registre masqué permettent de conserver la correspondance même si le numéro de
facture est corrigé. Les colonnes supplémentaires du document sont préservées,
et chaque succès ou erreur est enregistré dans l'historique de la facture.

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

## Point 3 – Dashboard analytique

**Objectif :** Créer une interface de visualisation financière et de suivi des statuts des factures.

### Spécifications fonctionnelles

- Dashboard de visualisation :
  - Factures reçues et factures en attente
  - Répartition et évolution des factures selon les deux statuts retenus
  - Moyenne de traitement
  - Top 5 fournisseurs, dépenses par mois…
  - Évolution mensuelle du nombre de factures et des montants transmis
- Filtres d’analyse :
  - société ;
  - dossier / affaire ;
  - fournisseur ;
  - statut ;
  - période mensuelle.

### Spécifications techniques

- Dashboard : Power BI, Google Data Studio ou interface personnalisée
- Connexion à la base de données de factures
- Hébergement : Cloud sécurisé (type OVH ou AWS)

### Extension IA

- Détection de fournisseurs à risque
- Prévisions budgétaires basées sur les historiques

## Point 4 – Référentiel sociétés

**Objectif :** Centraliser la liste des sociétés utilisées dans les factures, filtres, tableaux de bord et tampons.

### Spécifications fonctionnelles

- La création, la modification et le retrait des sociétés sont transférés au pôle administratif.
- Le pôle finance utilise le référentiel partagé en lecture et pour la sélection dans les formulaires.
- Une société déjà liée à une facture ou à un autre objet métier ne doit pas être supprimée physiquement. Elle doit être retirée des nouvelles sélections tout en restant visible dans l'historique.
- Une société jamais utilisée peut être supprimée définitivement par un utilisateur administratif autorisé.
- Afficher des statistiques par société lorsque les données sont disponibles : nombre de factures, montants transmis et répartition entre les statuts Reçue et En attente.
- Utiliser ce référentiel pour fiabiliser les filtres et les contrôles de doublons.

### Spécifications techniques

- Prévoir un modèle ou référentiel de sociétés réutilisable par les factures, les dossiers et les tampons.
- Conserver une compatibilité avec les factures existantes contenant déjà une société saisie en texte libre.
- Les droits de modification du référentiel sont gérés dans le module administratif.

## Ordre de réalisation recommandé

### Priorité 1 – Rôles et référentiels partagés

- attribuer le rôle CEO à Rudy et le rôle Assistante de direction à Mégane, en séparant lecture transversale et administration technique ;
- utiliser le référentiel de sociétés géré par le pôle administratif ;
- fiabiliser le référentiel partagé des dossiers et ajouter l'option fonctionnelle Divers.

### Priorité 2 – Modèle et règles des factures

- limiter les statuts à Reçue et En attente ;
- rendre obligatoires la société, le dossier ou Divers, et la pièce jointe ;
- rendre le commentaire obligatoire avec l'option Divers ;
- préparer la compatibilité ou la migration des anciennes valeurs de statut.

### Priorité 3 – Parcours de saisie et liste des factures

- adapter l'assistant d'ajout de facture ;
- afficher uniquement les deux statuts retenus ;
- trier par défaut selon la date de création décroissante ;
- adapter les filtres, contrôles de doublons et écrans de détail.

### Priorité 4 – Notifications

- joindre obligatoirement la facture à l'e-mail de création ;
- rendre les destinataires configurables ;
- notifier le pôle finance et les superadministrateurs ;
- gérer explicitement les échecs liés à la taille ou à l'envoi des pièces jointes.

### Priorité 5 – Dashboard

- recalculer les indicateurs à partir des statuts Reçue et En attente ;
- retirer les indicateurs payée, refusée, archivée ou en retard qui ne sont plus alimentés.

### Priorité 6 – Synchronisation Excel

- raccorder le classeur historique à l'intranet ;
- synchroniser les créations et modifications de factures ;
- permettre une resynchronisation complète ou ciblée ;
- conserver l'intranet comme source officielle sans import depuis Excel.

## Documents à collecter (pré-requis)

- Documentation Lockimmo utile aux exports éventuels
- Modèles de signature acceptés par la direction
- Liste des rôles/accès utilisateurs
- Liste des sociétés à proposer dans les formulaires finance
- Liste des dossiers / affaires rattachables à une facture
- Adresse e-mail ou groupe de diffusion du pôle finance
- Adresses ou groupe de notification des superadministrateurs
- Copie du classeur Excel historique et nom de la feuille contenant les factures
