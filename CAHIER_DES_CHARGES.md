# Cahier des charges informatique – Pôle Technique – Benjamin Immobilier

## 1. Contexte et objectifs

Ce document vise à formaliser les besoins d'automatisation, d'IA et de digitalisation pour le pôle technique de Benjamin Immobilier. L'objectif est de fournir des outils intégrés à l'intranet de l'entreprise pour assister les équipes dans le suivi juridique, la lecture documentaire, le classement des courriers, et la gestion budgétaire des projets techniques.

Note de cadrage : les nouveaux besoins exprimés par le pôle technique complètent le périmètre initial. Ils structurent le module autour d'une fiche dossier technique centrale, à laquelle doivent être reliées les briques documents, dates clés, actions à mener, données financières et, lorsque c'est pertinent, les affaires/dossiers existants dans l'intranet.

Points à confirmer avant validation définitive :

- le retrait du typage des documents techniques ;
- les règles d'archivage des dossiers, à valider par le rôle CEO / superadmin ;
- les modalités de convergence avec le dossier administratif dans une logique de dossier unique.

## 2. Socle transversal – Dossiers techniques

### 2.1 Objectif

Faire du dossier technique l'objet central du pôle technique, avec une convergence progressive vers un dossier unique partagé avec le pôle administratif.

Chaque dossier doit pouvoir regrouper les informations métier, les documents, les dates clés, les actions à mener, les éléments financiers et les liens éventuels avec les affaires ou dossiers des autres pôles. L'objectif fonctionnel est d'éviter deux référentiels concurrents entre dossiers techniques et dossiers administratifs : les écrans peuvent rester adaptés à chaque pôle, mais la donnée dossier doit être centralisée autant que possible.

### 2.2 Informations principales du dossier

Chaque dossier technique doit contenir a minima :

- une référence dossier ;
- un nom de dossier ou nom d'affaire ;
- un statut d'avancement ;
- un lien éventuel avec une affaire ou un dossier administratif ;
- les documents associés ;
- les dates clés ;
- les actions à mener ;
- les données financières du dossier ;
- l'historique des modifications.

### 2.3 Création d'un dossier

La création d'un dossier technique doit rester simple et rapide.

Champs attendus lors de la création :

- référence ;
- nom ;
- statut ;
- type.

Les autres informations pourront être ajoutées par la suite depuis la fiche dossier, notamment :

- documents ;
- dates clés ;
- actions à mener ;
- données financières ;
- historique et commentaires.

### 2.4 Statuts des dossiers techniques

Les statuts attendus pour les dossiers techniques sont :

- Étude ;
- Promesse signée ;
- Acquis.

Ces statuts doivent être proposés dans une liste déroulante afin d'éviter les saisies libres et de permettre le filtrage dans les vues de suivi.

Le statut doit pouvoir être modifié depuis la fiche dossier.

### 2.5 Types de dossiers techniques

Les types de dossiers techniques peuvent être conservés si le pôle technique en a l'usage pour filtrer ou organiser les dossiers.

Correction de cadrage : le retrait demandé ne concerne pas les types de dossiers, mais les types de documents.

### 2.6 Archivage des dossiers

La règle attendue est d'archiver les dossiers techniques plutôt que de les supprimer définitivement.

Dans le contexte actuel, Rudy représente le rôle CEO / superadmin. La règle fonctionnelle ne doit donc pas dépendre d'une personne nommée en dur, mais d'un niveau de droit.

Règles attendues :

- l'archivage doit être préféré à toute suppression définitive ;
- un dossier archivé doit rester consultable depuis son historique ou sa fiche, selon les droits de l'utilisateur ;
- un dossier archivé ne doit plus pouvoir être sélectionné lors de la création ou du rattachement d'une facture ;
- un dossier archivé ne doit plus pouvoir être sélectionné lors de la création ou du rattachement d'une activité ;
- l'archivage doit être historisé avec l'utilisateur, la date et, si possible, un commentaire ;
- la suppression définitive éventuelle doit rester exceptionnelle et validée par le CEO / superadmin.

