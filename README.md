# Assistant de service client

[![CI](https://github.com/jeremieflahaut/blent-assistant-service-client/actions/workflows/ci.yml/badge.svg)](https://github.com/jeremieflahaut/blent-assistant-service-client/actions/workflows/ci.yml)

## Templates de prompts

Le livrable de l'étape 3 est dans [`docs/templates-prompts.md`](docs/templates-prompts.md).
Il contient le routage sémantique (phrases de référence, seuil, réponse aux questions hors
sujet), le prompt système, la description de l'outil envoyée au modèle et le format de son
résultat.

## Lancer le projet

Dans la Cloud Sandbox Blent :

```bash
git clone https://github.com/jeremieflahaut/blent-assistant-service-client.git
cd blent-assistant-service-client
./run.sh
```

`run.sh` crée le `.env`, installe et démarre Ollama, télécharge le modèle de chat
(`mistral-small3.2:24b`, 15 Go) et le modèle d'embedding (`paraphrase-multilingual:278m`,
563 Mo), installe les dépendances avec uv, puis lance Streamlit sur le port 8501. On peut le
relancer sans risque : les étapes déjà faites sont sautées.

Le chat s'ouvre par le relais du VS Code web de la sandbox. `run.sh` affiche l'adresse :

```
https://<identifiant>-8081.proxy.runpod.net/proxy/8501/
```

Hors sandbox : http://localhost:8501.

Choisir ensuite un client dans le menu de gauche (connexion simulée), puis poser une
question. Par exemple, avec Ashton Frederick : « Où en est ma commande 22 ? ».

Prérequis : Linux, Python 3.11, `curl` et un GPU NVIDIA avec environ 16 Go de mémoire.
