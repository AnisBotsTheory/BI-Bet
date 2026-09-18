"""
Source unique retenue pour le MMA : API-Sports MMA API (v1.mma.api-sports.io).
Même famille que football_api.py : même compte, même authentification
(x-apisports-key), même plan gratuit (100 requêtes/jour).

Approche par COMBATTANT plutôt que par date : on cherche un combattant par
nom, on récupère son historique de combats, et on compare deux combattants
directement - beaucoup plus économe en requêtes qu'un balayage par mois.
"""

import requests
import streamlit as st
from datetime import datetime

from core.schema import Event, Participant, Sport

BASE_URL = "https://v1.mma.api-sports.io"


def _headers() -> dict:
    return {"x-apisports-key": st.secrets["football"]["api_key"]}


@st.cache_data(ttl=86400)
def rechercher_combattant(nom: str) -> list[dict]:
    """Recherche des combattants par nom. Retourne une liste (plusieurs homonymes possibles)."""
    resp = requests.get(f"{BASE_URL}/fighters", headers=_headers(), params={"search": nom}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("response", [])


@st.cache_data(ttl=86400)
def get_combats_du_combattant(fighter_id: int) -> list[dict]:
    """Récupère l'historique complet des combats d'un combattant précis."""
    resp = requests.get(f"{BASE_URL}/fights", headers=_headers(), params={"fighter": fighter_id}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("response", [])


@st.cache_data(ttl=86400)
def get_odds(fight_id: int) -> list[dict]:
    """Récupère les cotes brutes pour un combat donné."""
    resp = requests.get(f"{BASE_URL}/odds", headers=_headers(), params={"fight": fight_id}, timeout=15)
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
        brut=fight_brut,
    )
