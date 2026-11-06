"""Essai de l'agent complet sur le jeu de test, avec le modèle servi par Ollama.

Pour chaque cas à un seul message de cas.json, l'agent reçoit la question du client et
décide lui-même d'appeler l'outil ou non. Chaque réponse passe les vérifications
automatiques du cas (tests/eval/verifs.py) ; le rapport Markdown (tests/eval/resultats/)
donne le score, puis le détail des réponses à relire.

Même à température 0.05, une même question donne des réponses différentes d'un appel à
l'autre : --repeat joue chaque cas plusieurs fois (graine 1, 2, …) pour distinguer un
défaut régulier d'un accident.

Prérequis : serveur Ollama démarré, modèle téléchargé (OLLAMA_MODEL dans le .env).
Depuis la racine du dépôt :
    uv run python -m tests.eval.essai_prompt                # tous les cas, une fois
    uv run python -m tests.eval.essai_prompt --repeat 3     # tous les cas, trois fois
    uv run python -m tests.eval.essai_prompt 18 19          # seulement les cas 18 et 19
"""

import argparse
import json
import time
from datetime import date, datetime
from pathlib import Path

from langchain_core.messages import AIMessage

from agent import Context, build_agent
from config import get_model_name, get_today
from customers import list_customers
from llm import GENERATION, build_model
from tests.eval.verifs import check, dates_in, numbers_in
from tools import french_date, get_customer_orders_and_address

EVAL_DIR = Path(__file__).parent


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


def known_facts(user_id: int, today: date) -> tuple[set[str], set[str]]:
    """Dates et nombres que le bot a le droit de citer : ceux des données du client
    (commandes, durées, adresse), le nombre de ses commandes et la date du jour."""
    result = get_customer_orders_and_address(user_id)
    facts = (
        json.dumps(result, ensure_ascii=False) + " " + french_date(today.isoformat())
    )
    return dates_in(facts), numbers_in(facts) | {str(len(result["orders"]))}


def write_report(path: Path, today: date, repeat: int, rows: list) -> None:
    lines = [
        f"# Essai de l'agent — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Modèle : `{get_model_name()}` (Ollama) · date du jour : {today} · "
        f"réglages : `{GENERATION}` · répétitions : {repeat} (graines 1 à {repeat})",
        "",
        "## Score",
        "",
    ]
    for index in range(repeat):
        passed = sum(
            not runs[index]["failures"] for _, runs in rows if index < len(runs)
        )
        lines.append(f"- Répétition {index + 1} : **{passed}/{len(rows)}**")
    lines += [
        "",
        "Cas à plusieurs messages (29, 30) : non joués par ce script. Le ton n'est pas "
        "noté : voir les points « À relire ».",
        "",
        "| Cas | Réussites | Échecs relevés |",
        "|---|---|---|",
    ]
    for case, runs in rows:
        passed = sum(not run["failures"] for run in runs)
        failures = sorted({failure for run in runs for failure in run["failures"]})
        lines.append(
            f"| {case['id']} | {passed}/{len(runs)} | {' ; '.join(failures)} |"
        )
    lines.append("")

    for case, runs in rows:
        lines += [
            f"## Cas {case['id']} — {case['etape']} ({case['client']})",
            "",
            f"**Message** : {case['messages'][0]}",
            "",
            "**Attendu** : " + " ; ".join(case["attendu"]),
            "",
        ]
        if "a_relire" in case.get("verifs", {}):
            lines += [f"**À relire** : {case['verifs']['a_relire']}", ""]
        for index, run in enumerate(runs, start=1):
            verdict = (
                "✅" if not run["failures"] else "❌ " + " ; ".join(run["failures"])
            )
            calls = ", ".join(run["tool_calls"]) or "aucun"
            lines += [
                f"**Répétition {index}** ({run['duration']:.1f} s) · appels d'outil : "
                f"{calls} · {verdict}",
                "",
            ]
            lines += ["> " + line for line in run["answer"].splitlines()] + [""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cas", nargs="*", type=int, help="numéros des cas à jouer")
    parser.add_argument("--repeat", type=int, default=1, help="répétitions par cas")
    args = parser.parse_args()

    data = json.loads((EVAL_DIR / "cas.json").read_text(encoding="utf-8"))
    cases = [
        case
        for case in data["cas"]
        if len(case["messages"]) == 1 and (not args.cas or case["id"] in args.cas)
    ]
    customers = {customer["user_id"]: customer for customer in list_customers()}
    today = get_today()
    print(
        f"Modèle : {get_model_name()} · date du jour : {today} · {len(cases)} cas "
        f"× {args.repeat} répétition(s)"
    )

    path = EVAL_DIR / "resultats" / f"essai-agent-{datetime.now():%Y%m%d-%H%M}.md"
    path.parent.mkdir(exist_ok=True)

    models = [build_model(seed=seed) for seed in range(1, args.repeat + 1)]
    rows = []
    for case in cases:
        customer = customers[data["clients"][case["client"]]["user_id"]]
        dates, numbers = known_facts(customer["user_id"], today)
        runs = []
        for model in models:
            run = run_case(model, customer, case["messages"][0], today)
            run["failures"] = check(
                case,
                run["answer"],
                run["tool_calls"],
                data["interdits_globaux"],
                dates,
                numbers,
            )
            runs.append(run)
        rows.append((case, runs))
        passed = sum(not run["failures"] for run in runs)
        print(f"Cas {case['id']} : {passed}/{len(runs)} réussite(s)")
        write_report(path, today, args.repeat, rows)  # réécrit à chaque cas

    for index in range(args.repeat):
        passed = sum(not runs[index]["failures"] for _, runs in rows)
        print(f"Score, répétition {index + 1} : {passed}/{len(rows)}")
    print(f"Rapport : {path}")


if __name__ == "__main__":
    main()
