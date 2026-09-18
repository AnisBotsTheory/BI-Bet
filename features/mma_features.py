"""
Features MMA construites à partir des combats bruts API-Sports (voir
sources/mma_source.py). Même logique que football_features.py, adaptée
au fait qu'on part de l'historique de 2 combattants précis plutôt que
d'une compétition entière.
"""

import pandas as pd
from core.rating_engine import nouveau_rating, mettre_a_jour_duel, probabilite_victoire_duel


def construire_ratings(combats_bruts: list[dict]) -> dict[str, "trueskill.Rating"]:
    """
    Calcule un rating TrueSkill par combattant en rejouant l'historique
    combiné des deux combattants (et de leurs adversaires respectifs) dans
    l'ordre chronologique. Ne garde que les combats terminés avec un
    vainqueur clair (ignore matchs nuls / no contest).
    """
    combats_termines = [
        c for c in combats_bruts
        if c.get("fight", {}).get("status") in ("Finished", "FT") and c.get("winner", {}).get("id")
    ]
    combats_tries = sorted(combats_termines, key=lambda c: c["fight"]["date"])

    ratings: dict[str, "trueskill.Rating"] = {}

    def rating_de(fighter_id: str):
        if fighter_id not in ratings:
            ratings[fighter_id] = nouveau_rating()
        return ratings[fighter_id]

    for c in combats_tries:
        id_1 = str(c["fighters"]["first"]["id"])
        id_2 = str(c["fighters"]["second"]["id"])
        vainqueur_id = str(c["winner"]["id"])
        perdant_id = id_2 if vainqueur_id == id_1 else id_1

        r_vainqueur, r_perdant = rating_de(vainqueur_id), rating_de(perdant_id)
        ratings[vainqueur_id], ratings[perdant_id] = mettre_a_jour_duel(r_vainqueur, r_perdant)

    return ratings


def forme_recente(combats_bruts: list[dict], fighter_id: str, n: int = 5) -> dict:
    """Bilan victoires/défaites sur les n derniers combats d'un combattant."""
    combats = [
        c for c in combats_bruts
        if str(c["fighters"]["first"]["id"]) == fighter_id or str(c["fighters"]["second"]["id"]) == fighter_id
    ]
    combats = sorted(combats, key=lambda c: c["fight"]["date"], reverse=True)[:n]
    victoires = sum(1 for c in combats if str(c.get("winner", {}).get("id")) == fighter_id)
    return {"combats": len(combats), "victoires": victoires, "défaites": len(combats) - victoires}


def confrontation_directe(combats_bruts: list[dict], fighter_a_id: str, fighter_b_id: str) -> pd.DataFrame:
    """Combats déjà disputés entre ces deux combattants précis, s'il y en a."""
    paires = {fighter_a_id, fighter_b_id}
    combats = [
        c for c in combats_bruts
        if {str(c["fighters"]["first"]["id"]), str(c["fighters"]["second"]["id"])} == paires
    ]
    lignes = [{
        "date": c["fight"]["date"],
        "combattant 1": c["fighters"]["first"]["name"],
        "combattant 2": c["fighters"]["second"]["name"],
        "vainqueur": c.get("winner", {}).get("name"),
        "méthode": c.get("fight", {}).get("method"),
    } for c in combats]
    return pd.DataFrame(lignes)
