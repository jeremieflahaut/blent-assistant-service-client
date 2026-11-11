#!/usr/bin/env bash
# Installe et lance l'assistant de service client, depuis un clone vierge du dépôt.
# Relançable sans risque : chaque étape déjà faite est sautée.
#
#   ./run.sh                                     # modèle choisi dans .env
#   OLLAMA_MODEL=ministral-3:3b ./run.sh         # autre modèle, sans toucher au .env
set -euo pipefail
cd "$(dirname "$0")"

OLLAMA_URL="http://localhost:11434"

# 1. Configuration : .env créé depuis l'exemple (date du jour simulée, modèle)
if [ ! -f .env ]; then
    cp .env.example .env
    echo "→ .env créé depuis .env.example"
fi
# Une variable déjà définie dans le terminal l'emporte sur le .env, comme dans l'application
if [ -z "${OLLAMA_MODEL:-}" ]; then
    OLLAMA_MODEL=$(grep '^OLLAMA_MODEL=' .env | cut -d= -f2- | tr -d "\"'")
fi
: "${OLLAMA_MODEL:?OLLAMA_MODEL manquant dans .env}"

# 2. Ollama : installé s'il est absent
if ! command -v ollama > /dev/null; then
    echo "→ Installation d'Ollama"
    curl -fsSL https://ollama.com/install.sh | sh
fi

# 3. Serveur Ollama : démarré en arrière-plan s'il ne répond pas
if ! curl -fs "$OLLAMA_URL/api/version" > /dev/null; then
    echo "→ Démarrage du serveur Ollama (journal : /tmp/ollama.log)"
    # setsid : le serveur ne dépend pas du script, Ctrl+C sur Streamlit ne l'arrête pas
    setsid nohup ollama serve > /tmp/ollama.log 2>&1 &
    for _ in $(seq 30); do
        curl -fs "$OLLAMA_URL/api/version" > /dev/null && break
        sleep 1
    done
    curl -fs "$OLLAMA_URL/api/version" > /dev/null || {
        echo "Le serveur Ollama ne répond pas : voir /tmp/ollama.log" >&2
        exit 1
    }
fi

# 4. Modèle : téléchargé s'il est absent (9 Go pour ministral-3:14b)
if ! ollama show "$OLLAMA_MODEL" > /dev/null 2>&1; then
    echo "→ Téléchargement du modèle $OLLAMA_MODEL"
    ollama pull "$OLLAMA_MODEL"
fi

# 5. Dépendances Python : environnement isolé géré par uv (uv.lock)
if ! command -v uv > /dev/null; then
    echo "→ Installation de uv"
    pip install --quiet uv
fi
uv sync

# 6. Interface : http://localhost:8501 (headless : pas de navigateur ni de question
# au premier lancement)
echo "→ Lancement de l'assistant avec $OLLAMA_MODEL"
OLLAMA_MODEL="$OLLAMA_MODEL" exec uv run streamlit run app.py --server.headless true
