# Cahier des charges informatique – Pôle Administratif Benjamin Immobilier

## 1. Contexte et objectifs

Dans le cadre de l’amélioration des processus internes de Benjamin Immobilier, ce cahier des charges formalise les besoins du pôle administratif pour l’intranet interne.

L’objectif principal est de centraliser le suivi des dossiers administratifs liés aux opérations immobilières, afin de remplacer les suivis dispersés dans des tableaux Excel et de donner une vision claire de l’avancement de chaque affaire.

Le module administratif doit permettre de suivre les dossiers de vente et d’acquisition, les dates importantes, les activités associées, les signatures et les relances externes.

Ce cahier des charges met à jour l’ancien besoin initial qui parlait principalement de suivi de projets et de relances automatisées. La logique métier attendue est désormais centrée sur la notion de **dossier administratif**, avec une convergence vers un dossier unique partagé avec le pôle technique lorsque les informations concernent la même affaire.

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

Le pôle administratif doit pouvoir consulter les affaires et dossiers techniques pertinents pour son travail. Cette règle couvre notamment Mégane en tant que membre du pôle administratif : il ne doit pas y avoir de droit nominatif spécifique lorsque l'appartenance au pôle suffit.

## 3. Module 1 : Gestion des dossiers administratifs

### 3.1 Objectif

Mettre en place un module permettant de créer, consulter, modifier et suivre des dossiers administratifs liés aux affaires immobilières de Benjamin Immobilier.

Le terme **Projet** doit être remplacé par le terme **Dossier** dans l’interface, les menus, les formulaires et les vues concernées.

Les dossiers administratifs et techniques doivent converger vers une logique de dossier unique. Les interfaces peuvent rester adaptées au pôle administratif ou au pôle technique, mais elles ne doivent pas créer deux dossiers concurrents pour une même affaire lorsque les données peuvent être centralisées.

État actuel : la structure des dossiers administratifs est considérée comme implémentée dans le code. Les évolutions restantes concernent principalement les exports, imports, rappels et validations métier.

Mise à jour de cadrage : les filtres cachés par défaut et le retrait de l’export CSV sont considérés comme faits. Les nouveaux besoins à intégrer concernent notamment l’historique des relances, les rappels individuels, les champs personnalisables, l’export PDF, la gestion avancée des tampons et signatures, ainsi que l’import/export de calendrier. Google Agenda / Gmail est une solution temporaire ; l’objectif final est Outlook.

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

### 3.6 Champs personnalisables

Le module doit permettre la création de champs personnalisables sur les dossiers administratifs.

Fonctionnalités attendues :

- créer un champ personnalisé depuis l’interface ;
- choisir son libellé ;
- choisir son type de saisie, par exemple texte, date, montant, nombre, case à cocher ou liste de choix ;
- décider si le champ est affiché dans la fiche dossier ;
- décider si le champ est affiché dans le tableau de suivi ;
- permettre la modification ou la désactivation d’un champ personnalisé ;
- conserver les valeurs déjà saisies lorsqu’un champ est désactivé.

Ce mécanisme doit permettre au pôle administratif d’ajouter des informations métier sans intervention technique à chaque nouvelle évolution du tableau de suivi.

### 3.7 Fiche détail d’un dossier

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

### 3.8 Référentiel des sociétés

La gestion du référentiel des sociétés relève du pôle administratif. Ce référentiel doit rester commun aux dossiers, factures, signatures, tampons et autres modules qui utilisent une société.

Le module doit permettre aux utilisateurs administratifs autorisés :

- de créer et modifier une société ;
- de rechercher et consulter les sociétés ;
- de supprimer définitivement une société qui n'a jamais été utilisée ;
- de retirer des listes de sélection une société qui ne doit plus être utilisée.

Une société déjà liée à un dossier, une facture, un document ou un tampon ne doit pas être supprimée physiquement, afin de préserver l'intégrité et l'historique des données. Elle doit être retirée des nouvelles sélections tout en restant visible sur les éléments historiques auxquels elle est liée.

Les autres pôles peuvent utiliser ce référentiel selon leurs droits, sans pouvoir le modifier sauf permission administrative explicite.

### 3.9 Liaison obligatoire entre dossier et société

Chaque dossier, qu’il soit consulté depuis le pôle administratif, technique, financier ou un autre module, doit obligatoirement être rattaché à une société active du référentiel partagé.

