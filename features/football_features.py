"""
Features spécifiques au football, construites à partir des événements déjà
convertis au schéma commun (voir sources/football_api.py::vers_schema_commun).
Tout ce qui est calculable SANS appel API supplémentaire est privilégié
(forme, H2H, stats arbitre) - seuls les ratings s'appuient uniquement sur
l'historique déjà en mémoire.
"""

from collections import defaultdict
import pandas as pd

from core.rating_engine import nouveau_rating, mettre_a_jour_duel, score_affichable, probabilite_victoire_duel


def construire_ratings(fixtures_brutes: list[dict]) -> dict[str, "trueskill.Rating"]:
    """
    Calcule un rating TrueSkill par équipe en rejouant l'historique dans
    l'ordre chronologique. Ne garde que les matchs joués et terminés
    (ignore les matchs à venir, sans résultat).
    """
    fixtures_terminees = [
        f for f in fixtures_brutes
        if f["fixture"]["status"]["short"] == "FT" and f["goals"]["home"] is not None
    ]
    fixtures_triees = sorted(fixtures_terminees, key=lambda f: f["fixture"]["date"])

    ratings: dict[str, "trueskill.Rating"] = {}

    def rating_de(team_id: str):
        if team_id not in ratings:
            ratings[team_id] = nouveau_rating()
        return ratings[team_id]

    for f in fixtures_triees:
        home_id = str(f["teams"]["home"]["id"])
        away_id = str(f["teams"]["away"]["id"])
        buts_home, buts_away = f["goals"]["home"], f["goals"]["away"]

        r_home, r_away = rating_de(home_id), rating_de(away_id)
        if buts_home > buts_away:
            ratings[home_id], ratings[away_id] = mettre_a_jour_duel(r_home, r_away)
        elif buts_away > buts_home:
            ratings[away_id], ratings[home_id] = mettre_a_jour_duel(r_away, r_home)
        # match nul : TrueSkill configuré sans probabilité de nul (draw_probability=0),
        # on ne met à jour aucun des deux ratings pour rester neutre sur ce résultat

    return ratings


def forme_recente(fixtures_brutes: list[dict], team_id: str, n: int = 5) -> dict:
    """Points par match sur les n derniers matchs joués par une équipe (3/1/0)."""
    matchs_equipe = [
        f for f in fixtures_brutes
        if f["fixture"]["status"]["short"] == "FT"
        and (str(f["teams"]["home"]["id"]) == team_id or str(f["teams"]["away"]["id"]) == team_id)
    ]
    matchs_equipe = sorted(matchs_equipe, key=lambda f: f["fixture"]["date"], reverse=True)[:n]

    points = 0
    for f in matchs_equipe:
        est_domicile = str(f["teams"]["home"]["id"]) == team_id
        buts_pour = f["goals"]["home"] if est_domicile else f["goals"]["away"]
        buts_contre = f["goals"]["away"] if est_domicile else f["goals"]["home"]
        if buts_pour is None:
            continue
        if buts_pour > buts_contre:
            points += 3
        elif buts_pour == buts_contre:
            points += 1

    return {"matchs_joues": len(matchs_equipe), "points": points,
            "points_par_match": round(points / len(matchs_equipe), 2) if matchs_equipe else None}


def confrontations_directes(fixtures_brutes: list[dict], team_a_id: str, team_b_id: str) -> pd.DataFrame:
    """Historique des matchs déjà rencontrés entre deux équipes précises."""
    paires = {team_a_id, team_b_id}
    matchs = [
        f for f in fixtures_brutes
        if {str(f["teams"]["home"]["id"]), str(f["teams"]["away"]["id"])} == paires
    ]
    lignes = [{
        "date": f["fixture"]["date"],
        "domicile": f["teams"]["home"]["name"],
        "extérieur": f["teams"]["away"]["name"],
        "score": f"{f['goals']['home']} - {f['goals']['away']}",
    } for f in matchs]
    return pd.DataFrame(lignes)


