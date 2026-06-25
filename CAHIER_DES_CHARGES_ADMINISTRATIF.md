# Cahier des charges informatique – Pôle Administratif Benjamin Immobilier

## 1. Contexte et objectifs

Dans le cadre de l’amélioration des processus internes de Benjamin Immobilier, ce cahier des charges formalise les besoins du pôle administratif pour l’intranet interne.

L’objectif principal est de centraliser le suivi des dossiers administratifs liés aux opérations immobilières, afin de remplacer les suivis dispersés dans des tableaux Excel et de donner une vision claire de l’avancement de chaque affaire.

Le module administratif doit permettre de suivre les dossiers de vente et d’acquisition, les dates importantes, les activités associées, les signatures et les relances externes.

Ce cahier des charges met à jour l’ancien besoin initial qui parlait principalement de suivi de projets et de relances automatisées. La logique métier attendue est désormais centrée sur la notion de **dossier administratif**.

Note de cadrage : les arbitrages ci-dessous constituent une version de travail. Ils devront être confirmés avec les personnes concernées du pôle administratif avant validation définitive.

## 2. Périmètre du pôle administratif

Le pôle administratif concerne principalement les activités suivantes :

- activité de marchand de biens ;
- activité de promotion immobilière ;
- suivi des ventes ;
- suivi des acquisitions ;
- suivi des dates clés administratives ;
- suivi des activités internes liées aux dossiers ;
- suivi des signatures ;
- relances auprès des interlocuteurs externes.

Le module doit être conçu pour permettre aux collaborateurs du pôle administratif de travailler à partir d’un tableau de suivi clair, tout en conservant une fiche détaillée pour chaque dossier.

## 3. Module 1 : Gestion des dossiers administratifs

### 3.1 Objectif

Mettre en place un module permettant de créer, consulter, modifier et suivre des dossiers administratifs liés aux affaires immobilières de Benjamin Immobilier.

Le terme **Projet** doit être remplacé par le terme **Dossier** dans l’interface, les menus, les formulaires et les vues concernées.

État actuel : la structure des dossiers administratifs est considérée comme implémentée dans le code. Les évolutions restantes concernent principalement les exports, imports, rappels et validations métier.

### 3.2 Types de dossiers

Chaque dossier doit pouvoir être classé selon son type :

- Vente ;
- Acquisition.

Chaque dossier doit également pouvoir être rattaché à une activité métier :

- Marchand de biens ;
- Promotion immobilière.

### 3.3 États du dossier

Chaque dossier doit disposer d’un état administratif permettant de suivre son avancement.

États minimums attendus :

- En cours de promesse ;
- Vendu ;
- Acheté.

États complémentaires à confirmer avec le pôle administratif :

- En attente ;
- Signé ;
- Annulé ;
- Archivé.

Les états doivent être gérés avec une liste déroulante afin d’éviter les erreurs de saisie.

### 3.4 Catégories de dossiers

Les dossiers devront être classés selon les catégories transmises par Mégane.

État actuel :

- les catégories sont implémentées dans le code ;
- l’association d’une catégorie à chaque dossier est prévue ;
- la recherche, le filtrage et l’affichage par catégorie sont prévus dans l’interface ;
- la liste définitive reste à confirmer avec le pôle administratif.

### 3.5 Informations à stocker sur un dossier

La fiche dossier doit reprendre les informations présentes dans le tableau de suivi administratif actuel.

Champs attendus :

| Champ | Description |
|---|---|
| Affaire | Nom ou référence de l’affaire |
| Lot / étage | Lot, étage ou bâtiment concerné |
| Adresse du bien | Adresse complète du bien immobilier |
| Vendeur | Nom du vendeur |
| Bénéficiaire | Nom du bénéficiaire |
| Locataire | Locataire concerné, si applicable |
| État | État administratif du dossier |
| Date de promesse | Date de signature ou de prévision de la promesse |
| Négociation externe | Information liée à une négociation externe |
| Frais | Frais liés au dossier |
| Prix | Prix de vente ou d’acquisition |
| DG | Champ à confirmer métier, probablement dépôt de garantie |
| Date DG | Date associée au DG |
| CS prêt | Condition suspensive liée au prêt |
| Date CS prêt | Date associée à la condition suspensive de prêt |
| Date de réitération | Date prévue ou réalisée de réitération |
| Acte | Information ou statut lié à l’acte |

