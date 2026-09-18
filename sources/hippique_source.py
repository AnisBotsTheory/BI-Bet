"""
Source unique retenue pour l'hippique : open-pmu-api.
Seule vraie API structurée disponible gratuitement pour ce sport - pas de
concurrent direct à recouper (France Galop / LeTROT restent des références
de vérification ponctuelle, pas des sources intégrées au pipeline).

L'API n'expose les arrivées que JOUR PAR JOUR. Pour permettre une sélection
année/mois côté interface (plus pertinente qu'une date exacte pour explorer
les données), get_arrivees_mois boucle sur chaque jour du mois choisi.
"""

import calendar
from datetime import date

import requests
import streamlit as st

from core.schema import Event, Participant, Sport

BASE_URL = "https://open-pmu-api.vercel.app/api"


@st.cache_data(ttl=86400)
def get_arrivees(jour: str) -> list[dict]:
    """
    jour au format MM/DD/YYYY (format attendu par l'API).
    Retourne la liste brute des courses de ce jour précis.
    """
    resp = requests.get(f"{BASE_URL}/arrivees", params={"date": jour}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", [])


def get_arrivees_mois(annee: int, mois: int) -> list[dict]:
    """
    Agrège les arrivées de TOUS les jours d'un mois donné, en enchaînant les
    appels quotidiens (contrainte technique de l'API, invisible pour l'utilisateur
    qui ne choisit qu'une année et un mois côté interface).
    Chaque jour est mis en cache individuellement (get_arrivees), donc relancer
    la même période ne recoûte rien en requêtes.
    """
    nb_jours = calendar.monthrange(annee, mois)[1]
    toutes_courses = []
    for jour in range(1, nb_jours + 1):
        jour_str = date(annee, mois, jour).strftime("%m/%d/%Y")
        try:
            courses = get_arrivees(jour_str)
            toutes_courses.extend(courses)
        except Exception:
            continue  # jour sans course ou erreur ponctuelle, on continue le mois
    return toutes_courses


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
        id=f"{course_brute.get('lieu')}_{course_brute.get('r/c', '')}",
        sport=Sport.HIPPIQUE,
        date=course_brute.get("date_evenement") or "",
        participants=participants,
        competition=course_brute.get("prix"),
        meta={"hippodrome": course_brute.get("lieu"), "discipline": course_brute.get("type")},
        brut=course_brute,  # réponse API complète conservée, rien n'est filtré
    )