def backtest_modele(fixtures_brutes: list[dict]) -> dict:
    """
    Mesure la fiabilité réelle du modèle sur l'historique déjà chargé.
    Principe : pour chaque match, on calcule la probabilité AVANT de
    connaître le résultat (avec les ratings tels qu'ils étaient à ce
    moment-là), puis on met à jour les ratings - jamais l'inverse. Ça
    évite le biais classique de "prédire" avec des infos qui ne seraient
    connues qu'après coup.
    """
    fixtures_terminees = [
        f for f in fixtures_brutes
        if f["fixture"]["status"]["short"] == "FT" and f["goals"]["home"] is not None
    ]
    fixtures_triees = sorted(fixtures_terminees, key=lambda f: f["fixture"]["date"])

    ratings: dict[str, "trueskill.Rating"] = {}
    bonnes_predictions, matchs_evalues = 0, 0

    def rating_de(team_id: str):
        if team_id not in ratings:
            ratings[team_id] = nouveau_rating()
        return ratings[team_id]

    for f in fixtures_triees:
        home_id, away_id = str(f["teams"]["home"]["id"]), str(f["teams"]["away"]["id"])
        buts_home, buts_away = f["goals"]["home"], f["goals"]["away"]
        r_home, r_away = rating_de(home_id), rating_de(away_id)

        # on ne juge le modèle que sur les matchs où les deux équipes ont déjà
        # un minimum d'historique (sinon la prédiction est arbitraire, 50/50)
        deja_vues = home_id in ratings and away_id in ratings
        if deja_vues and buts_home != buts_away:  # on exclut les nuls, non modélisés par le rating
            proba_home = probabilite_victoire_duel(r_home, r_away)
            favori_predit = home_id if proba_home >= 0.5 else away_id
            gagnant_reel = home_id if buts_home > buts_away else away_id
            matchs_evalues += 1
            if favori_predit == gagnant_reel:
                bonnes_predictions += 1

        if buts_home > buts_away:
            ratings[home_id], ratings[away_id] = mettre_a_jour_duel(r_home, r_away)
        elif buts_away > buts_home:
            ratings[away_id], ratings[home_id] = mettre_a_jour_duel(r_away, r_home)

    return {
        "matchs_evalues": matchs_evalues,
        "bonnes_predictions": bonnes_predictions,
        "precision": round(100 * bonnes_predictions / matchs_evalues, 1) if matchs_evalues else None,
    }


def stats_arbitres(fixtures_brutes: list[dict]) -> pd.DataFrame:
    """
    Statistiques par arbitre à partir des matchs déjà chargés : nombre de
    matchs, taux de victoire à domicile. Aucun appel API supplémentaire -
    tout est déjà présent dans les fixtures récupérées.
    """
    cumul = defaultdict(lambda: {"matchs": 0, "victoires_domicile": 0, "nuls": 0})
    for f in fixtures_brutes:
        arbitre = f["fixture"].get("referee")
        if not arbitre or f["fixture"]["status"]["short"] != "FT":
            continue
        buts_home, buts_away = f["goals"]["home"], f["goals"]["away"]
        cumul[arbitre]["matchs"] += 1
        if buts_home > buts_away:
            cumul[arbitre]["victoires_domicile"] += 1
        elif buts_home == buts_away:
            cumul[arbitre]["nuls"] += 1

    lignes = []
    for arbitre, c in cumul.items():
        if c["matchs"] < 3:  # écarte les arbitres avec trop peu de matchs pour être significatifs
            continue
        lignes.append({
            "arbitre": arbitre,
            "matchs": c["matchs"],
            "% victoire domicile": round(100 * c["victoires_domicile"] / c["matchs"], 1),
            "% nul": round(100 * c["nuls"] / c["matchs"], 1),
        })
    return pd.DataFrame(lignes).sort_values("matchs", ascending=False)
