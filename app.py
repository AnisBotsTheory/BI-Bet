"""
Point d'entrée de l'application. Streamlit détecte automatiquement le
dossier pages/ et construit la navigation multi-onglets à partir de là.
"""

import streamlit as st

st.set_page_config(page_title="BI Paris Sportifs", page_icon="📊", layout="wide")

st.title("📊 Outil d'aide à la décision — paris sportifs")

st.warning(
    "**Cet outil est un support d'analyse, pas un pronostic garanti.** "
    "Vous restez seul responsable de vos décisions de mise. "
    "Jeu excessif : Joueurs Info Service, 09 74 75 13 13 (appel non surtaxé)."
)

st.markdown(
    """
    Utilisez le menu à gauche pour explorer chaque activité sportive.
    Chaque onglet suit la même logique en 3 blocs :

    1. **Ingestion** — statut de connexion à la source de données
    2. **Exploration** — ce que la donnée brute permet de calculer
    3. **Sortie exploitable** — rating et probabilités calculées

    Aucune donnée temps réel : les analyses portent sur des données
    consolidées, mises à jour quotidiennement ou hebdomadairement.
    """
)

st.subheader("Statut des sources par activité")
statuts = {
    "⚽ Football": "API-Football",
    "🎾 Tennis": "tennis-data.co.uk",
    "🐎 Hippique": "open-pmu-api",
    "🥊 MMA": "Ultimate UFC Dataset (Kaggle)",
}
for sport, source in statuts.items():
    st.markdown(f"- **{sport}** — source retenue : `{source}`")
