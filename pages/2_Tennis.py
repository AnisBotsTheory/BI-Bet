import streamlit as st
import pandas as pd

from sources import tennis_source
from core.rating_engine import nouveau_rating, probabilite_victoire_duel

st.set_page_config(page_title="Tennis", page_icon="🎾", layout="wide")
st.title("🎾 Tennis")

onglet_ingestion, onglet_exploration, onglet_sortie = st.tabs(
    ["1. Ingestion", "2. Exploration", "3. Sortie exploitable"]
)

with onglet_ingestion:
    st.subheader("Statut de connexion à la source")
    st.write("Source unique : **TennisMyLife (TML-Database)** — accès public, sans clé API")

    annee_courante = 2026
    annees_disponibles = list(range(2000, annee_courante + 1))
    annees = st.multiselect(
        "Année(s)", options=annees_disponibles, default=[annee_courante - 1]
    )

    if st.button("Tester le téléchargement des saisons"):
        if not annees:
            st.warning("Sélectionne au moins une année.")
        else:
            try:
                dfs = [tennis_source.get_saison(a) for a in annees]
                df = pd.concat(dfs, ignore_index=True)
                st.success(f"{len(df)} matchs récupérés sur {len(annees)} année(s)")
                st.session_state["tennis_df"] = df
            except Exception as e:
                st.error(f"Échec du téléchargement : {e}")

with onglet_exploration:
    st.subheader("Ce que la donnée permet de calculer")
    df = st.session_state.get("tennis_df")
    if df is None:
        st.info("Télécharge d'abord une ou plusieurs saisons dans l'onglet Ingestion.")
    else:
        st.write(f"{df.shape[1]} colonnes disponibles au total (toutes conservées, rien n'est filtré)")
        st.dataframe(df)
        st.caption(
            "Features spécifiques exploitables ici : surface (dur/terre/gazon), "
            "round, niveau du tournoi (Grand Chelem, Masters, etc.)."
        )

with onglet_sortie:
    st.subheader("Rating et probabilités (démonstration)")
    a, b = nouveau_rating(), nouveau_rating()
    proba = probabilite_victoire_duel(a, b)
    st.metric("Probabilité modèle (joueur A)", f"{proba:.1%}")
    st.caption(
        "À terme : rating décliné PAR SURFACE (un rating terre battue, "
        "un rating dur, un rating gazon) plutôt qu'un rating unique."
    )
