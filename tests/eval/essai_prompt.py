"""Premier essai du prompt système, à lancer dans la Cloud Sandbox (GPU).

Pour chaque cas à un seul message de cas.json, l'essai rejoue le 2e passage de
l'agent : le modèle a déjà appelé l'outil et reçoit son résultat (la vraie fonction,
sur la vraie base) ; il ne lui reste qu'à rédiger la réponse. Chaque cas est joué
avec chaque valeur de repetition_penalty, et les réponses sont écrites dans un rapport
Markdown (tests/eval/resultats/) à relire.

Depuis la racine du dépôt, dans la sandbox :
    cp .env.example .env            # date du jour simulée
    pip install python-dotenv       # torch et transformers sont fournis par la sandbox
    python -m tests.eval.essai_prompt
"""

import inspect
import json
import re
import time
from datetime import date, datetime
from pathlib import Path

from transformers import (
    FineGrainedFP8Config,
    Mistral3ForConditionalGeneration,
    MistralCommonBackend,
    set_seed,
)

from config import get_today
from db import get_connection
from prompts import build_system_prompt
from tools import get_customer_orders_and_address

MODEL_ID = "mistralai/Ministral-3-14B-Instruct-2512"
EVAL_DIR = Path(__file__).parent
REPETITION_PENALTIES = [1.0, 1.5]
# Réglages du cours 01.1. do_sample=True : sans lui, temperature, top_p et top_k
# sont ignorés et le modèle prend toujours le token le plus probable.
GENERATION = {
    "do_sample": True,
    "temperature": 0.05,
    "top_p": 0.75,
    "top_k": 10,
    "max_new_tokens": 400,
}

TOOL_NAME = get_customer_orders_and_address.__name__
# Aucun paramètre exposé au modèle : le user_id vient de la session, jamais du LLM
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": inspect.getdoc(get_customer_orders_and_address),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}
# Le tokeniseur Mistral exige un identifiant d'appel de 9 caractères alphanumériques
TOOL_CALL_ID = "call00001"

RAW_STATUS = re.compile(r"\b(invoiced|shipped|delivered)\b", re.IGNORECASE)


def customer_names(user_id: int) -> tuple[str, str]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT first_name, last_name FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def build_messages(question: str, user_id: int, today: date) -> list[dict]:
    """Conversation telle que le modèle la voit après l'appel de l'outil."""
    first_name, last_name = customer_names(user_id)
    result = get_customer_orders_and_address(user_id)
    return [
        {
            "role": "system",
            "content": build_system_prompt(first_name, last_name, today),
        },
        {"role": "user", "content": question},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": TOOL_CALL_ID,
                    "type": "function",
                    "function": {"name": TOOL_NAME, "arguments": {}},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": TOOL_CALL_ID,
            "name": TOOL_NAME,
            "content": json.dumps(result, ensure_ascii=False),
        },
    ]


def load_model():
    tokenizer = MistralCommonBackend.from_pretrained(MODEL_ID)
    model = Mistral3ForConditionalGeneration.from_pretrained(
        MODEL_ID,
        device_map="auto",
        quantization_config=FineGrainedFP8Config(dequantize=True),
    )
    return tokenizer, model


def generate(model, tokenizer, messages: list[dict], penalty: float):
    inputs = tokenizer.apply_chat_template(
        messages, tools=[TOOL_SCHEMA], return_tensors="pt", return_dict=True
    ).to(model.device)
    set_seed(0)  # même tirage pour chaque cas : les essais sont comparables
    start = time.perf_counter()
    output = model.generate(**inputs, repetition_penalty=penalty, **GENERATION)
    duration = time.perf_counter() - start
    new_tokens = output[0][inputs["input_ids"].shape[1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip(), duration


def write_report(path: Path, today: date, rows: list) -> None:
    lines = [
        f"# Essai du prompt système — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Modèle : `{MODEL_ID}` · date du jour : {today} · réglages : `{GENERATION}`",
        "",
    ]
    for case, answers in rows:
        lines += [
            f"## Cas {case['id']} — {case['etape']} ({case['client']})",
            "",
            f"**Message** : {case['messages'][0]}",
            "",
            "**Attendu** : " + " ; ".join(case["attendu"]),
            "",
        ]
        for penalty, text, duration in answers:
            flag = " · ⚠️ code brut de statut" if RAW_STATUS.search(text) else ""
            lines += [
                f"**repetition_penalty = {penalty}** ({duration:.1f} s){flag}",
                "",
            ]
            lines += ["> " + line for line in text.splitlines()] + [""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    data = json.loads((EVAL_DIR / "cas.json").read_text(encoding="utf-8"))
    cases = [case for case in data["cas"] if len(case["messages"]) == 1]
    today = get_today()
    print(f"Date du jour utilisée : {today} — {len(cases)} cas")

    tokenizer, model = load_model()
    path = EVAL_DIR / "resultats" / f"essai-prompt-{datetime.now():%Y%m%d-%H%M}.md"
    path.parent.mkdir(exist_ok=True)

    rows = []
    for case in cases:
        user_id = data["clients"][case["client"]]["user_id"]
        messages = build_messages(case["messages"][0], user_id, today)
        answers = []
        for penalty in REPETITION_PENALTIES:
            text, duration = generate(model, tokenizer, messages, penalty)
            answers.append((penalty, text, duration))
            print(f"Cas {case['id']} · repetition_penalty={penalty} : {duration:.1f} s")
        rows.append((case, answers))
        write_report(path, today, rows)  # réécrit à chaque cas : rien n'est perdu

    print(f"Rapport : {path}")


if __name__ == "__main__":
    main()
