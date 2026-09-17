"""
Source unique retenue pour l'hippique : open-pmu-api.
Seule vraie API structurée disponible gratuitement pour ce sport - pas de
concurrent direct à recouper (France Galop / LeTROT restent des références
de vérification ponctuelle, pas des sources intégrées au pipeline).
"""

import requests
import streamlit as st
from datetime import datetime

from core.schema import Event, Participant, Sport

BASE_URL = "https://open-pmu-api.vercel.app/api"


@st.cache_data(ttl=86400)
def get_arrivees(date: str) -> list[dict]:
    """
    date au format MM/DD/YYYY (format attendu par l'API, cf. doc du projet).
    Retourne la liste brute des courses du jour.
    """
    resp = requests.get(f"{BASE_URL}/arrivees", params={"date": date}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", [])


def vers_schema_commun(course_brute: dict) -> Event:
    """Convertit une course brute open-pmu-api vers le schéma Event commun (n participants)."""
    participants = []
    for numero, details in course_brute.get("arrivee_details", {}).items():
        participants.append(
            Participant(
                id=str(numero),
                name=details["nom_cheval"],
                sport=Sport.HIPPIQUE,
                meta={
                    "musique": details.get("musique"),
                    "corde": details.get("corde"),
                    "jockey": details.get("nom_jockey"),
                },
            )
        )
    return Event(
        id=f"{course_brute['lieu']}_{course_brute.get('r/c', '')}",
        sport=Sport.HIPPIQUE,
        date=datetime.now(),  # à remplacer par la date réelle passée en paramètre de la requête
        participants=participants,
        competition=course_brute.get("prix"),
        meta={"hippodrome": course_brute.get("lieu"), "discipline": course_brute.get("type")},
    )