Les champs de date doivent être enregistrés sous forme de dates et non sous forme de texte.  
Les champs financiers doivent être enregistrés sous forme de montants afin de permettre des tris, calculs et exports fiables.

### 3.6 Fiche détail d’un dossier

Chaque dossier doit disposer d’une page détail permettant de consulter :

- les informations principales du dossier ;
- son type ;
- son activité métier ;
- sa catégorie ;
- son état ;
- ses dates clés ;
- ses activités associées ;
- ses documents ;
- ses signatures ;
- son historique de modifications ;
- ses relances éventuelles.

## 4. Module 2 : Tableau de suivi administratif

### 4.1 Objectif

Créer une vue tableau qui remplace le tableau Excel actuel du pôle administratif.

Cette vue doit permettre de suivre rapidement l’ensemble des affaires et de repérer les dossiers en retard, incomplets ou proches d’une échéance.

### 4.2 Fonctionnalités attendues

La page de suivi des dossiers doit permettre :

- d’afficher tous les dossiers dans un tableau ;
- de trier les dossiers par date, prix, état ou affaire ;
- de rechercher par affaire, adresse, vendeur, bénéficiaire ou locataire ;
- de filtrer par type de dossier ;
- de filtrer par activité métier ;
- de filtrer par catégorie ;
- de filtrer par état ;
- de filtrer par collaborateur interne ;
- d’accéder rapidement à la fiche détail d’un dossier ;
- d’exporter les données au format Excel ou CSV.

### 4.3 Colonnes prioritaires du tableau

Colonnes à afficher en priorité :

- Affaire ;
- Lot / étage ;
- Adresse du bien ;
- Vendeur ;
- Bénéficiaire ;
- Locataire ;
- État ;
- Date de promesse ;
- Prix ;
- Frais ;
- DG ;
- Date DG ;
- CS prêt ;
- Date CS prêt ;
- Date de réitération ;
- Acte.

La liste doit rester lisible. Les informations secondaires pourront être affichées dans la fiche détail du dossier.

## 5. Module 3 : Gestion des activités administratives

### 5.1 Objectif

Adapter le module d’activité afin qu’il corresponde aux besoins du pôle administratif.

Une activité représente une tâche, une action ou un suivi à réaliser sur un dossier.

### 5.2 Modification du formulaire “Nouvelle activité”

Le formulaire actuel doit être modifié.

Champs à retirer :

- Client ;
- Contact.

Ces champs doivent être remplacés par une notion de collaborateur interne.

Champs attendus pour une nouvelle activité :

- Société liée à l’affaire ;
- Affaire concernée ou dossier concerné ;
- Collaborateur interne responsable ;
- Statut ;
- Date unique de suivi ou d’échéance ;
- Description ou commentaire ;
- Priorité éventuelle.

Le collaborateur interne doit correspondre à un utilisateur ou à un profil interne de Benjamin Immobilier.

Les pièces jointes ne sont pas retenues dans le formulaire d’activité à ce stade.

### 5.3 Statuts d’activité

Chaque activité doit disposer d’un statut.

Statuts retenus pour la version actuelle :

- À faire ;
- En cours ;
- Terminé ;
- Annulé.

Ces statuts doivent être filtrables et visibles depuis le tableau de bord.

Les statuts plus détaillés, par exemple "En attente d’un tiers", "En attente de signature" ou "Bloqué", ne sont pas retenus pour l’instant. Ils pourront être ajoutés plus tard si le pôle administratif en exprime le besoin.

