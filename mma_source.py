"""
Source unique retenue pour le MMA : Ultimate UFC Dataset (Kaggle, mdabbert).
Ce dataset a déjà fusionné ufcstats.com + cotes + classements dans un seul
schéma - pas besoin de recouper plusieurs datasets Kaggle entre eux.

A télécharger manuellement une première fois (compte Kaggle requis) :
https://www.kaggle.com/datasets/mdabbert/ultimate-ufc-dataset
puis placer le CSV dans data/cache/ufc_dataset.csv
"""

import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime

from core.schema import Event, Participant, Sport

CHEMIN_LOCAL = Path("data/cache/ufc_dataset.csv")


@st.cache_data(ttl=None)  # dataset statique, mis à jour manuellement (pas de temps réel voulu)
def charger_dataset() -> pd.DataFrame:
    if not CHEMIN_LOCAL.exists():
        raise FileNotFoundError(
            "Dataset MMA introuvable. Télécharge-le depuis Kaggle "
            "(mdabbert/ultimate-ufc-dataset) et place-le dans data/cache/ufc_dataset.csv"
        )
    return pd.read_csv(CHEMIN_LOCAL)


def vers_schema_commun(ligne: pd.Series) -> Event:
    """Convertit une ligne du dataset vers le schéma Event commun."""
    participants = [
        Participant(id=ligne["RedFighter"], name=ligne["RedFighter"], sport=Sport.MMA),
        Participant(id=ligne["BlueFighter"], name=ligne["BlueFighter"], sport=Sport.MMA),
    ]
    return Event(
        id=f"{ligne['Date']}_{ligne['RedFighter']}_{ligne['BlueFighter']}",
        sport=Sport.MMA,
        date=pd.to_datetime(ligne["Date"]).to_pydatetime(),
        participants=participants,
        competition=ligne.get("WeightClass"),
        meta={"methode": ligne.get("Finish")},
    )
