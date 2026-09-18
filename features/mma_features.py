"""
Features hippiques construites à partir des courses brutes open-pmu-api
(voir sources/hippique_source.py). Même logique que tennis_features.py :
un rating TrueSkill DÉCLINÉ PAR DISCIPLINE (le champ "type" - Attelé, Monté,
Plat, Obstacle... - joue le même rôle que la surface au tennis), avec la
différence que chaque course a n partants (classement, pas un duel) - le
cas d'usage pour lequel TrueSkill a été retenu dès le départ du projet.

HYPOTHÈSE À VÉRIFIER avec de vraies données : l'ordre des clés dans
arrivee_details reflète l'ordre d'arrivée (1er, 2e, 3e...). Si ce n'est
pas le cas, il faudra trouver le bon champ de classement dans la réponse
réelle de l'API - à confirmer une fois que tu me partages un exemple.
"""

import pandas as pd
from core.rating_engine import nouveau_rating, mettre_a_jour_classement, probabilite_victoire_duel


def construire_ratings_par_discipline(courses_brutes: list[dict]) -> dict[str, dict[str, "trueskill.Rating"]]:
    """Un rating TrueSkill indépendant par discipline (type de course)."""
    ratings: dict[str, dict[str, "trueskill.Rating"]] = {}

    for course in courses_brutes:
        discipline = course.get("type") or "Inconnue"
        ratings.setdefault(discipline, {})

        partants = list(course.get("arrivee_details", {}).items())  # supposé dans l'ordre d'arrivée
        if len(partants) < 2:
            continue

        for numero, details in partants:
            cheval_id = details.get("nom_cheval", numero)
            if cheval_id not in ratings[discipline]:
                ratings[discipline][cheval_id] = nouveau_rating()

        ratings_ordonnes = [ratings[discipline][d.get("nom_cheval", n)] for n, d in partants]
        nouveaux = mettre_a_jour_classement(ratings_ordonnes)
        for (n, d), nouveau in zip(partants, nouveaux):
            ratings[discipline][d.get("nom_cheval", n)] = nouveau

    return ratings


def forme_recente(courses_brutes: list[dict], nom_cheval: str, n: int = 5) -> dict:
    """Bilan des n dernières courses d'un cheval : nombre de victoires (1ère place) et de places (top 3)."""
    courses_du_cheval = []
    for course in courses_brutes:
        partants = list(course.get("arrivee_details", {}).items())
        for position, (numero, details) in enumerate(partants, start=1):
            if details.get("nom_cheval") == nom_cheval:
                courses_du_cheval.append({"date": course.get("date_evenement"), "position": position})

    courses_du_cheval = sorted(courses_du_cheval, key=lambda c: c["date"] or "", reverse=True)[:n]
    victoires = sum(1 for c in courses_du_cheval if c["position"] == 1)
    places = sum(1 for c in courses_du_cheval if c["position"] <= 3)
    return {"courses": len(courses_du_cheval), "victoires": victoires, "places_top3": places}


def confrontations_directes(courses_brutes: list[dict], cheval_a: str, cheval_b: str) -> pd.DataFrame:
    """Courses où les deux chevaux étaient tous les deux partants, avec leurs positions respectives."""
    lignes = []
    for course in courses_brutes:
        partants = {d.get("nom_cheval"): pos for pos, (n, d) in enumerate(course.get("arrivee_details", {}).items(), start=1)}
        if cheval_a in partants and cheval_b in partants:
            lignes.append({
                "date": course.get("date_evenement"), "hippodrome": course.get("lieu"),
                f"position {cheval_a}": partants[cheval_a], f"position {cheval_b}": partants[cheval_b],
            })
    return pd.DataFrame(lignes)