### 5.4 Suivi des activités

Le module doit permettre :

- de créer une activité depuis un dossier ;
- de consulter les activités liées à un dossier ;
- d’assigner une activité à un collaborateur ;
- de modifier son statut ;
- d’identifier les activités en retard ;
- d’afficher les activités à venir ;
- d’envoyer un rappel au collaborateur concerné.

Exemples d’activités administratives :

- préparer une promesse ;
- vérifier une date de réitération ;
- relancer un notaire ;
- transmettre un document à Rudy ;
- vérifier une condition suspensive ;
- attendre une signature ;
- contrôler un acte ;
- mettre à jour les informations d’un dossier.

## 6. Module 4 : Calendrier et échéancier

### 6.1 Objectif

Mettre en place une vue calendrier permettant au pôle administratif de visualiser les dates importantes.

### 6.2 Dates à afficher

Le calendrier doit permettre de suivre les dates importantes, principalement via des activités créées manuellement.

Les dates suivantes peuvent être reprises manuellement dans le calendrier lorsqu’un collaborateur souhaite les suivre :

- date de promesse ;
- date DG ;
- date CS prêt ;
- date de réitération ;
- date liée à l’acte ;
- dates de suivi ou d’échéance des activités ;
- dates de relance ;
- dates de signature attendues.

Les dates présentes dans la fiche dossier ne doivent pas nécessairement générer automatiquement des événements calendrier dans cette version.

### 6.3 Fonctionnalités attendues

La vue calendrier doit permettre :

- une vue mensuelle ;
- une vue hebdomadaire ;
- une distinction visuelle par type de dossier ou par état ;
- un accès rapide à la fiche dossier depuis un événement ;
- l’affichage des échéances en retard ;
- le filtrage par collaborateur ;
- le filtrage par activité métier ;
- le filtrage par catégorie de dossier.

Une synchronisation avec Outlook ou Google Calendar pourra être envisagée dans un second temps.

## 7. Module 5 : Rappels et notifications

### 7.1 Objectif

Réduire les oublis liés aux dates importantes des dossiers administratifs.

### 7.2 Fonctionnalités attendues

Le système doit pouvoir envoyer des rappels :

- lorsqu’une activité arrive à échéance ;
- lorsqu’une activité est en retard.

Les rappels portent d’abord sur les activités créées dans le calendrier. Si une date de promesse, une date DG, une date CS prêt, une date de réitération ou une date de signature doit faire l’objet d’un rappel, elle peut être saisie manuellement comme activité.

### 7.3 Paramétrage des rappels

Les délais de rappel doivent être paramétrables.

Exemples :

- 7 jours avant ;
- 3 jours avant ;
- le jour même ;
- 1 jour après échéance ;
- chaque semaine tant que l’activité n’est pas terminée, si ce comportement est retenu.

Le paramétrage doit permettre de choisir si le rappel est envoyé avant ou après l’échéance, ainsi que le nombre de jours concerné.

Dans la première version, un e-mail suffit. Il doit être envoyé à la personne associée à l’activité.

Une intégration Outlook, Google Calendar ou autre outil interne pourra être ajoutée plus tard.

## 8. Module 6 : Signature administrative

### 8.1 Objectif

Mettre en place un suivi des signatures liées aux documents transmis depuis l’intranet.

Le circuit de signature attendu fonctionne ainsi :

- n’importe quel membre de l’intranet peut envoyer un document à signer ;
- la demande est assignée à un membre du pôle administratif ;
- un e-mail est envoyé au membre du pôle administratif assigné ainsi qu’à Rudy (CEO) ;
- Rudy conserve une visibilité complète sur toutes les demandes de signature ;
- le membre du pôle administratif assigné et Rudy peuvent signer le document.

Ce fonctionnement permet au pôle administratif de traiter les signatures tout en garantissant une traçabilité et une supervision par le CEO.

### 8.2 Fonctionnalités attendues

Le module doit permettre :

