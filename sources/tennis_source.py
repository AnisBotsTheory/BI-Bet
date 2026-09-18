"""
Source unique retenue pour le tennis : TennisMyLife (TML-Database) sur GitHub.
Bascule depuis tennis-data.co.uk, devenu indisponible (timeout de connexion).
Pas d'authentification nécessaire - fichiers CSV publics, un par année,
couvrant ATP et WTA dans le même référentiel.
"""

import io
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

from core.schema import Event, Participant, Sport

BASE_URL = "https://raw.githubusercontent.com/Tennismylife/TML-Database/master"


@st.cache_data(ttl=86400)  # 1x/jour, cohérent avec le choix de données différées
def get_saison(annee: int) -> pd.DataFrame:
    """Télécharge le fichier CSV d'une saison (ATP, toutes catégories confondues)."""
    url = f"{BASE_URL}/{annee}.csv"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text))


def vers_schema_commun(ligne: pd.Series) -> Event:
    """Convertit une ligne TennisMyLife vers le schéma Event commun."""
    nom_gagnant = f"{ligne.get('winner_name', '')}".strip()
    nom_perdant = f"{ligne.get('loser_name', '')}".strip()
    participants = [
        Participant(
            id=str(ligne.get("winner_id", nom_gagnant)), name=nom_gagnant, sport=Sport.TENNIS,
            meta={"surface": ligne.get("surface")},
        ),
        Participant(
            id=str(ligne.get("loser_id", nom_perdant)), name=nom_perdant, sport=Sport.TENNIS,
            meta={"surface": ligne.get("surface")},
        ),
    ]
    return Event(
        id=f"{ligne.get('tourney_id')}_{ligne.get('match_num')}",
        sport=Sport.TENNIS,
        date=pd.to_datetime(str(ligne.get("tourney_date")), format="%Y%m%d", errors="coerce"),
        participants=participants,
        competition=ligne.get("tourney_name"),
        meta={"surface": ligne.get("surface"), "round": ligne.get("round")},
    )
