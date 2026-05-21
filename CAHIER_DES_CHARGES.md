# Cahier des charges informatique – Pôle Technique – Benjamin Immobilier

## 1. Contexte et objectifs

Ce document vise à formaliser les besoins d'automatisation, d'IA et de digitalisation pour le pôle technique de Benjamin Immobilier. L'objectif est de fournir des outils intégrés à l'intranet de l'entreprise pour assister les équipes dans le suivi juridique, la lecture documentaire, le classement des courriers, et la gestion budgétaire des projets techniques.

## 2. Module 1 – Assistant IA juridique pour la promotion immobilière

### 2.1 Objectif

Fournir une interface IA capable de répondre aux questions juridiques liées à l'immobilier et à la promotion.

### 2.2 Fonctionnalités

- Recherche et synthèse juridique à partir de documents internes et textes réglementaires.
- Interface en langage naturel pour consultation simple.
- Historique des requêtes par utilisateur.

### 2.3 Spécifications techniques

- LLM open source (ex. Mistral, LLaMA 3) avec interface type Open Web UI.
- Implémentation RAG avec base documentaire interne.
- Déploiement en local ou sur cloud sécurisé avec authentification interne.

## 3. Module 2 – Lecture et résumé automatique des contrats

### 3.1 Objectif

Accélérer la compréhension de documents longs et complexes (contrats de réservation, etc.).

### 3.2 Fonctionnalités

- Upload de documents PDF/DOCX.
- Extraction et résumé automatique structuré.
- Export du résumé en PDF et consultation dans l’intranet.

### 3.3 Spécifications techniques

- API GPT-4 ou équivalent (Hugging Face, Mistral) via token sécurisé.
- Intégration dans l’intranet via formulaire d’upload + restitution formatée.
- Journalisation des analyses avec tri par projet.

## 4. Module 3 – Tri automatique des e-mails et pièces jointes

### 4.1 Objectif

Classer automatiquement les e-mails et pièces jointes reçues selon les projets.

### 4.2 Fonctionnalités

- Connexion à la messagerie du pôle technique.
- Classement automatique des e-mails selon mots-clés, émetteur, pièce jointe.
- Association des pièces jointes à un projet dans l’intranet.

### 4.3 Spécifications techniques

- Intégration de la solution Emana ou développement sur mesure avec NLP.
- API de liaison vers l’intranet pour affichage par projet.
- RGPD : respect du traitement des données personnelles et professionnelles.

## 5. Module 4 – Suivi de paiement des factures

### 5.1 Objectif

Donner au pôle technique une visibilité en temps réel sur les paiements liés aux projets.

### 5.2 Fonctionnalités

- Liste des factures reçues, validées, en attente, payées.
- Filtres par fournisseur, date, projet.
- Téléchargement des justificatifs.

### 5.3 Spécifications techniques

- Module intranet synchronisé avec la base finance (Cegid/Lockimmo si possible).
- Notification automatique lors des changements de statut.
- Vue tableau + export Excel/PDF.

## 6. Module 5 – Vue financière projetée par projet

### 6.1 Objectif

Remplacer les tableaux Excel isolés par un module intranet clair, structuré et collaboratif.

### 6.2 Fonctionnalités

- Saisie des frais engagés / frais payés / frais restants.
- Calcul automatique du total estimé du projet.
- Visualisation par graphique (barres, camemberts).
- Export du budget en PDF.

### 6.3 Spécifications techniques

- Interface web interactive (React/Vue.js).
- Liaison avec base de données projets + API finance.
- Historique des mises à jour par utilisateur.

## 7. Sécurité et évolutivité

- Respect du RGPD et chiffrement des données sensibles.
- Architecture modulaire pour ajouter d’autres fonctions techniques (planning travaux, documents techniques, etc.).
- Documentation technique et formation des utilisateurs.
