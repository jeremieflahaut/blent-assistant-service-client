"""Essai de l'agent complet sur le jeu de test, avec le modèle servi par Ollama.

Pour chaque cas à un seul message de cas.json, l'agent reçoit la question du client et
décide lui-même d'appeler l'outil ou non. Les appels d'outil, les réponses et les
erreurs éventuelles sont écrits dans un rapport Markdown (tests/eval/resultats/) à
relire.

Prérequis : serveur Ollama démarré, modèle téléchargé (OLLAMA_MODEL dans le .env).
Depuis la racine du dépôt :
    uv run python -m tests.eval.essai_prompt
"""

import json
import re
import time
from datetime import date, datetime
from pathlib import Path

from langchain_core.messages import AIMessage

from agent import Context, build_agent
from config import get_model_name, get_today
from customers import list_customers
from llm import GENERATION, build_model

EVAL_DIR = Path(__file__).parent
RAW_STATUS = re.compile(r"\b(invoiced|shipped|delivered)\b", re.IGNORECASE)


def run_case(model, customer: dict, question: str, today: date) -> dict:
    agent = build_agent(model, customer["first_name"], customer["last_name"], today)
    start = time.perf_counter()
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            context=Context(user_id=customer["user_id"]),
        )
    except Exception as error:  # un cas en erreur ne doit pas arrêter l'essai
        duration = time.perf_counter() - start
        return {"duration": duration, "tool_calls": [], "answer": f"ERREUR : {error}"}
    messages = result["messages"]
    return {
        "duration": time.perf_counter() - start,
        "tool_calls": [
            f"{call['name']}({json.dumps(call['args'], ensure_ascii=False)})"
            for message in messages
            if isinstance(message, AIMessage)
            for call in message.tool_calls
        ],
        "answer": messages[-1].content,
    }


def write_report(path: Path, today: date, rows: list) -> None:
    lines = [
        f"# Essai de l'agent — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Modèle : `{get_model_name()}` (Ollama) · date du jour : {today} · "
        f"réglages : `{GENERATION}`",
        "",
    ]
    for case, run in rows:
        lines += [
            f"## Cas {case['id']} — {case['etape']} ({case['client']})",
            "",
            f"**Message** : {case['messages'][0]}",
            "",
            "**Attendu** : " + " ; ".join(case["attendu"]),
            "",
        ]
        calls = ", ".join(run["tool_calls"]) or "aucun"
        flag = " · ⚠️ code brut de statut" if RAW_STATUS.search(run["answer"]) else ""
        lines += [
            f"**Réponse** ({run['duration']:.1f} s) · appels d'outil : {calls}{flag}",
            "",
        ]
        lines += ["> " + line for line in run["answer"].splitlines()] + [""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    data = json.loads((EVAL_DIR / "cas.json").read_text(encoding="utf-8"))
    cases = [case for case in data["cas"] if len(case["messages"]) == 1]
    customers = {customer["user_id"]: customer for customer in list_customers()}
    today = get_today()
    print(f"Modèle : {get_model_name()} · date du jour : {today} · {len(cases)} cas")

    path = EVAL_DIR / "resultats" / f"essai-agent-{datetime.now():%Y%m%d-%H%M}.md"
    path.parent.mkdir(exist_ok=True)

    model = build_model()
    rows = []
    for case in cases:
        customer = customers[data["clients"][case["client"]]["user_id"]]
        run = run_case(model, customer, case["messages"][0], today)
        rows.append((case, run))
        print(f"Cas {case['id']} : {run['duration']:.1f} s · {run['tool_calls']}")
        write_report(path, today, rows)  # réécrit à chaque cas : rien n'est perdu

    print(f"Rapport : {path}")


if __name__ == "__main__":
    main()
