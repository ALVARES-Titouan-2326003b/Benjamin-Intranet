# Guide de mise en production

La cible de référence utilise Docker Compose avec cinq rôles séparés : Nginx,
Django/Gunicorn, Celery Worker, Celery Beat, PostgreSQL et Redis.

## 1. Préparer l'hôte

- Installer Docker Engine et le plugin Docker Compose.
- Autoriser uniquement les ports 22, 80 et 443 au pare-feu.
- Pointer le DNS du domaine vers l'hôte.
- Déposer le certificat dans `deploy/certs/fullchain.pem` et sa clé privée dans
  `deploy/certs/privkey.pem`. Ces fichiers sont ignorés par Git.

## 2. Préparer les secrets

Copier `.env.production.example` vers `.env.production`, puis remplacer toutes
les valeurs factices. Ne jamais versionner ce fichier.

Générer les deux secrets principaux :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`FIELD_ENCRYPTION_KEY` chiffre les jetons OAuth stockés en base. Sa perte rend
les jetons illisibles. Lors d'une rotation, déplacer l'ancienne clé dans
`FIELD_ENCRYPTION_KEY_FALLBACKS`, déployer, réenregistrer les secrets, puis
retirer l'ancienne clé après vérification.

Pour une base PostgreSQL située dans le réseau Docker local, conserver
`POSTGRES_SSLMODE=prefer`. Pour une base managée distante, utiliser `require`
ou le mode imposé par le fournisseur.

## 3. Vérifier avant le premier déploiement

```bash
docker compose config --quiet
docker compose build
docker compose run --rm web python manage.py check --deploy --fail-level WARNING
docker compose run --rm web python manage.py makemigrations --check --dry-run
```

Configurer dans Google OAuth l'URI exacte
`https://VOTRE_DOMAINE/oauth/callback/`.

Déposer le classeur de suivi dans `data/excel/` sur l'hôte, vérifier que son
propriétaire autorise l'écriture par le conteneur, puis renseigner
`INVOICE_EXCEL_SYNC_PATH=/data/shared/NOM_DU_FICHIER.xlsx`. Le nom de feuille et
la ligne d'en-tête doivent correspondre au fichier existant. Conserver
`INVOICE_EXCEL_SYNC_CREATE_IF_MISSING=False` pour éviter de créer silencieusement
un second classeur à la suite d'une erreur de chemin.

Après sauvegarde du classeur original, effectuer le raccordement initial :

```bash
docker compose exec web python manage.py sync_invoices_excel
```

## 4. Déployer

```bash
sh deploy/release.sh
```

Le service `migrate` applique les migrations puis exécute `collectstatic` avant
le démarrage du Web, du Worker et de Beat. Vérifier ensuite :

```bash
curl --fail https://VOTRE_DOMAINE/health/live/
curl --fail https://VOTRE_DOMAINE/health/ready/
docker compose ps
docker compose logs --tail=200 web worker beat nginx
```

Créer le premier administrateur uniquement au premier déploiement :

```bash
docker compose exec web python manage.py createsuperuser
```

## 5. Sauvegarde et restauration

Créer une sauvegarde cohérente de PostgreSQL et des médias :

```bash
BACKUP_DIR=/chemin/hors-du-serveur sh deploy/backup.sh
```

Copier les sauvegardes vers un stockage externe chiffré et immuable. Tester la
restauration régulièrement sur une instance isolée :

```bash
sh deploy/restore.sh --confirm database.dump media.tar.gz
```

La restauration remplace la base et les médias courants. Elle arrête les
processus applicatifs pendant l'opération.

Objectifs initiaux conseillés : sauvegarde quotidienne, rétention 30 jours,
RPO 24 heures et RTO 4 heures. Les adapter aux exigences métier.

## 6. Retour arrière

1. Ne jamais inverser une migration sans avoir lu sa fonction inverse.
2. Sauvegarder avant chaque release.
3. Revenir au tag d'image précédent avec `APP_IMAGE_TAG`.
4. Restaurer la base uniquement si la migration n'est pas compatible avec
   l'ancienne version.
5. Vérifier les sondes et les parcours connexion, factures, documents,
   signatures, Gmail et tâches planifiées.

## 7. Supervision minimale

Surveiller : disponibilité des deux sondes, codes HTTP 5xx, latence, espace
disque, connexions PostgreSQL, mémoire Redis, files Celery, échecs de tâches,
expiration OAuth, erreurs SMTP et expiration TLS. Les logs applicatifs sont
émis sur stdout et doivent être collectés par la plateforme d'hébergement.
Renseigner `SENTRY_DSN` active automatiquement la remontée des erreurs Django et
Celery sans envoyer les données personnelles par défaut.

## 8. Checklist de recette

- Authentification, blocage Axes et second facteur.
- Invitations et réinitialisations de mots de passe.
- Téléversement et consultation authentifiée des médias.
- Création et export des factures.
- Création puis modification d'une facture avec contrôle de la ligne Excel et
  de l'historique de synchronisation.
- Signature simple et multi-signataires.
- OAuth Gmail, synchronisation, envoi et révocation.
- Traitement asynchrone d'un document et exécution de Beat.
- Sauvegarde puis restauration sur une instance isolée.
- Absence de secret ou de donnée personnelle dans les logs.
