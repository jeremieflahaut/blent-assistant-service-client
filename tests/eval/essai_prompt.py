"""Essai de l'agent complet sur le jeu de test, avec le modèle servi par Ollama.

Chaque cas de cas.json est joué comme dans l'application : une conversation avec
mémoire, la réponse diffusée au fil de la génération (agent.stream_reply). L'agent
décide lui-même d'appeler l'outil ou non. Les cas à plusieurs messages (29, 30, 34)
enchaînent leurs messages dans la même conversation ; seule la dernière réponse est
notée. Chaque réponse notée passe les vérifications automatiques du cas
(tests/eval/verifs.py) ; le rapport Markdown (tests/eval/resultats/) donne le score, le
temps jusqu'au premier mot, puis le détail des réponses à relire.

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
import statistics
import time
from datetime import date, datetime
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent import build_agent, stream_reply
from config import get_model_name, get_today
from customers import list_customers
from llm import GENERATION, build_model
from tests.eval.verifs import check, dates_in, numbers_in
from tools import french_date, get_customer_orders

EVAL_DIR = Path(__file__).parent
THREAD_ID = "essai"
FIRST_WORD_TARGET = 2.0


def run_turn(agent, user_id: int, question: str) -> dict:
    """Un message du client : réponse diffusée comme dans l'app, chronométrée."""
    start = time.perf_counter()
    first_word = None
    chunks = []
    try:
        for text in stream_reply(agent, question, user_id, THREAD_ID, lambda: None):
            if first_word is None:
                first_word = time.perf_counter() - start
            chunks.append(text)
    except Exception as error:
        return {
            "question": question,
            "duration": time.perf_counter() - start,
            "first_word": None,
            "tool_calls": [],
            "answer": f"ERREUR : {error}",
        }
    duration = time.perf_counter() - start

    config = {"configurable": {"thread_id": THREAD_ID}}
    messages = agent.get_state(config).values["messages"]
    last = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
    return {
        "question": question,
        "duration": duration,
        "first_word": first_word,
        "tool_calls": [
            f"{call['name']}({json.dumps(call['args'], ensure_ascii=False)})"
            for message in messages[last + 1 :]
            if isinstance(message, AIMessage)
            for call in message.tool_calls
        ],
        "answer": "".join(chunks),
    }


def run_case(model, customer: dict, messages: list[str], today: date) -> list[dict]:
    """Joue les messages d'un cas dans une même conversation ; renvoie chaque tour."""
    agent = build_agent(
        model,
        customer["first_name"],
        customer["last_name"],
        today,
        checkpointer=InMemorySaver(),
    )
    turns = []
    for question in messages:
        turns.append(run_turn(agent, customer["user_id"], question))
        if turns[-1]["answer"].startswith("ERREUR"):
            break
    return turns


def known_facts(user_id: int, today: date) -> tuple[set[str], set[str], int]:
    """Dates et nombres que le bot a le droit de citer : ceux des commandes du client
    (numéros, dates, durées), le nombre de ses commandes et la date du jour ; puis le
    nombre de commandes, pour accepter les comptages (« 2 commandes »)."""
    orders = get_customer_orders(user_id)
    today_label = french_date(today.isoformat())
    facts = json.dumps(orders, ensure_ascii=False) + " " + today_label
    return dates_in(facts), numbers_in(facts) | {str(len(orders))}, len(orders)


def score_line(rows: list, index: int) -> str:
    """Score d'une répétition : tous les cas, puis ceux exigés par le brief."""
    results = [(case["brief"], not runs[index]["failures"]) for case, runs in rows]
    brief = [passed for is_brief, passed in results if is_brief]
    total = sum(passed for _, passed in results)
    return f"**{total}/{len(results)}** (cas du brief : **{sum(brief)}/{len(brief)}**)"


