# Benjamin-Intranet

Ce projet est une **application web intranet** développée en **Python avec Django** et **PostegreSQL** pour gérer plusieurs
modules internes d’une organisation (authentification, gestion des employés, factures, recrutement, chatbot, signatures, etc.).

---

## Sommaire

- [À propos](#à-propos)
- [Fonctionnalités principales](#fonctionnalités-principales)
- [Structure du projet](#structure-du-projet)
- [Modules nécessaires](#modules-nécessaires)
- [Installation & configuration](#installation--configuration)
- [Lancement de l’application](#lancer-lapplication-et-les-crons)
- [Tâches planifiées (Cron)](#tâches-planifiées-cron)
- [Synchronisation mail](#synchronisation-mail)

---

## À propos

Dans le cadre de ce projet de **SAE5.01**, il nous a été donné comme mission de développer un **intranet** pour l’entreprise **Benjamin Immobilier**.
Cet outil serait divisé en **plusieurs pôles**, ayant chacun des fonctionnalités qui leur sont propres et ne seraient **accessibles**
qu’à certains **groupes de personnes selon leurs responsabilités** au sein de l’entreprise.
Le projet est construit avec Django et suit une **architecture modulaire** pour faciliter la maintenance et l’ajout de fonctionnalités.

---

## Fonctionnalités principales

| Module                 | Description                                               |
|------------------------|-----------------------------------------------------------|
| **Authentication**     | Système d’authentification des utilisateurs               |
| **Chatbot**            | Assistant interactif pour les utilisateurs                |
| **Home**               | Tableau de bord ou page d’accueil de l’intranet           |
| **Invoices**           | Gestion des factures                                      |
| **Management**         | Administration interne des utilisateurs/ressources        |
| **Recrutement**        | Module de suivi des recrutements                          |
| **Signatures**         | Gestion des signatures électroniques                      |
| **Technique**          | Gestion des documents techniques (contrats, permis, etc.) |
| **Static & Templates** | Ressources CSS/JS et templates HTML                       |

---

## Structure du projet

```
Benjamin-Intranet/
├── authentication/
├── chatbot/
├── config/
├── home/
├── invoices/
├── logs/           # contient les fichiers logs (1 par jour)
├── management/
├── media/          # contient les fichiers uploadés catégorisés
│   ├── documents/
│   ├── documents_tech/
│   ├── signatures/
│   └── tampons/
├── recrutement/
├── signatures/
├── static/
├── technique/
├── templates/
├── manage.py
├── requirements.txt
└── README.md
```

---

## Modules nécessaires

Les modules ainsi que leur version sont tous disponibles dans le fichier `requirements.txt` à la racine du dépôt.

| Package                          | Version |
|----------------------------------|---------|
| Django                           | 5.2.8   |
| django-celery-beat               | 2.8.1   |
| django-celery-results            | 2.5.0   |
| django_environ                   | 0.12.0  |
| django_mailbox                   | 4.10.1  |
| django-filter                    | 25.2    |
| PyPDF2                           | 3.0.1   |
| python_docx                      | 1.2.0   |
| reportlab                        | 4.4.4   |
| Requests                         | 2.32.5  |
| Pillow                           | 12.0.0  |
| pypdf                            | 6.3.0   |
| psycopg2-binary                  | 2.9.11  |
| celery                           | 5.3.4   |
| SQLAlchemy                       | 2.0.44  |
| django-two-factor-auth[call,sms] | 1.18.1  |
| phonenumbers                     | 9.0.21  |
| django-otp                       | 1.6.3   |
| django-axes                      | 8.1.0   |
| google-auth                      | 2.29.0  |
| google-auth-oauthlib             | 1.2.0   |
| google-api-python-client         | 2.122.0 |
| google-auth-httplib2             | 0.2.0   |
| pytest                           | 8.3.4   |
| pytest-django                    | 4.9.0   |
| pytest-cov                       | 6.0.0   |

---

## Installation & configuration

1. **Cloner le dépôt**

Dans un terminal :

```bash
git clone https://github.com/ALVARES-Titouan-2326003b/Benjamin-Intranet.git
cd Benjamin-Intranet
```

2. **Créer un environnement virtuel**

Dans un terminal, à la racine du projet :

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

3. **Installer les dépendances**

Dans un terminal, à la racine du projet :

```bash
pip install -r requirements.txt
```

3.5. **Créer la BD** (optionnel)

Si vous partez d'une BD vide, utilisez la branche `for_migration` pour créer les relations.  
**Cela ne créera aucun tuple, seulement les relations.**  
Dans un terminal, à la racine du projet :

```bash
git checkout for_migration
```

4. **Créer les dossiers pour accueillir les fichiers uploadés et les logs**

Dans un terminal, à la racine du projet :

````bash
mkdir logs
mkdir media
mkdir media{documents,documents_tech,signatures,tampons}
````

5. **Générer une clé secrète**

Dans un terminal, à la racine du projet :

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
>> cle_secrete
```

6. **Configurer les variables d’environnement**

Dans votre fichier `.env` placé à la racine du projet :

```env
# Les valeurs n'ont pas besoin d'être entre guillemets à part
# si elles contiennent au moins un espace


# Pour la connexion à votre base de données PostgreSQL
POSTGRES_DB=votre_bd_psql
POSTGRES_USER=votre_utilisateur
POSTGRES_PASSWORD=votre_mdp
POSTGRES_HOST=votre_serveur
POSTGRES_PORT=votre_port

# Pour l'API Groq
GROQ_API_KEY=votre_cle_groq

# Pour le chatbot
LEGIFRANCE_CLIENT_ID=votre_id_legifrance_api
LEGIFRANCE_CLIENT_SECRET=votre_cle_secrete_legifrance_api
LEGIFRANCE_ENV=sandbox

# API Google
GOOGLE_CLIENT_ID=votre_id_google_api
GOOGLE_CLIENT_SECRET=votre_cle_secrete_google_api
GOOGLE_REDIRECT_URI=url_redirection_apres_synchro # exemple : http://localhost:8000/oauth/callback/

# Pour la connexion à votre serveur de mail
EMAIL_HOST=votre_serveur_mail
EMAIL_PORT=votre_port_mail
EMAIL_USE_TLS=connexion_tls # True ou False
EMAIL_HOST_USER=votre_adresse_mail_serveur
EMAIL_HOST_PASSWORD=votre_mdp_mail_serveur
DEFAULT_FROM_EMAIL=adresse_mail_serveur_par_defaut # pour la communication avec le système par exemple


# force le HTTPS et désactive le debug
# laisser vide quand vous êtes en dev
# -> désactivera le HTTPS et activera le debug
DJANGO_ENV=production

# autorise votre machine à se connecter en localhost
# remplacer par votre vrai nom de domaine lors de la mise en ligne
# exemple :
# ALLOWED_HOSTS=benjamin-intranet.fr,www.benjamin-intranet.fr
ALLOWED_HOSTS=127.0.0.1,localhost


SECRET_KEY=cle_secrete_generee_a_letape_5

# liste des précédentes valeurs n'étant plus utilisées de SECRET_KEY séparées par des virgules
# exemple :
# SECRET_KEY_FALLBACKS=cle_secrete1,cle_secrete2,cle_secrete3
SECRET_KEY_FALLBACKS=
```

7. **Appliquer les migrations**

Dans un terminal, à la racine du projet :

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Lancer l’application et les Crons

Le lancement de l'application et des tâches planifiées (crons) est désormais automatisé.

Dans un terminal, à la racine du projet, exécutez simplement :

```bash
python start_intranet.py
```

Ce script démarre automatiquement **tous les services nécessaires** :
1. **Le serveur Django** (Interface web accessible sur http://127.0.0.1:8000/)
2. **Celery Worker** (Exécution des tâches)
3. **Celery Beat** (Planification des tâches)

---

## Tâches planifiées (Cron)

Grâce au script `start_intranet.py`, vous n'avez plus besoin de lancer manuellement les commandes Celery.
Les tâches crons suivantes seront exécutées automatiquement en arrière-plan :

- **Relance factures**
- **Relance activités**
- **Relance mail**

---

## Synchronisation mail

De par la nature de la relance mail, la mise en place d’une boite mail est nécessaire. **Le domaine du client est hébergé par
Microsoft**, nous utilisons donc l’api `Microsoft Graph` avec l’outil `Entra`
(nécessite de rejoindre le Microsoft 365 Developer Program).  
Depuis `Entra`, nous ajoutons le projet parmi les applications du compte, le paramétrons
en fonction des besoins puis donnons les permissions aux utilisateurs du tenant.  
Or, pour ce projet, **n’ayant pas eu accès au tenant du client en tant qu’administrateur, nous n’avons pas pu définir d’autorisations
ou ajouter notre projet**. Cela **reste donc à implémenter** ; à noter que la synchronisation boîte mail par Microsoft est fonctionnelle
mais que toute fonctionnalité au-delà de cette étape n’a pas pu être testée,
telles que la récupération de la boîte "Éléments envoyés" et "Boîte de réception" de l’adresse mail.