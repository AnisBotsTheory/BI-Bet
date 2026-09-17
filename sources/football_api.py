"""
Source unique retenue pour le football : API-Football (api-sports.io).
Fixtures, historique et cotes utilisent le même système d'ID (fixture_id,
team_id) - pas de réconciliation entre plusieurs fournisseurs.

Clé API à placer dans .streamlit/secrets.toml sous [football] api_key = "..."
"""

import requests
import streamlit as st
from datetime import datetime

from core.schema import Event, Participant, OddsSnapshot, Sport

BASE_URL = "https://v3.football.api-sports.io"


def _headers() -> dict:
    return {"x-apisports-key": st.secrets["football"]["api_key"]}


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
    )
