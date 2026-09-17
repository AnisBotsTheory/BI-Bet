"""
Source unique retenue pour le tennis : tennis-data.co.uk.
Résultats + cotes dans le même fichier par saison - pas de réconciliation
avec un second fournisseur (ex: TennisMyLife volontairement écarté ici,
cf. discussion sur le risque de mismatch entre référentiels de noms).
"""

import io
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

from core.schema import Event, Participant, Sport

BASE_URL = "http://www.tennis-data.co.uk"


@st.cache_data(ttl=86400)  # 1x/jour, cohérent avec le choix de données différées
def get_saison(annee: int, circuit: str = "atp") -> pd.DataFrame:
    """
    Télécharge le fichier Excel d'une saison.
    circuit: "atp" ou "wta" (le site distingue les deux avec un suffixe différent).
    """
    suffixe = "" if circuit == "atp" else "w"
    url = f"{BASE_URL}/{annee}{suffixe}/{annee}.xlsx"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return pd.read_excel(io.BytesIO(resp.content))


def vers_schema_commun(ligne: pd.Series) -> Event:
    """Convertit une ligne du fichier tennis-data.co.uk vers le schéma Event commun."""
    participants = [
        Participant(
            id=ligne["Winner"], name=ligne["Winner"], sport=Sport.TENNIS,
            meta={"surface": ligne.get("Surface")},
        ),
        Participant(
            id=ligne["Loser"], name=ligne["Loser"], sport=Sport.TENNIS,
            meta={"surface": ligne.get("Surface")},
        ),
    ]
    return Event(
        id=f"{ligne['Tournament']}_{ligne['Date']}_{ligne['Winner']}_{ligne['Loser']}",
        sport=Sport.TENNIS,
        date=pd.to_datetime(ligne["Date"]).to_pydatetime(),
        participants=participants,
        competition=ligne.get("Tournament"),
        meta={"surface": ligne.get("Surface"), "round": ligne.get("Round")},
    )