- la société est demandée lors de la création d’un dossier ;
- un dossier existant ne peut pas être enregistré sans société ;
- la société du dossier est affichée dans les listes, filtres, fiches et exports ;
- les imports de nouveaux dossiers doivent contenir une société reconnue du référentiel ;
- dans tout écran proposant un dossier, la société doit être sélectionnée en premier et seuls ses dossiers doivent être proposés ;
- toute création ou modification reçue par le serveur doit être refusée si le dossier est fourni sans société ou si le couple société–dossier est incohérent ;
- une modification de la société du dossier est répercutée sur ses factures et activités liées afin d’éviter toute association contradictoire.

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
- d’exporter les données au format Excel ;
- d’exporter les données au format PDF.

Les filtres avancés doivent être cachés par défaut afin de garder une interface lisible. L’utilisateur doit pouvoir les afficher uniquement lorsqu’il en a besoin.

L’export CSV est retiré du périmètre et ne doit plus être proposé dans l’interface.

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

Le type d'activité est entièrement supprimé. Il ne doit plus exister dans le modèle de données ni être demandé, affiché ou utilisé dans les formulaires, tableaux, filtres, calendriers, imports ou pages de détail. Les activités, leurs statuts, priorités, responsables, dates et rappels restent conservés.

### 5.2 Modification du formulaire “Nouvelle activité”

Le formulaire actuel doit être modifié.

Champs à retirer :

- Client ;
- Contact.

Ces champs doivent être remplacés par une notion de collaborateur interne.

Champs attendus pour une nouvelle activité :

- Société liée à l’affaire ;
- Affaire concernée ou dossier concerné, facultatif ;
- Collaborateur interne responsable ;
- Intitulé ;
- Statut ;
- Créneau personnalisé avec une date et une heure de début ainsi qu’une date et une heure de fin ;
- Description ou commentaire ;
- Priorité éventuelle.

Le collaborateur interne doit correspondre à un utilisateur ou à un profil interne de Benjamin Immobilier.

Une activité peut exister sans dossier rattaché lorsque le suivi concerne une action générale, un rappel interne ou une tâche non encore associée à une affaire précise.

Les dossiers archivés ne doivent pas être proposés comme dossiers rattachables à une nouvelle activité.

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
- l’affichage du calendrier administrateur / CEO, c’est-à-dire du superadmin, en vue complémentaire et en lecture seule pour le pôle administratif ;
- une distinction visuelle par type de dossier ou par état ;
- un accès rapide à la fiche dossier depuis un événement ;
- l’affichage des échéances en retard ;
- le filtrage par collaborateur ;
- le filtrage par catégorie de dossier ;
- l’import d’événements calendrier ;
- l’export d’événements calendrier.

Le besoin retenu est un import/export de calendrier, et non une synchronisation complète dans cette version. Google Agenda / Gmail est une solution temporaire pour faciliter les premiers échanges. L’objectif final est de permettre l’import/export avec Outlook.

L’import calendrier doit pouvoir créer des activités sans dossier rattaché et sans responsable sélectionné, afin d’intégrer un calendrier externe sans dépendance préalable à des données intranet. Les activités importées sont associées au calendrier personnel de l’utilisateur qui réalise l’import. Aucun type d'activité ne doit être demandé ou affiché lors de cet import.

Le pôle administratif peut consulter le calendrier administrateur / CEO, c’est-à-dire le calendrier du superadmin. Il ne doit pas pouvoir créer, modifier ou supprimer des événements dans ce calendrier.

## 7. Module 5 : Rappels et notifications

### 7.1 Objectif

Réduire les oublis liés aux dates importantes des dossiers administratifs.

### 7.2 Fonctionnalités attendues

Le système doit pouvoir envoyer des rappels :

- lorsqu’une activité arrive à échéance ;
- lorsqu’une activité est en retard ;
- à un collaborateur précis, sous forme de rappel individuel.

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

Le formulaire d’activité doit permettre de définir librement le début et la fin du créneau. La durée est calculée automatiquement et réutilisée dans le calendrier, les rappels et les échanges Outlook/ICS.

Dans la première version, un e-mail suffit. Il doit être envoyé à la personne associée à l’activité.

L’import/export de calendrier doit être pris en compte dans le cadrage du calendrier et des rappels. Google Agenda / Gmail sert de solution temporaire ; Outlook reste la cible finale.

## 8. Module 6 : Signature administrative

### 8.1 Objectif

Mettre en place un suivi des signatures liées aux documents transmis depuis l’intranet.

Le circuit de signature attendu fonctionne ainsi :

