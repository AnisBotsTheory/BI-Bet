"""
Source unique retenue pour le football : API-Football (api-sports.io).
Fixtures, historique et cotes utilisent le même système d'ID (fixture_id,
team_id) - pas de réconciliation entre plusieurs fournisseurs.

Clé API à placer dans .streamlit/secrets.toml sous [football] api_key = "..."
"""

import requests
import streamlit as st
from datetime import datetime

from core.schema import Event, Participant, Sport

BASE_URL = "https://v3.football.api-sports.io"


def _headers() -> dict:
    return {"x-apisports-key": st.secrets["football"]["api_key"]}


@st.cache_data(ttl=86400)  # les ligues changent rarement, cache 1 jour
def get_leagues() -> list[dict]:
    """
    Récupère la liste complète des ligues disponibles (nom, pays, id).
    Sert à peupler le menu déroulant de sélection dans l'interface,
    plutôt que de demander à l'utilisateur de connaître l'ID numérique.
    """
    resp = requests.get(f"{BASE_URL}/leagues", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json().get("response", [])


@st.cache_data(ttl=3600)  # rafraîchi 1x/heure, cohérent avec le choix "différé, pas temps réel"
def get_fixtures(league_id: int, season: int) -> list[dict]:
    """Récupère les matchs bruts d'une ligue/saison. Retourne le JSON brut de l'API."""
    resp = requests.get(
        f"{BASE_URL}/fixtures",
        headers=_headers(),
        params={"league": league_id, "season": season},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("response", [])


def get_fixtures_multi_saisons(league_id: int, saisons: list[int]) -> list[dict]:
    """Concatène les fixtures de plusieurs saisons pour une même ligue."""
    toutes_fixtures = []
    for saison in saisons:
        toutes_fixtures.extend(get_fixtures(league_id, saison))
    return toutes_fixtures


@st.cache_data(ttl=3600)
def get_odds(fixture_id: int) -> list[dict]:
    """Récupère les cotes brutes pour un match donné."""
    resp = requests.get(
        f"{BASE_URL}/odds",
        headers=_headers(),
        params={"fixture": fixture_id},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("response", [])


@st.cache_data(ttl=3600)
def get_predictions(fixture_id: int) -> dict:
    """
    Récupère le pronostic natif d'API-Football pour un match (endpoint gratuit).
    Calculé par 6 algorithmes internes, SANS utiliser les cotes des bookmakers -
    donc un second avis réellement indépendant du marché et de notre propre
    rating TrueSkill.
    """
    resp = requests.get(
        f"{BASE_URL}/predictions",
        headers=_headers(),
        params={"fixture": fixture_id},
        timeout=15,
    )
    resp.raise_for_status()
    reponse = resp.json().get("response", [])
    return reponse[0] if reponse else {}


def extraire_cotes_1x2(odds_bruts: list[dict]) -> dict | None:
    """
    Moyenne les cotes 1X2 ("Match Winner") tous bookmakers confondus.
    Retourne {"home": x, "draw": y, "away": z} ou None si aucune cote dispo
    (fréquent sur les divisions amateurs ou les matchs déjà anciens).
    """
    if not odds_bruts:
        return None
    cumul = {"Home": [], "Draw": [], "Away": []}
    for bookmaker in odds_bruts[0].get("bookmakers", []):
        for pari in bookmaker.get("bets", []):
            if pari.get("name") == "Match Winner":
                for valeur in pari.get("values", []):
                    if valeur["value"] in cumul:
                        cumul[valeur["value"]].append(float(valeur["odd"]))
    if not cumul["Home"]:
        return None
    return {
        "home": sum(cumul["Home"]) / len(cumul["Home"]),
        "draw": sum(cumul["Draw"]) / len(cumul["Draw"]),
        "away": sum(cumul["Away"]) / len(cumul["Away"]),
    }


def vers_schema_commun(fixture_brut: dict) -> Event:
    """Convertit un fixture brut API-Football vers le schéma Event commun."""
    teams = fixture_brut["teams"]
    participants = [
        Participant(id=str(teams["home"]["id"]), name=teams["home"]["name"], sport=Sport.FOOTBALL),
        Participant(id=str(teams["away"]["id"]), name=teams["away"]["name"], sport=Sport.FOOTBALL),
    ]
    return Event(
        id=str(fixture_brut["fixture"]["id"]),
        sport=Sport.FOOTBALL,
        date=datetime.fromisoformat(fixture_brut["fixture"]["date"]),
        participants=participants,
        competition=fixture_brut["league"]["name"],
        meta={"venue": fixture_brut["fixture"].get("venue", {}).get("name")},
        brut=fixture_brut,  # réponse API complète conservée, rien n'est filtré
    )
