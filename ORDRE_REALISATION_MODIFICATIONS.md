# Ordre de réalisation des modifications demandées

Ce document consolide les priorités des cahiers des charges Technique, Administratif et Comptabilité/Finance. L'ordre proposé tient compte des dépendances fonctionnelles et techniques : les rôles et référentiels partagés doivent être stabilisés avant les formulaires qui les utilisent, puis les données doivent être fiabilisées avant les tableaux de bord, exports et fonctions d'IA.

## Phase 0 – Arbitrages courts avant développement

1. Fournir les fichiers et les intitulés des quatre signatures.
2. Valider les seuils de couleur de la jauge budgétaire : 75 % et 100 % proposés.
3. Confirmer que l'absence de relance d'échéance concerne les factures, les rappels internes des activités restant conservés.
4. Identifier les deux plateformes concernées par le suivi Excel et collecter leur documentation d'export, d'import ou d'API.
5. Valider la règle des sociétés : suppression définitive si elles ne sont jamais utilisées, sinon retrait des nouvelles sélections avec conservation de l'historique.

## Phase 1 – Fondations transversales

### 1. Transfert du référentiel des sociétés

- transférer la gestion des sociétés au pôle administratif ;
- conserver un référentiel unique partagé par les dossiers, factures, signatures et tampons ;
- appliquer la règle de suppression ou de retrait des sélections ;
- reprendre les anciennes sociétés saisies en texte libre lorsque cela est nécessaire.

### 2. Référentiel partagé des dossiers

- fiabiliser la liaison entre dossier administratif, dossier technique et facture ;
- rendre obligatoire la société sur chaque dossier et utiliser cette relation comme source de vérité dans tous les modules ;
- synchroniser automatiquement la société des factures et activités liées lorsque le dossier est sélectionné ou modifié ;
- exclure les dossiers archivés des nouvelles sélections ;
- ajouter l'option fonctionnelle Divers pour les factures, sans créer de faux dossier.

### Rôles de direction

Rudy porte le rôle CEO et les pouvoirs de superadministration. Mégane appartient au pôle administratif et reçoit une vue transversale via le rôle Assistante de direction, sans droits techniques de superadministration ni droits de modification des autres pôles.

## Phase 2 – Simplification des activités et des factures

### 4. Retrait du type d'activité

- retirer le champ des formulaires de création et de modification ;
- le retirer des tableaux, filtres, calendriers et imports ;
- supprimer le champ et son référentiel du modèle de données, sans valeur technique de remplacement.

### 5. Règles fondamentales des factures

- limiter les statuts à Reçue et En attente ;
- définir Reçue comme statut initial ;
- rendre obligatoires la société, le dossier ou Divers, et la facture jointe ;
- rendre le commentaire obligatoire lorsque Divers est sélectionné ;
- adapter les anciennes données et supprimer les anciens statuts des interfaces ;
- supprimer les relances automatiques fondées sur l'échéance.

## Phase 3 – Liaisons documentaires et financières

### 6. Plusieurs documents sur une date clé

- créer la relation multiple entre dates clés et documents ;
- permettre la sélection, le téléversement, la consultation et le retrait d'une liaison ;
- préserver le document lorsque seule sa liaison avec la date est retirée.

### 7. Données nécessaires à la jauge budgétaire

- fiabiliser les montants prévus, engagés, payés et restants ;
- relier les dépenses aux factures lorsqu'elles existent ;
- historiser les changements de montants ;
- préparer le calcul agrégé par dossier.

## Phase 4 – Interfaces métier

### 8. Interface des dépenses du dossier technique

- unifier les formulaires de création et de modification ;
- permettre la modification directement depuis la fiche dossier ;
- afficher clairement les montants et la facture éventuellement associée ;
- vérifier les permissions et l'historique.

### 9. Interface des actions du dossier technique

- unifier les formulaires de création et de modification ;
- permettre la modification directe depuis la fiche dossier ;
- gérer responsable, statut, priorité, date, description et commentaires ;
- historiser les modifications.

### 10. Parcours et liste des factures

- adapter l'assistant de saisie aux nouvelles règles ;
- trier par défaut selon la date de création décroissante ;
- adapter les filtres, détails et contrôles de doublons ;
- tester le dossier Divers et l'exclusion des dossiers archivés.

### 11. Jauge des dépenses

- afficher budget total, engagé, payé, restant et pourcentage consommé ;
- appliquer les seuils de couleur validés ;
- afficher le détail permettant de comprendre le calcul.

## Phase 5 – Notifications et signatures

### 12. Pièce jointe obligatoire dans l'e-mail de facture

- joindre automatiquement le fichier de facture à l'e-mail de création ;
- notifier le pôle finance et les superadministrateurs configurés ;
- traiter explicitement les erreurs d'envoi et les fichiers trop volumineux.

### 13. Quatre signatures et mention de lieu et de date

- administrer quatre signatures préenregistrées ;
- permettre leur sélection selon les permissions ;
- ajouter la mention « Fait à [lieu], le [date] » ;
- prévisualiser le placement avant génération ;
- historiser la signature, l'utilisateur, le lieu et la date.

## Phase 6 – Restitution et échanges

### 14. Mise à jour du dashboard Finance

- afficher uniquement les indicateurs compatibles avec Reçue et En attente ;
- retirer les indicateurs payée, refusée, archivée ou en retard qui ne sont plus alimentés ;
- vérifier les analyses par société et par dossier.

### 15. Suivi Intranet vers Excel

- conserver l'intranet comme système faisant foi ;
- ajouter ou mettre à jour la ligne Excel à chaque écriture de facture ;
- utiliser l'identifiant intranet pour éviter les doublons ;
- préserver les colonnes supplémentaires du classeur historique ;
- journaliser les erreurs et permettre une resynchronisation complète ou ciblée.

## Phase 7 – Approfondissement de l'IA interne

### 16. IA documentaire et juridique

- définir les sources et dossiers interrogeables ;
- appliquer strictement les permissions documentaires ;
- ajouter les questions-réponses par dossier, les résumés, comparaisons et extractions ;
- afficher les sources utilisées ;
- constituer un jeu de tests métier et mesurer la qualité des réponses avant généralisation.

Cette phase arrive en dernier car l'IA dépend de documents correctement rattachés, de référentiels fiables et de droits d'accès stabilisés.

## Résumé de l'ordre conseillé

1. Référentiel des sociétés.
2. Liaisons entre sociétés, dossiers et factures.
3. Retrait du type d'activité.
4. Simplification des statuts et règles des factures.
5. Documents multiples sur les dates clés.
6. Modèle financier nécessaire à la jauge.
7. Interfaces des dépenses et des actions.
8. Parcours et tri des factures.
9. Jauge budgétaire.
10. E-mail avec facture jointe.
11. Quatre signatures et mention « Fait à…, le… ».
12. Dashboard Finance.
13. Export ou liaison Excel.
14. Approfondissement de l'IA interne.
15. Activation future d'Outlook après obtention des autorisations Microsoft Entra.
