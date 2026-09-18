"""
Source unique retenue pour le MMA : API-Sports MMA API (v1.mma.api-sports.io).
Remplace le dataset Kaggle initialement prévu, qui n'était plus mis à jour
depuis fin 2024. Même famille que football_api.py : même compte, même
mécanisme d'authentification (x-apisports-key), même plan gratuit
(100 requêtes/jour).

Clé API : la même que pour le football, déjà dans .streamlit/secrets.toml
sous [football] api_key = "...". API-Sports utilise une seule clé pour
toute la famille de produits (football, MMA, basket, etc.).
"""

import requests
import streamlit as st
from datetime import datetime

from core.schema import Event, Participant, Sport

BASE_URL = "https://v1.mma.api-sports.io"


def _headers() -> dict:
    return {"x-apisports-key": st.secrets["football"]["api_key"]}


@st.cache_data(ttl=86400)  # 1x/jour, cohérent avec le choix "différé"
def get_fights(date: str) -> list[dict]:
    """
    date au format YYYY-MM-DD.
    Retourne la liste brute des combats à cette date.
    """
    resp = requests.get(
        f"{BASE_URL}/fights",
        headers=_headers(),
        params={"date": date},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("response", [])


@st.cache_data(ttl=86400)
def get_odds(fight_id: int) -> list[dict]:
    """Récupère les cotes brutes pour un combat donné."""
    resp = requests.get(
        f"{BASE_URL}/odds",
        headers=_headers(),
        params={"fight": fight_id},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("response", [])


def vers_schema_commun(fight_brut: dict) -> Event:
    """Convertit un combat brut API-Sports MMA vers le schéma Event commun."""
    fighters = fight_brut["fighters"]
    participants = [
        Participant(id=str(fighters["first"]["id"]), name=fighters["first"]["name"], sport=Sport.MMA),
        Participant(id=str(fighters["second"]["id"]), name=fighters["second"]["name"], sport=Sport.MMA),
    ]
    return Event(
        id=str(fight_brut["fight"]["id"]),
        sport=Sport.MMA,
        date=datetime.fromisoformat(fight_brut["fight"]["date"]),
        participants=participants,
        competition=fight_brut.get("category"),
        meta={"organisation": fight_brut.get("organisation", {}).get("name")},
    )