## 3. Module 1 – Assistant IA juridique pour la promotion immobilière

### 3.1 Objectif

Fournir une interface IA capable de répondre aux questions juridiques liées à l'immobilier et à la promotion.

### 3.2 Fonctionnalités

- Recherche et synthèse juridique à partir de documents internes et textes réglementaires.
- Interface en langage naturel pour consultation simple.
- Historique des requêtes par utilisateur.
- Recherche dans les sources officielles lorsque cela est possible, notamment via Légifrance.

### 3.3 Spécifications techniques

- LLM open source (ex. Mistral, LLaMA 3) avec interface type Open Web UI.
- Implémentation RAG avec base documentaire interne.
- Déploiement en local ou sur cloud sécurisé avec authentification interne.
- Étudier l'API Légifrance pour récupérer ou citer les textes officiels pertinents dans les réponses juridiques.
- Prévoir une configuration sécurisée des identifiants API, un mode sandbox si disponible, et une gestion des limites d'appel.

## 4. Module 2 – Lecture, classement et résumé automatique des documents

### 4.1 Objectif

Accélérer la compréhension de documents longs et complexes (contrats de réservation, etc.).

### 4.2 Fonctionnalités

- Upload de documents PDF/DOCX.
- Extraction et résumé automatique structuré.
- Export du résumé en PDF et consultation dans l’intranet.
- Suppression du champ "type de document" pour le pôle technique.
- Liaison obligatoire ou recommandée du document avec un dossier technique.
- Affichage des documents depuis la fiche dossier technique.
- Accès aux documents depuis les vues liées : affaire/dossier, données financières et autres briques pertinentes.

### 4.3 Typage des documents techniques

Le typage des documents techniques doit être retiré du périmètre.

Raison métier : il existe trop de types de documents possibles pour que la liste soit exploitable et maintenable.

Le module documents doit donc privilégier :

- un titre clair ;
- le rattachement au dossier technique ;
- la recherche texte ;
- les résumés automatiques ;
- les dates, montants, clauses ou informations importantes extraites automatiquement ;
- éventuellement des mots-clés libres ou générés automatiquement, sans liste fermée obligatoire.

### 4.4 Spécifications techniques

- API GPT-4 ou équivalent (Hugging Face, Mistral) via token sécurisé.
- Intégration dans l’intranet via formulaire d’upload + restitution formatée.
- Journalisation des analyses avec tri par projet.
- Remplacer progressivement le rattachement texte libre d'un document par un rattachement structuré au dossier technique.
- Retirer le champ de type de document des formulaires, filtres et vues du pôle technique, ou le masquer s'il doit être conservé temporairement pour compatibilité technique.

## 5. Module 3 – Tri automatique des e-mails et pièces jointes

### 5.1 Objectif

Classer automatiquement les e-mails et pièces jointes reçues selon les projets.

### 5.2 Fonctionnalités

- Connexion à la messagerie du pôle technique.
- Classement automatique des e-mails selon mots-clés, émetteur, pièce jointe.
- Association des pièces jointes à un projet dans l’intranet.
- Création ou proposition de documents techniques à partir des pièces jointes pertinentes.
- Rattachement de l'e-mail et de ses pièces jointes au dossier technique concerné.

### 5.3 Spécifications techniques

- Intégration de la solution Emana ou développement sur mesure avec NLP.
- Interface de liaison vers l’intranet pour affichage par projet.
- RGPD : respect du traitement des données personnelles et professionnelles.

## 6. Module 4 – Suivi de paiement des factures

### 6.1 Objectif

Donner au pôle technique une visibilité en temps réel sur les paiements liés aux projets.

### 6.2 Fonctionnalités

- Liste des factures reçues, validées, en attente, payées.
- Filtres par fournisseur, date, projet.
- Téléchargement des justificatifs.
- Accès aux justificatifs et documents financiers depuis la fiche dossier technique.
- Les dossiers archivés ne doivent pas être proposés comme dossiers rattachables à une facture.

### 6.3 Spécifications techniques