def first_word_line(label: str, turns: list[dict]) -> str:
    """Temps jusqu'au premier mot d'un groupe de réponses : médiane, maximum."""
    times = [turn["first_word"] for turn in turns if turn["first_word"] is not None]
    if not times:
        return f"- {label} : aucune réponse"
    on_target = sum(t < FIRST_WORD_TARGET for t in times)
    return (
        f"- {label} ({len(times)} réponses) : "
        f"médiane **{statistics.median(times):.1f} s**,"
        f" maximum {max(times):.1f} s, moins de {FIRST_WORD_TARGET:.0f} s : "
        f"{on_target}/{len(times)}"
    )


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
        lines.append(f"- Répétition {index + 1} : {score_line(rows, index)}")

    turns = [turn for _, runs in rows for run in runs for turn in run["turns"]]
    lines += [
        "",
        "## Temps jusqu'au premier mot",
        "",
        "Mesuré comme dans l'application (réponse diffusée), modèle déjà chargé.",
        "",
        first_word_line("Avec appel d'outil", [t for t in turns if t["tool_calls"]]),
        first_word_line(
            "Sans appel d'outil", [t for t in turns if not t["tool_calls"]]
        ),
        "",
        "Cas à plusieurs messages : joués dans une même conversation, seule la "
        "dernière réponse est notée. Le ton n'est pas noté : voir les points "
        "« À relire ».",
        "",
        "| Cas | Brief | Réussites | Échecs relevés |",
        "|---|---|---|---|",
    ]
    for case, runs in rows:
        passed = sum(not run["failures"] for run in runs)
        failures = " ; ".join(
            sorted({failure for run in runs for failure in run["failures"]})
        )
        brief = "oui" if case["brief"] else "ajout"
        lines.append(f"| {case['id']} | {brief} | {passed}/{len(runs)} | {failures} |")
    lines.append("")

    for case, runs in rows:
        lines += [f"## Cas {case['id']} — {case['etape']} ({case['client']})", ""]
        for number, message in enumerate(case["messages"], start=1):
            label = "Message" if len(case["messages"]) == 1 else f"Message {number}"
            lines += [f"**{label}** : {message}", ""]
        lines += ["**Attendu** : " + " ; ".join(case["attendu"]), ""]
        if "a_relire" in case.get("verifs", {}):
            lines += [f"**À relire** : {case['verifs']['a_relire']}", ""]
        for index, run in enumerate(runs, start=1):
            verdict = (
                "✅" if not run["failures"] else "❌ " + " ; ".join(run["failures"])
            )
            lines += [f"**Répétition {index}** · {verdict}", ""]
            for number, turn in enumerate(run["turns"], start=1):
                calls = ", ".join(turn["tool_calls"]) or "aucun"
                first_word = (
                    f"{turn['first_word']:.1f} s"
                    if turn["first_word"] is not None
                    else "—"
                )
                prefix = (
                    "" if len(run["turns"]) == 1 else f"Réponse au message {number} · "
                )
                lines += [
                    f"{prefix}premier mot {first_word} · réponse complète "
                    f"{turn['duration']:.1f} s · appels d'outil : {calls}",
                    "",
                ]
                lines += ["> " + line for line in turn["answer"].splitlines()] + [""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cas", nargs="*", type=int, help="numéros des cas à jouer")
    parser.add_argument("--repeat", type=int, default=1, help="répétitions par cas")
    args = parser.parse_args()

    data = json.loads((EVAL_DIR / "cas.json").read_text(encoding="utf-8"))
    cases = [case for case in data["cas"] if not args.cas or case["id"] in args.cas]
    customers = {customer["user_id"]: customer for customer in list_customers()}
    today = get_today()
    print(
        f"Modèle : {get_model_name()} · date du jour : {today} · {len(cases)} cas "
        f"× {args.repeat} répétition(s)"
    )

    path = EVAL_DIR / "resultats" / f"essai-agent-{datetime.now():%Y%m%d-%H%M}.md"
    path.parent.mkdir(exist_ok=True)

    models = [build_model(seed=seed) for seed in range(1, args.repeat + 1)]
    print("Chargement du modèle…")
    models[0].invoke("Bonjour")

    rows = []
    for case in cases:
        customer = customers[data["clients"][case["client"]]["user_id"]]
        dates, numbers, order_count = known_facts(customer["user_id"], today)
        runs = []
        for model in models:
            turns = run_case(model, customer, case["messages"], today)
            last = turns[-1]
            failures = check(
                case,
                last["answer"],
                last["tool_calls"],
                data["interdits_globaux"],
                dates,
                numbers,
                order_count,
            )
            runs.append({"turns": turns, "failures": failures})
        rows.append((case, runs))
        passed = sum(not run["failures"] for run in runs)
        print(f"Cas {case['id']} : {passed}/{len(runs)} réussite(s)")
        write_report(path, today, args.repeat, rows)

    for index in range(args.repeat):
        print(f"Score, répétition {index + 1} : {score_line(rows, index)}")
    print(f"Rapport : {path}")


if __name__ == "__main__":
    main()
