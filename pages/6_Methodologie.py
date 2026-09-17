import streamlit as st

st.set_page_config(page_title="Méthodologie", page_icon="📖", layout="wide")
st.title("📖 Méthodologie")

st.error(
    "**Cet outil est un support d'aide à la décision, pas un service de "
    "pronostics garantis.** Vous restez seul responsable de vos décisions "
    "de mise. Aucune donnée ni aucun modèle statistique ne garantit un gain."
)

st.markdown(
    """
    ### Sources de données (une seule par sport, volontairement)
    - ⚽ Football : API-Football (api-sports.io)
    - 🎾 Tennis : tennis-data.co.uk
    - 🐎 Hippique : open-pmu-api
    - 🥊 MMA : Ultimate UFC Dataset (Kaggle)

    ### Moteur de rating
    TrueSkill, mutualisé entre tous les sports — gère aussi bien les duels
    (foot, tennis, MMA) que les classements à *n* participants (hippique).

    ### Choix du différé plutôt que du temps réel
    Réduit la responsabilité sur la véracité instantanée des données,
    limite les paris impulsifs, simplifie l'infrastructure.

    ### Limites connues
    - Les probabilités affichées sont des estimations statistiques, pas des certitudes
    - La qualité du rating dépend du volume d'historique disponible par participant
    - Aucune donnée médicale, tactique ou d'entraînement n'est intégrée
    """
)

st.info(
    "Jeu excessif : Joueurs Info Service — 09 74 75 13 13 (appel non surtaxé). "
    "Interdit aux mineurs."
)
