"""Vérifications automatiques d'une réponse du bot (sans appel au modèle).

Une réponse échoue si l'une des vérifications de son cas (cas.json, clé « verifs »)
ou l'un des interdits globaux n'est pas respecté, ou si elle cite une date ou un nombre
absent des données du client et de sa question (donnée inventée). Le ton n'est pas
noté : les points « a_relire » restent à juger à la main.
"""

import re

MONTHS = (
    "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre"
    "|décembre"
)
DATE = re.compile(rf"(?<!\w)(1er|\d{{1,2}}) ({MONTHS})\b")


def normalize(text: str) -> str:
    """Minuscules, sans gras Markdown, apostrophes et espaces uniformisées."""
    text = text.lower().replace("*", "").replace("’", "'")
    return text.replace(" ", " ").replace(" ", " ")


def find(text: str, term: str) -> int:
    """Position de term dans text (déjà normalisé), sans couper un mot à gauche."""
    match = re.search(r"(?<!\w)" + re.escape(normalize(term)), text)
    return match.start() if match else -1


def dates_in(text: str) -> set[str]:
    """Dates « jour mois » citées dans un texte : « 1er juin » devient « 1 juin »."""
    return {
        f"{day.replace('er', '')} {month}"
        for day, month in DATE.findall(normalize(text))
    }


def numbers_in(text: str) -> set[str]:
    """Nombres cités dans un texte, sans zéros initiaux : « 06843 » devient « 6843 »."""
    return {str(int(number)) for number in re.findall(r"\d+", normalize(text))}


def check(
    case: dict,
    answer: str,
    tool_calls: list,
    forbidden: list[str],
    known_dates: set[str],
    known_numbers: set[str],
    order_count: int = 0,
) -> list[str]:
    """Liste des vérifications échouées ; vide si la réponse passe.

    order_count (nombre de commandes du client) autorise les comptages comme
    « (2 commandes) » qui ne le dépassent pas.
    """
    if answer.startswith("ERREUR"):
        return ["erreur pendant l'appel au modèle"]
    verifs = case.get("verifs", {})
    text = normalize(answer)
    failures = []

    tool = verifs.get("outil", "indifferent")
    if tool == "obligatoire" and not tool_calls:
        failures.append("outil non appelé")
    if tool == "interdit" and tool_calls:
        failures.append("outil appelé sans raison")

    for alternatives in verifs.get("doit_contenir", []):
        if all(find(text, term) < 0 for term in alternatives):
            failures.append("manque : " + " / ".join(alternatives))

    for term in verifs.get("ne_doit_pas_contenir", []) + forbidden:
        if find(text, term) >= 0:
            failures.append(f"contient : {term}")

    positions = []
    for alternatives in verifs.get("dans_l_ordre", []):
        found = [find(text, term) for term in alternatives if find(text, term) >= 0]
        positions.append(min(found) if found else -1)
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        failures.append("ordre incorrect")

    unknown = dates_in(answer) - known_dates
    if unknown:
        failures.append("date absente des données du client : " + ", ".join(unknown))

    allowed = known_numbers | numbers_in(" ".join(case["messages"]))
    counts = re.findall(r"(\d+) commandes?\b", text)
    allowed |= {str(int(n)) for n in counts if int(n) <= order_count}
    unknown = numbers_in(answer) - allowed
    if unknown:
        failures.append(
            "nombre absent des données du client : " + ", ".join(sorted(unknown))
        )

    return failures