- n’importe quel membre de l’intranet peut envoyer un document à signer ;
- la demande est assignée à un membre du pôle administratif ;
- un e-mail est envoyé au membre du pôle administratif assigné ainsi qu’aux superadministrateurs configurés ;
- les superadministrateurs conservent une visibilité complète sur toutes les demandes de signature ;
- le membre du pôle administratif assigné et les superadministrateurs autorisés peuvent signer le document.

Ce fonctionnement permet au pôle administratif de traiter les signatures tout en garantissant une traçabilité et une supervision par le CEO.

### 8.2 Fonctionnalités attendues

Le module doit permettre :

- de lier un document à un dossier ;
- d’envoyer un document en signature depuis n’importe quel compte intranet autorisé ;
- d’assigner la demande à un membre du pôle administratif ;
- d’envoyer un e-mail au membre du pôle administratif assigné et aux superadministrateurs configurés ;
- de permettre au membre du pôle administratif assigné de signer le document ;
- de permettre aux superadministrateurs autorisés de signer le document ;
- de permettre aux superadministrateurs de consulter l’ensemble des demandes et documents à signer ;
- de suivre l’état de la signature ;
- d’archiver le document signé ;
- de conserver l’historique de validation ;
- de proposer quatre signatures préenregistrées au choix ;
- de choisir entre une signature seule, un tampon seul, ou un bloc tampon + signature ;
- de sélectionner le tampon à utiliser avant génération du PDF signé ;
- de créer ou modifier un tampon depuis l’interface, identifié par sa société ;
- de prévoir jusqu’à 46 tampons disponibles ;
- de renseigner un lieu et une date pour générer la mention « Fait à [lieu], le [date] » ;
- de prévisualiser le placement de cette mention avant la génération du document final ;
- d’étudier l’aide OCR / IA pour détecter les zones de signature ou de tampon sur les documents.

Les quatre signatures doivent être administrables uniquement par les utilisateurs disposant de la permission correspondante. La signature sélectionnée, l'utilisateur ayant réalisé l'opération, le lieu et la date doivent être conservés dans l'historique. La liste et les fichiers définitifs des quatre signatures doivent être fournis avant la mise en production.

### 8.3 Statuts de signature

Statuts proposés :

- Brouillon ;
- En attente de signature;
- Signé ;
- Refusé ;
- Archivé.

L’intégration d’une solution de signature électronique certifiée pourra être étudiée ultérieurement si l’entreprise souhaite un processus juridiquement renforcé.

L’idée retenue est que la signature soit accessible à l’administratif assigné et aux superadministrateurs autorisés, avec notification des superadministrateurs configurés afin de conserver une trace écrite et une vue globale.

Le besoin prioritaire porte sur la signature interne avec génération de PDF signé, choix du tampon et possibilité d’apposer le tampon avec ou sans signature.

Les documents signés doivent être visibles uniquement par les utilisateurs concernés par la demande ou le document. Les administrateurs et le CEO conservent une visibilité complète pour supervision, contrôle et historique.

Les tampons doivent être identifiés par société. Le champ "nom du tampon" n'est pas retenu comme information métier à maintenir ; la société suffit pour la sélection et l'affichage.

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
- de consulter l’historique complet des relances depuis la fiche dossier ;
- de distinguer les relances automatiques des relances manuelles ;
- de tracer la date, l’émetteur, le destinataire, le contenu ou le modèle utilisé et le statut de chaque relance ;
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

- Superadministrateur ;
- Pôle administratif.

Le rôle de superadministrateur doit pouvoir être attribué à plusieurs utilisateurs simultanément. Lors de la mise en service initiale, il est attribué à Mégane et Rudy. Ces deux comptes disposent du même niveau de droits, sauf exception explicitement documentée et validée.

### 10.3 Permissions à prévoir

Le système doit permettre de définir :

- qui peut créer un dossier ;
- qui peut modifier un dossier ;
- qui peut archiver un dossier ;
- qui peut valider une suppression définitive exceptionnelle ;
- qui peut créer une activité ;
- qui peut modifier une activité ;
- qui peut signer un document ;
- qui peut gérer les quatre signatures préenregistrées ;
- qui peut créer, modifier ou retirer une société du référentiel ;
- qui peut consulter les documents ;
- qui peut consulter les dossiers techniques pertinents depuis le pôle administratif ;
- qui peut consulter le calendrier administrateur / CEO superadmin en lecture seule ;
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

L'affichage des documents signés doit être limité aux utilisateurs concernés par la demande ou le document, avec exception pour les administrateurs et le CEO.

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