- de lier un document à un dossier ;
- d’envoyer un document en signature depuis n’importe quel compte intranet autorisé ;
- d’assigner la demande à un membre du pôle administratif ;
- d’envoyer un e-mail au membre du pôle administratif assigné et à Rudy ;
- de permettre au membre du pôle administratif assigné de signer le document ;
- de permettre à Rudy de signer le document ;
- de permettre à Rudy de consulter l’ensemble des demandes et documents à signer ;
- de suivre l’état de la signature ;
- d’archiver le document signé ;
- de conserver l’historique de validation.

### 8.3 Statuts de signature

Statuts proposés :

- Brouillon ;
- En attente de signature;
- Signé ;
- Refusé ;
- Archivé.

L’intégration d’une solution de signature électronique certifiée pourra être étudiée ultérieurement si l’entreprise souhaite un processus juridiquement renforcé.

L’idée retenue est que la signature soit accessible à l’administratif assigné et à Rudy, avec Rudy systématiquement informé pour conserver une trace écrite et une vue globale.

## 9. Module 7 : Relances externes

### 9.1 Objectif

Automatiser ou faciliter les relances auprès des interlocuteurs externes lorsqu’une réponse est attendue.

Ce besoin reste à clarifier. Il ne doit pas être considéré comme prioritaire tant que le fonctionnement attendu n’a pas été validé avec le pôle administratif.

Interlocuteurs concernés :

- notaires ;
- avocats ;
- huissiers ;
- partenaires ;
- vendeurs ;
- bénéficiaires ;
- autres interlocuteurs liés aux dossiers.

### 9.2 Fonctionnalités potentielles à confirmer

Le module de relance pourrait permettre :

- de créer une relance liée à un dossier ;
- de créer une relance liée à une activité ;
- de choisir un modèle de mail ;
- d’envoyer une relance manuellement ;
- d’automatiser certaines relances après un délai paramétrable ;
- d’historiser les relances envoyées ;
- de suivre le statut de la relance.

### 9.3 Statuts de relance

Statuts proposés, à confirmer :

- À relancer ;
- Relance envoyée ;
- Réponse reçue ;
- Relance annulée ;
- Clos.

L’automatisation complète des relances e-mail doit être considérée comme une étape secondaire.  
La priorité est d’abord de structurer correctement les dossiers, les activités et les échéances.

## 10. Rôles et permissions

### 10.1 Objectif

Sécuriser les accès et éviter les modifications non autorisées.

### 10.2 Rôles proposés

Rôles minimums :

- Rudy (CEO, superadmin)
- Pôle administratif

### 10.3 Permissions à prévoir

Le système doit permettre de définir :

- qui peut créer un dossier ;
- qui peut modifier un dossier ;
- qui peut archiver un dossier ;
- qui peut supprimer un dossier ;
- qui peut créer une activité ;
- qui peut modifier une activité ;
- qui peut signer un document ;
- qui peut consulter les documents ;
- qui peut exporter les données.

Les actions importantes doivent être historisées.

## 11. Documents et pièces jointes

### 11.1 Objectif

Centraliser les documents administratifs liés aux dossiers.

### 11.2 Fonctionnalités attendues

Le module doit permettre :

- d’ajouter des pièces jointes à un dossier ;
- de classer les documents par type ;
- de rechercher un document ;
- de télécharger un document ;
- d’identifier les documents signés ;
- d’archiver les documents importants.

Les pièces jointes liées directement aux activités ne sont pas retenues à ce stade.

Types de documents possibles :

- promesse ;
- acte ;
- document de prêt ;
- document de négociation ;
- document notarial ;
- courrier ;
- facture ou justificatif ;
- autre pièce administrative.

## 12. Import et reprise des données existantes

### 12.1 Objectif

Permettre la reprise des données déjà présentes dans les fichiers de suivi existants et permettre l’export des dossiers administratifs depuis l’intranet.

### 12.2 Travail attendu