- Module intranet alimenté par les données finance disponibles dans l’intranet.
- Les éventuels échanges avec Cegid / Lockimmo relèvent d’un cadrage documentaire futur et ne doivent pas être considérés comme un développement API dans ce périmètre.
- Notification automatique lors des changements de statut.
- Vue tableau + export Excel/PDF.
- L'export CSV n'est pas retenu pour les dossiers techniques et ne doit pas être proposé dans l'interface.

## 7. Module 5 – Données financières du dossier

### 7.1 Objectif

Remplacer les tableaux Excel isolés par une brique financière intégrée à la fiche dossier.

Le point d'entrée principal doit être le dossier technique, plutôt qu'une page nommée "Vue financière". Les informations financières doivent être accessibles depuis le dossier et contribuer à sa lecture globale.

### 7.2 Fonctionnalités

- Saisie des frais engagés / frais payés / frais restants.
- Calcul automatique du total estimé du projet.
- Visualisation par graphique (barres, camemberts).
- Export du budget en PDF.
- Affichage des documents financiers liés au dossier.
- Affichage direct des informations financières depuis la fiche dossier technique.
- Lien avec les briques affaire/dossier lorsque le dossier technique correspond à une affaire suivie ailleurs dans l'intranet.
- Affichage des factures rattachées au dossier et provenant du pôle financier.
- Saisie de dépenses propres au dossier, avec ou sans facture associée.

Une facture est un élément issu du pôle financier. Une dépense est une ligne de suivi du dossier technique : elle peut être liée à une facture existante, mais elle peut aussi être saisie sans facture lorsque la dépense est prévisionnelle, estimative ou non encore facturée.

### 7.3 Spécifications techniques

- Interface web interactive (React/Vue.js).
- Liaison avec la base de données projets et les données finance disponibles.
- Historique des mises à jour par utilisateur.

## 8. Module 6 – Dates clés du dossier

### 8.1 Objectif

Ajouter une brique dédiée aux dates clés du dossier technique afin de centraliser les échéances importantes.

### 8.2 Fonctionnalités

La fiche dossier doit permettre de créer, consulter, modifier et supprimer des dates clés.

Chaque date clé doit contenir :

- un libellé ;
- une date ;
- un commentaire optionnel ;
- un statut optionnel ;
- un lien éventuel avec un document ou une action à mener.

Exemples de dates clés :

- dépôt ou obtention d'un permis ;
- signature de promesse ;
- acquisition ;
- échéance d'étude ;
- date limite de réponse ou de validation ;
- réunion technique importante.

Les dates clés doivent pouvoir être affichées dans la fiche dossier et dans une vue de suivi globale.

## 9. Module 7 – Actions à mener

### 9.1 Objectif

Ajouter au pôle technique une brique d'actions à mener, similaire à une liste de tâches, mais adaptée au suivi technique des dossiers.

### 9.2 Fonctionnalités

Le module doit permettre :

- de créer une action depuis un dossier technique ;
- d'assigner une action à un collaborateur membre du pôle technique ;
- de définir un statut ;
- de définir une priorité ;
- d'ajouter une description ou un commentaire ;
- d'ajouter une date d'échéance si nécessaire ;
- de conserver des actions sans date lorsqu'elles ne correspondent pas à une échéance précise ;
- de filtrer les actions par dossier, collaborateur, statut et priorité.

Statuts proposés pour les actions :

- À faire ;
- En cours ;
- Terminé ;
- Annulé.

Les dates des actions ne doivent pas obligatoirement être liées aux dates clés du dossier. Une action peut exister sans date ou avec une date de suivi propre.

Les dossiers archivés ne doivent pas être proposés comme dossiers rattachables à une action technique.

## 10. Sécurité et évolutivité

- Respect du RGPD et chiffrement des données sensibles.
- Architecture modulaire pour ajouter d’autres fonctions techniques (planning travaux, documents techniques, etc.).
- Documentation technique et formation des utilisateurs.
- Gestion fine des droits sur les dossiers, documents, actions, dates clés et archivages.
- Traçabilité des modifications importantes, notamment sur les dossiers, budgets, documents et archivages.