- une fonction d’export des dossiers administratifs au format Excel ;
- une fonction d’export des dossiers administratifs au format PDF ;
- une analyse du fichier Excel actuel ;
- une correspondance entre les colonnes Excel et les champs de l’intranet ;
- un nettoyage des dates ;
- un nettoyage des montants ;
- une vérification des doublons ;
- un import initial en base de données ;
- un contrôle par le pôle administratif après import.

L’export Excel, l’export PDF et l’import des dossiers administratifs sont retenus comme fonctions à ajouter.

L’export CSV est retiré du périmètre.

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

Travail réalisé :

- retirer les liens de menu liés aux candidatures ;
- retirer les pages candidature du tableau de bord administratif ;
- retirer les routes concernées ;
- retirer les permissions inutiles ;
- supprimer les modèles et les tables après validation définitive.

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
- export Excel et PDF pour les données administratives ;
- import/export calendrier, avec Google Agenda / Gmail en solution temporaire et Outlook comme cible finale.

## 15. Sécurité, traçabilité et RGPD

Le module administratif devra respecter les exigences suivantes :

- stockage sécurisé des données ;
- accès limité selon les rôles ;
- journalisation des créations, modifications, archivages et suppressions exceptionnelles ;
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
- confirmer la convergence avec le dossier technique dans une logique de dossier unique ;
- conserver les états de dossier actuellement retenus ;
- confirmer les catégories avec le pôle administratif ;
- conserver la fiche dossier et les champs issus du tableau administratif.

### Priorité 2 : Référentiel des sociétés

À réaliser avant les modules qui consomment ces données :

- transférer la gestion des sociétés au pôle administratif ;
- partager le même référentiel avec les dossiers, factures, signatures et tampons ;
- autoriser la suppression définitive uniquement pour une société jamais utilisée ;
- retirer des nouvelles sélections une société déjà utilisée qui ne doit plus être proposée.

La gestion de plusieurs superadministrateurs, dont l'attribution initiale à Mégane et Rudy, est conservée dans le périmètre mais reportée à une phase ultérieure.

### Priorité 3 : Activités administratives

À réaliser ensuite :

- modifier le formulaire Nouvelle activité ;
- retirer Client et Contact ;
- retirer le type d'activité de tous les formulaires, tableaux, filtres et imports ;
- ajouter Collaborateur interne ;
- permettre de lier l’activité à un dossier lorsque c’est pertinent, sans rendre ce rattachement obligatoire ;
- gérer les statuts retenus et une date unique ;
- afficher les activités par dossier.

### Priorité 4 : Tableau de suivi

État actuel : la gestion des dossiers administratifs est considérée comme implémentée.

À maintenir ou ajouter :

- conserver la vue tableau ;
- conserver les filtres, cachés par défaut ;
- conserver la recherche ;
- conserver le tri ;
- ajouter l’export Excel si absent ;
- ajouter l’export PDF.

### Priorité 5 : Signature

À réaliser une fois les dossiers, les sociétés et les droits structurés :

- lier les documents à un dossier ;
- permettre à n’importe quel membre de l’intranet d’envoyer un document à signer ;
- assigner la demande à un membre du pôle administratif ;
- notifier le membre assigné et les superadministrateurs configurés ;
- permettre la signature par le membre administratif assigné ou un superadministrateur autorisé ;
- donner aux superadministrateurs une vue globale sur toutes les demandes ;
- proposer quatre signatures préenregistrées au choix ;
- ajouter la mention « Fait à [lieu], le [date] » et sa prévisualisation ;
- suivre les statuts de signature et archiver les documents signés ;
- permettre le choix signature seule, tampon seul ou tampon + signature ;
- limiter l'affichage des documents signés aux utilisateurs concernés, sauf administrateurs et superadministrateurs ;
- prévoir 46 tampons sélectionnables, identifiés par société ;
- permettre la création ou modification de tampon sans gérer de nom de tampon distinct de la société ;
- étudier l’OCR / IA pour aider au placement de la signature, du tampon et de la mention de lieu et de date.

### Priorité 6 : Calendrier et rappels

À réaliser ensuite :

- créer la vue calendrier ;
- afficher le calendrier administrateur / CEO superadmin en lecture seule comme vue complémentaire pour le pôle administratif ;
- permettre la saisie manuelle des dates importantes sous forme d’activités ;
- identifier les échéances en retard ;
- paramétrer les rappels avant ou après échéance ;
- permettre un créneau personnalisé en choisissant librement l’heure de début et l’heure de fin ;
- envoyer les rappels par e-mail à la personne associée à l’activité ;
- gérer les rappels individuels ;
- prévoir l’import/export calendrier, avec Google Agenda / Gmail en solution temporaire et Outlook comme cible finale.