Il faudra prévoir :

- une fonction d’export des dossiers administratifs au format Excel ou CSV ;
- une analyse du fichier Excel actuel ;
- une correspondance entre les colonnes Excel et les champs de l’intranet ;
- un nettoyage des dates ;
- un nettoyage des montants ;
- une vérification des doublons ;
- un import initial en base de données ;
- un contrôle par le pôle administratif après import.

L’export et l’import des dossiers administratifs sont retenus comme fonctions à ajouter.

### 12.3 Correspondance indicative

| Colonne Excel actuelle | Champ intranet attendu |
|---|---|
| AFFAIRES | Affaire |
| LOTS / ETAGE | Lot / étage |
| ADRESSE DU BIEN | Adresse du bien |
| VENDEUR | Vendeur |
| BENEFICIAIRE | Bénéficiaire |
| LOCATAIRE | Locataire |
| ETAT | État |
| DATE PROMESSE | Date de promesse |
| NEGOCIATION EXTERNE | Négociation externe |
| FRAIS | Frais |
| PRIX | Prix |
| DG | Dépôt de garantie |
| DATE DG | Date DG |
| CS PRÊT | CS prêt | (Conditions suspensives)
| DATE CS PRÊT | Date CS prêt |
| DATE REITERATION | Date de réitération |
| ACTE | Acte |

## 13. Éléments à retirer ou à exclure du périmètre

### 13.1 Retrait du système de candidature

Le système de candidature ne fait plus partie du périmètre du pôle administratif.

Travail à réaliser :

- retirer les liens de menu liés aux candidatures ;
- retirer les pages candidature du tableau de bord administratif ;
- masquer ou désactiver les routes concernées ;
- retirer les permissions inutiles ;
- conserver les données existantes tant qu’aucune suppression définitive n’a été validée.

La suppression technique définitive des tables ou modèles liés aux candidatures devra être validée avant intervention.

### 13.2 Éléments hors périmètre immédiat

Ne sont pas prioritaires dans cette version :

- assistant IA administratif ;
- analyse automatique avancée des documents ;
- automatisation complète des relances e-mail ;
- signature électronique certifiée externe ;
- synchronisation calendrier avancée ;
- reporting décisionnel avancé.

Ces éléments pourront être envisagés dans une version ultérieure.

## 14. Contraintes techniques

### 14.1 Contraintes générales

Le module doit respecter les contraintes suivantes :

- interface web accessible depuis l’intranet ;
- responsive design ;
- authentification sécurisée ;
- gestion des rôles ;
- base de données relationnelle ;
- journalisation des actions importantes ;
- compatibilité avec l’architecture existante de l’intranet Benjamin Immobilier.

### 14.2 Technologies envisagées

Dans le cadre de l’intranet existant, les technologies à privilégier sont :

- Django pour le backend ;
- PostgreSQL pour la base de données ;
- templates Django ou frontend dédié selon l’architecture existante ;
- Celery ou tâche planifiée pour les rappels ;
- SMTP ou service mail existant pour l’envoi des notifications ;
- export Excel ou CSV pour les données administratives.

## 15. Sécurité, traçabilité et RGPD

Le module administratif devra respecter les exigences suivantes :

- stockage sécurisé des données ;
- accès limité selon les rôles ;
- journalisation des créations, modifications et suppressions ;
- conservation de l’historique des signatures ;
- protection des documents confidentiels ;
- respect du RGPD ;
- sauvegarde régulière des données ;
- possibilité d’archivage des dossiers terminés.

## 16. Priorisation du travail restant

### Priorité 1 : Structure métier des dossiers

État actuel : implémenté dans le code.

À maintenir et confirmer métier :

- conserver le vocabulaire Dossier ;
- conserver les types Vente et Acquisition ;
- conserver les états de dossier actuellement retenus ;
- confirmer les catégories avec le pôle administratif ;
- conserver la fiche dossier et les champs issus du tableau administratif.

