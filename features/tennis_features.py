"""
Features spécifiques au tennis, construites à partir du DataFrame brut
TennisMyLife (voir sources/tennis_source.py). Contrairement au football,
il n'y a ici ni cotes ni pronostic tiers - le classement ATP officiel
(rank_points) sert de seconde référence indépendante de notre propre
rating, pour garder le même principe de "confronter plusieurs avis".
"""

import math
import pandas as pd

from core.rating_engine import nouveau_rating, mettre_a_jour_duel, probabilite_victoire_duel


def construire_ratings_par_surface(df: pd.DataFrame) -> dict[str, dict[str, "trueskill.Rating"]]:
    """
    Un rating TrueSkill indépendant PAR SURFACE (terre battue, dur, gazon) -
    un joueur fort sur terre battue n'est pas forcément fort sur gazon,
    donc mélanger les surfaces fausserait le rating.
    """
    df_ordonne = df.sort_values("tourney_date")
    ratings: dict[str, dict[str, "trueskill.Rating"]] = {}

    for _, ligne in df_ordonne.iterrows():
        surface = ligne.get("surface") or "Inconnue"
        gagnant_id, perdant_id = str(ligne["winner_id"]), str(ligne["loser_id"])
        ratings.setdefault(surface, {})

        if gagnant_id not in ratings[surface]:
            ratings[surface][gagnant_id] = nouveau_rating()
        if perdant_id not in ratings[surface]:
            ratings[surface][perdant_id] = nouveau_rating()

        r_gagnant, r_perdant = ratings[surface][gagnant_id], ratings[surface][perdant_id]
        ratings[surface][gagnant_id], ratings[surface][perdant_id] = mettre_a_jour_duel(r_gagnant, r_perdant)

    return ratings


def forme_recente(df: pd.DataFrame, joueur_id: str, n: int = 5) -> dict:
    """Bilan victoires/défaites sur les n derniers matchs d'un joueur, toutes surfaces confondues."""
    matchs = df[(df["winner_id"].astype(str) == joueur_id) | (df["loser_id"].astype(str) == joueur_id)]
    matchs = matchs.sort_values("tourney_date", ascending=False).head(n)
    victoires = (matchs["winner_id"].astype(str) == joueur_id).sum()
    return {"matchs_joues": len(matchs), "victoires": int(victoires),
            "défaites": len(matchs) - int(victoires)}


def confrontations_directes(df: pd.DataFrame, joueur_a_id: str, joueur_b_id: str) -> pd.DataFrame:
    """Historique des confrontations directes entre deux joueurs précis."""
    paires = {joueur_a_id, joueur_b_id}
    matchs = df[df.apply(lambda l: {str(l["winner_id"]), str(l["loser_id"])} == paires, axis=1)]
    return matchs[["tourney_date", "tourney_name", "surface", "winner_name", "loser_name", "score"]]


def stats_service_moyennes(df: pd.DataFrame, joueur_id: str) -> dict:
    """
    Moyennes de service d'un joueur (aces, doubles fautes, % de 1ère balle gagnée)
    sur tous les matchs disponibles, qu'il ait gagné ou perdu.
    """
    en_gagnant = df[df["winner_id"].astype(str) == joueur_id][["w_ace", "w_df", "w_1stWon", "w_1stIn", "w_svpt"]]
    en_gagnant.columns = ["ace", "df", "1stWon", "1stIn", "svpt"]
    en_perdant = df[df["loser_id"].astype(str) == joueur_id][["l_ace", "l_df", "l_1stWon", "l_1stIn", "l_svpt"]]
    en_perdant.columns = ["ace", "df", "1stWon", "1stIn", "svpt"]
    tout = pd.concat([en_gagnant, en_perdant])

    if tout.empty:
        return {"matchs": 0}
    return {
        "matchs": len(tout),
        "aces_moyenne": round(tout["ace"].mean(), 1),
        "doubles_fautes_moyenne": round(tout["df"].mean(), 1),
        "pct_1ere_balle_gagnee": round(100 * tout["1stWon"].sum() / tout["1stIn"].sum(), 1) if tout["1stIn"].sum() else None,
    }


def proba_classement_atp(points_a: float, points_b: float) -> float:
    """
    Probabilité de victoire du joueur A dérivée des points ATP officiels,
    via une fonction logistique (même principe que le calcul Elo aux échecs).
    Sert de seconde référence, indépendante de notre rating maison.
    """
    if not points_a or not points_b:
        return None
    diff = points_a - points_b
    return 1 / (1 + math.exp(-diff / 400))


def backtest_modele(df: pd.DataFrame) -> dict:
    """
    Même principe que pour le foot : on prédit AVANT de connaître le
    résultat (avec les ratings tels qu'ils étaient à ce moment), on compte
    les bonnes prédictions, puis seulement après on met à jour le rating.
    """
    df_ordonne = df.sort_values("tourney_date")
    ratings: dict[str, dict[str, "trueskill.Rating"]] = {}
    bonnes_predictions, matchs_evalues = 0, 0

    for _, ligne in df_ordonne.iterrows():
        surface = ligne.get("surface") or "Inconnue"
        gagnant_id, perdant_id = str(ligne["winner_id"]), str(ligne["loser_id"])
        ratings.setdefault(surface, {})

        deja_vus = gagnant_id in ratings[surface] and perdant_id in ratings[surface]
        if deja_vus:
            proba_gagnant = probabilite_victoire_duel(ratings[surface][gagnant_id], ratings[surface][perdant_id])
            matchs_evalues += 1
            if proba_gagnant >= 0.5:  # le modèle donnait bien le futur vainqueur favori
                bonnes_predictions += 1

        if gagnant_id not in ratings[surface]:
            ratings[surface][gagnant_id] = nouveau_rating()
        if perdant_id not in ratings[surface]:
            ratings[surface][perdant_id] = nouveau_rating()
        r_g, r_p = ratings[surface][gagnant_id], ratings[surface][perdant_id]
        ratings[surface][gagnant_id], ratings[surface][perdant_id] = mettre_a_jour_duel(r_g, r_p)

    return {
        "matchs_evalues": matchs_evalues,
        "bonnes_predictions": bonnes_predictions,
        "precision": round(100 * bonnes_predictions / matchs_evalues, 1) if matchs_evalues else None,
    }