### Priorité 7 : Import / export des dossiers

À réaliser :

- exporter les dossiers administratifs au format Excel ;
- exporter les dossiers administratifs au format PDF ;
- importer les anciens fichiers Excel après validation du mapping ;
- contrôler les données importées avec le pôle administratif.

### Priorité 8 : Champs personnalisables

À réaliser :

- créer une interface de création de champ personnalisé ;
- gérer les types de champs autorisés ;
- permettre l’affichage des champs personnalisés dans la fiche dossier et, si besoin, dans le tableau ;
- conserver l’historique ou les valeurs en cas de désactivation du champ.

### Priorité 9 : Relances externes

À réaliser :

- conserver un historique des relances ;
- afficher l’historique depuis la fiche dossier ;
- tracer les relances manuelles et automatiques ;
- confirmer le niveau d’automatisation attendu.

### Priorité 10 : Nettoyage de l’existant

À réaliser en parallèle ou en fin de sprint :

- retirer le système candidature de l’interface ;
- nettoyer les menus ;
- nettoyer les permissions inutiles ;
- masquer les routes non utilisées.

## 17. Points à confirmer avec le pôle administratif

Avant développement complet, les points suivants doivent être validés :

- liste exacte des catégories envoyées par Mégane ;
- confirmation que Mégane est couverte par les droits du pôle administratif, sans exception nominative ;
- validation de l'attribution initiale du rôle de superadministrateur à Mégane et Rudy, avec des droits identiques ;
- liste définitive des états de dossier ;
- validation du fait que les statuts d’activité actuels suffisent ;
- validation des limites autorisées pour les créneaux personnalisés, actuellement de 5 minutes à 24 heures ;
- confirmation que le champ Société correspond bien à la société liée à l’affaire ;
- confirmation que les dates dossier doivent être ajoutées manuellement au calendrier ;
- règles de paramétrage des rappels : avant ou après échéance, nombre de jours, répétition éventuelle ;
- confirmation que l’e-mail de rappel doit uniquement viser la personne associée à l’activité ;
- règles d’import/export calendrier, d’abord Google Agenda / Gmail puis Outlook ;
- règles de signature : émetteur intranet, membre administratif assigné, notification aux superadministrateurs et droits de signature associés ;
- liste et fichiers définitifs des quatre signatures à proposer ;
- règle de placement de la mention « Fait à [lieu], le [date] » ;
- liste des sociétés correspondant aux 46 tampons à prévoir ;
- règles de création, modification et sélection des tampons par société ;
- confirmation de la règle de retrait des sociétés déjà utilisées afin de préserver l'historique ;
- utilité réelle de l’OCR / IA pour détecter ou proposer la zone de signature ;
- périmètre réel des relances externes ;
- format d’import souhaité pour les anciens fichiers Excel ;
- format d’export souhaité pour les dossiers administratifs ;
- structure attendue des champs personnalisables ;
- niveau d’automatisation attendu pour les relances ;
- besoin ou non d’une signature électronique externe certifiée.

## 18. Synthèse

Le module administratif doit devenir un outil central de suivi des dossiers immobiliers de Benjamin Immobilier.

La priorité est de structurer l’intranet autour des dossiers, et non plus autour des projets. Chaque dossier doit pouvoir être suivi selon son type, son état, ses dates clés, ses activités internes, ses documents, ses signatures et ses relances éventuelles. La cible fonctionnelle est un dossier unique partagé entre les besoins administratifs et techniques, avec des vues adaptées selon les pôles.

Le travail restant consiste principalement à :

- confirmer les arbitrages métier avec le pôle administratif ;
- mettre en place les deux superadministrateurs et transférer le référentiel des sociétés au pôle administratif ;
- finaliser le module d’activité sans type d'activité, avec un créneau personnalisé et les statuts actuels ;
- ajouter le paramétrage des rappels par e-mail, avec rappels individuels et créneaux horaires ;
- ajouter l’export Excel, l’export PDF et l’import des dossiers administratifs ;
- gérer le circuit de signature ouvert aux membres de l’intranet, avec quatre signatures au choix, la mention de lieu et de date, les tampons et la supervision des superadministrateurs ;
- clarifier le périmètre des relances externes et conserver leur historique ;
- ajouter les champs personnalisables ;
- prévoir l’import/export calendrier, avec consultation du calendrier administrateur / CEO superadmin en lecture seule par le pôle administratif, Google Agenda / Gmail en solution temporaire puis Outlook comme cible finale ;
- retirer le système candidature.