### Priorité 2 : Activités administratives

À réaliser ensuite :

- modifier le formulaire Nouvelle activité ;
- retirer Client et Contact ;
- ajouter Collaborateur interne ;
- lier l’activité à un dossier ;
- gérer les statuts retenus et une date unique ;
- afficher les activités par dossier.

### Priorité 3 : Tableau de suivi

État actuel : la gestion des dossiers administratifs est considérée comme implémentée.

À maintenir ou ajouter :

- conserver la vue tableau ;
- conserver les filtres ;
- conserver la recherche ;
- conserver le tri ;
- ajouter l’export Excel ou CSV si absent.

### Priorité 4 : Calendrier et rappels

À réaliser ensuite :

- créer la vue calendrier ;
- permettre la saisie manuelle des dates importantes sous forme d’activités ;
- identifier les échéances en retard ;
- paramétrer les rappels avant ou après échéance ;
- envoyer les rappels par e-mail à la personne associée à l’activité.

### Priorité 5 : Signature

À réaliser une fois les dossiers structurés :

- lier les documents à un dossier ;
- permettre à n’importe quel membre de l’intranet d’envoyer un document à signer ;
- assigner la demande à un membre du pôle administratif ;
- notifier par e-mail le membre assigné et Rudy ;
- permettre la signature par le membre administratif assigné ou par Rudy ;
- donner à Rudy une vue globale sur toutes les demandes ;
- suivre les statuts de signature ;
- archiver les documents signés.

### Priorité 6 : Import / export des dossiers

À réaliser :

- exporter les dossiers administratifs au format Excel ou CSV ;
- importer les anciens fichiers Excel après validation du mapping ;
- contrôler les données importées avec le pôle administratif.

### Priorité 7 : Nettoyage de l’existant

À réaliser en parallèle ou en fin de sprint :

- retirer le système candidature de l’interface ;
- nettoyer les menus ;
- nettoyer les permissions inutiles ;
- masquer les routes non utilisées.

## 17. Points à confirmer avec le pôle administratif

Avant développement complet, les points suivants doivent être validés :

- liste exacte des catégories envoyées par Mégane ;
- liste définitive des états de dossier ;
- validation du fait que les statuts d’activité actuels suffisent ;
- confirmation qu’une seule date suffit dans le formulaire d’activité ;
- confirmation que le champ Société correspond bien à la société liée à l’affaire ;
- confirmation que les dates dossier doivent être ajoutées manuellement au calendrier ;
- règles de paramétrage des rappels : avant ou après échéance, nombre de jours, répétition éventuelle ;
- confirmation que l’e-mail de rappel doit uniquement viser la personne associée à l’activité ;
- règles de signature : émetteur intranet, membre administratif assigné, notification e-mail à l’assigné et à Rudy, signature possible par les deux ;
- périmètre réel des relances externes ;
- format d’import souhaité pour les anciens fichiers Excel ;
- format d’export souhaité pour les dossiers administratifs ;
- niveau d’automatisation attendu pour les relances ;
- besoin ou non d’une signature électronique externe certifiée.

## 18. Synthèse

Le module administratif doit devenir un outil central de suivi des dossiers immobiliers de Benjamin Immobilier.

La priorité est de structurer l’intranet autour des dossiers, et non plus autour des projets. Chaque dossier doit pouvoir être suivi selon son type, son état, ses dates clés, ses activités internes, ses documents, ses signatures et ses relances éventuelles.

Le travail restant consiste principalement à :

- confirmer les arbitrages métier avec le pôle administratif ;
- finaliser le module d’activité avec une date unique et les statuts actuels ;
- ajouter le paramétrage des rappels par e-mail ;
- ajouter l’export et l’import des dossiers administratifs ;
- gérer le circuit de signature ouvert aux membres de l’intranet, assigné à un membre administratif, avec notification et visibilité CEO ;
- clarifier le périmètre des relances externes ;
- retirer le système candidature.
