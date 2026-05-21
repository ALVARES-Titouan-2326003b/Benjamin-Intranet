# Cahier des charges informatique – Intranet Administratif et Relances Automatisées

## 1. Contexte et objectifs

Dans le cadre de l’amélioration des processus internes de Benjamin Immobilier, ce cahier des charges vise à formaliser les besoins pour la création d’un intranet dédié au suivi administratif et à l’automatisation des relances externes. L’objectif est de centraliser les informations clés, de fluidifier les échanges et de réduire les erreurs et oublis.

## 2. Module 1 : Intranet - Suivi des dates clés

### 2.1 Objectif

Mettre en place une interface web sécurisée permettant de centraliser les dates importantes liées aux activités de promotion, vente, gestion locative, et juridique, avec système de rappel automatisé et planning partagé.

### 2.2 Fonctionnalités attendues

- Interface web accessible sur réseau interne ou hébergement cloud sécurisé.
- Création et gestion des projets par le pôle administratif.
- Tableau de bord par utilisateur avec filtres (type d'activité, client, intervenant externe).
- Vue calendrier mensuelle/semaine avec couleurs par type de dossier.
- Système de rappel automatique par e-mail et/ou notification (SMS, Slack, calendrier).
- Gestion des rôles : administration, secrétaire, juriste, direction.

### 2.3 Contraintes techniques

- Responsive design (mobile/tablette/ordinateur).
- Compatible avec Microsoft Outlook et/ou Google Calendar.
- Authentification sécurisée (SSO ou double authentification si possible).
- Base de données relationnelle (ex. PostgreSQL, MySQL).
- Technologies possibles : Django, Laravel, Node.js, ou plateforme no-code évolutive.

## 3. Module 2 : Automatisation des relances e-mail

### 3.1 Objectif

Automatiser les relances e-mail en cas d'absence de réponse après un premier envoi, notamment pour les interlocuteurs externes (huissiers, avocats, notaires).

### 3.2 Fonctionnalités attendues

- Détection automatique des e-mails envoyés sans réponse après X jours (paramétrable).
- Relance automatique avec contenu personnalisable (modèles selon métier : notaire, avocat, etc.).
- Suivi des relances effectuées avec horodatage et statut (ouvert / répondu / relancé).
- Journal d’activité des relances avec possibilité de modification manuelle.
- Intégration avec l’intranet via API ou module natif.

### 3.3 Contraintes techniques

- Intégration avec serveur mail existant (Microsoft Exchange, Gmail, Outlook).
- Possibilité de gérer les envois via SMTP sécurisé.
- Compatibilité RGPD (stockage et gestion des données personnelles).
- Possibilité de coupler avec outils existants (N8N, Zapier).

## 4. Sécurité et évolutivité

- Respect des normes RGPD pour la gestion des données sensibles.
- Journalisation des accès et modifications.
- Architecture évolutive pour intégrer de futurs modules (ex. assistant IA, dashboard décisionnel).
