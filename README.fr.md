# 🎛️ Orchestrateur Immo-Boussole

[![CI](https://github.com/Immo-Boussole/immo-boussole-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/Immo-Boussole/immo-boussole-orchestrator/actions/workflows/ci.yml)
[![Docker Hub](https://img.shields.io/badge/docker-hub-blue.svg?logo=docker&logoColor=white)](https://hub.docker.com/repository/docker/wikijm/immo-boussole-orchestrator/general)
[![Documentation Wiki](https://img.shields.io/badge/docs-GitHub%20Wiki-blue?logo=github)](https://github.com/Immo-Boussole/immo-boussole/wiki)

> 🧭 **Organisation Immo-Boussole** : [Application Web](https://github.com/Immo-Boussole/immo-boussole) • [Extension Web](https://github.com/Immo-Boussole/immo-boussole-extension) • [Orchestrateur](https://github.com/Immo-Boussole/immo-boussole-orchestrator) • [Wiki Central](https://github.com/Immo-Boussole/immo-boussole/wiki)

---

## 🌐 Langues

- 🇬🇧 [English (Default)](README.md)
- 🇫🇷 [Français](README.fr.md)

---

> **Orchestrateur web et en ligne de commande (CLI)** pour déployer, administrer, surveiller et mettre à jour plusieurs instances [Immo-Boussole](https://github.com/Immo-Boussole/immo-boussole) sur des hôtes Docker locaux ou distants — depuis n'importe quel système (Windows, Linux, macOS).

---

## ✨ Vue d'Ensemble

L'**Orchestrateur Immo-Boussole** est le centre de commande de votre flotte d'instances Immo-Boussole. Que vous gériez une instance de développement sur votre PC portable, un environnement de test sur un serveur dédié ou plusieurs déploiements de production, cet outil vous offre une interface unique et unifiée.

Il communique directement avec les démons Docker — localement via socket Unix/TCP ou à distance via tunnel SSH ou TLS — et peut lui-même être exécuté dans un conteneur Docker.

---

## 🚀 Fonctionnalités Clés

- **Gestion multi-instances** — Créer, démarrer, arrêter, redémarrer, mettre à jour et supprimer des instances Immo-Boussole
- **Support multi-hôtes** — Connexion aux démons Docker locaux ou distants (SSH, TCP/TLS)
- **Surveillance en temps réel** — État de santé, uptime et streaming des logs par conteneur
- **Sauvegarde & Restauration** — Déclencher des backups et restores via l'API Immo-Boussole
- **Clonage d'instance** — Dupliquer une instance complète (configuration + données) en une commande
- **Flexibilité des images** — Utiliser les images officielles Docker Hub ou construire depuis les sources locales
- **Interface Web** — Tableau de bord moderne avec thème sombre/clair
- **CLI** — Interface en ligne de commande complète (commande `orchestrator`)
- **Notifications** — Alertes d'état par Webhook (POST JSON générique) et e-mail (SMTP)
- **Serveur MCP** — Serveur Model Context Protocol pour piloter vos instances via Claude Desktop ou tout outil LLM
- **Authentification** — Authentification HTTP Basic pour l'interface web
- **CI/CD** — Pipeline GitHub Actions : tests + publication automatique de l'image Docker Hub

---

## 📚 Documentation Complète & Guides Wiki

Des guides détaillés d'administration et d'exploitation sont disponibles sur le **[Wiki Central GitHub](https://github.com/Immo-Boussole/immo-boussole/wiki)** :

| Guide | Description | Lien |
|---|---|---|
| 🎛️ **Guide de l'Orchestrateur** | Déploiement de flotte, commandes CLI, serveurs Docker distants SSH/TCP | [Consulter le Guide](https://github.com/Immo-Boussole/immo-boussole/wiki/Orchestrator-Setup-FR) |
| 🧭 **Architecture & Écosystème** | Fonctionnement conjoint de l'App Principale, de l'Extension et de l'Orchestrateur | [Consulter le Guide](https://github.com/Immo-Boussole/immo-boussole/wiki/Architecture-Overview-FR) |
| 🐳 **Installation Docker (App Principale)** | Déploiement autonome de l'application avec Docker Compose | [Consulter le Guide](https://github.com/Immo-Boussole/immo-boussole/wiki/Installation-Docker-FR) |

---

## 🏗️ Stack Technique

| Composant | Technologie |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **CLI** | Typer |
| **Contrôle Docker** | `python-on-whales` (Docker SDK) |
| **Stockage Config** | YAML (`instances.yaml`) |
| **Frontend** | HTML5, Vanilla CSS, templates Jinja2 |
| **Notifications** | HTTPX (webhook), `aiosmtplib` (SMTP) |
| **MCP** | Bibliothèque `mcp` (Model Context Protocol) |
| **Conteneurisation** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |

---

## ⚡ Démarrage Rapide

### 1. Avec Docker (Recommandé)

```bash
# Télécharger et lancer l'orchestrateur
docker compose -f docker-compose.hub.yml up -d
```

L'interface web est immédiatement accessible sur **[http://localhost:9000](http://localhost:9000)**.

### 2. Développement Local en Python

```bash
# 1. Cloner le dépôt
git clone https://github.com/Immo-Boussole/immo-boussole-orchestrator.git
cd immo-boussole-orchestrator

# 2. Configurer l'environnement virtuel
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configuration
cp .env.example .env
# Éditer .env selon vos paramètres

# 5. Lancer le serveur web
python -m uvicorn app.main:app --reload --port 9000

# Ou utiliser la CLI
python -m orchestrator --help
```

---

## 🖥️ Utilisation de la CLI

```bash
# Lister toutes les instances enregistrées
orchestrator list

# Ajouter une nouvelle instance
orchestrator add --name prod --host ssh://user@myserver --port 8000 --image wikijm/immo-boussole:latest

# Démarrer / arrêter / redémarrer
orchestrator start prod
orchestrator stop prod
orchestrator restart prod

# Mettre à jour vers une nouvelle version d'image
orchestrator update prod --tag 1.2.3

# Suivre les journaux (logs) en temps réel
orchestrator logs prod --follow

# Cloner une instance existante
orchestrator clone prod staging

# Supprimer une instance (conserver les volumes de données)
orchestrator remove prod --keep-volumes

# Déclencher une sauvegarde
orchestrator backup prod

# Ouvrir l'interface web dans le navigateur
orchestrator ui
```

---

## ⚙️ Configuration

### `.env` — Paramètres de l'orchestrateur

| Variable | Défaut | Description |
|---|---|---|
| `SECRET_KEY` | *(requis)* | Clé de signature des sessions |
| `ADMIN_USERNAME` | `admin` | Nom d'utilisateur de l'interface web |
| `ADMIN_PASSWORD` | *(requis)* | Mot de passe de l'interface web |
| `ORCHESTRATOR_PORT` | `9000` | Port d'écoute du serveur web |
| `INSTANCES_FILE` | `instances.yaml` | Chemin du registre des instances |
| `NOTIFICATION_WEBHOOK_URL` | *(optionnel)* | URL de webhook pour les alertes |
| `SMTP_HOST` | *(optionnel)* | Serveur SMTP pour les alertes e-mail |
| `SMTP_PORT` | `587` | Port SMTP |
| `SMTP_USERNAME` | *(optionnel)* | Identifiant SMTP |
| `SMTP_PASSWORD` | *(optionnel)* | Mot de passe SMTP |
| `SMTP_FROM` | *(optionnel)* | Adresse e-mail d'expédition |
| `SMTP_TO` | *(optionnel)* | Destinataire(s) des alertes |

### `instances.yaml` — Registre des instances

```yaml
instances:
  - name: dev
    host: local          # ou ssh://user@host, tcp://host:2376
    port: 8000
    image: wikijm/immo-boussole:latest
    env_file: ./envs/dev.env
    tls_cert: null       # chemin vers le certificat TLS pour hôtes TCP

  - name: prod
    host: ssh://deploy@myserver.com
    port: 8100
    image: wikijm/immo-boussole:1.2.3
    env_file: ./envs/prod.env
```

---

## 🔌 Serveur MCP

L'orchestrateur intègre un serveur MCP sur le port `9001` pour la connexion avec Claude Desktop et les outils IA :

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "immo-boussole-orchestrator": {
      "url": "http://localhost:9001/sse"
    }
  }
}
```

Outils MCP disponibles : `list_instances`, `start_instance`, `stop_instance`, `restart_instance`, `get_instance_status`, `get_instance_logs`, `update_instance`, `create_instance`, `delete_instance`, `backup_instance`.

---

## 🧪 Tests

```bash
# Exécuter tous les tests
python tests/run_tests.py

# Mode CI
python tests/run_tests.py --ci
```

---

## 🐳 Hôtes Docker — Connectivité

| Type de Cible | Chaîne de Connexion | Remarques |
|---|---|---|
| Local (Linux/macOS) | `local` ou `unix:///var/run/docker.sock` | Par défaut |
| Local (Windows) | `npipe:////./pipe/docker_engine` | Docker Desktop |
| SSH Distant | `ssh://user@hostname` | Clé SSH recommandée |
| TCP/TLS Distant | `tcp://hostname:2376` | Nécessite des certificats TLS |

---

## 📄 Licence

Ce projet est sous licence open-source. Consultez [LICENSE](LICENSE) pour plus de détails.

---

*Fait partie de l'organisation [Immo-Boussole](https://github.com/Immo-Boussole).*
