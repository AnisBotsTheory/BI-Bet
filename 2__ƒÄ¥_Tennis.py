import streamlit as st

from sources import tennis_source
from core.rating_engine import nouveau_rating, probabilite_victoire_duel

st.set_page_config(page_title="Tennis", page_icon="🎾", layout="wide")
st.title("🎾 Tennis")

onglet_ingestion, onglet_exploration, onglet_sortie = st.tabs(
    ["1. Ingestion", "2. Exploration", "3. Sortie exploitable"]
)

with onglet_ingestion:
    st.subheader("Statut de connexion à la source")
    st.write("Source unique : **tennis-data.co.uk** (historique + cotes, pas de temps réel)")
    circuit = st.selectbox("Circuit", ["atp", "wta"])
    annee = st.number_input("Année", value=2025, min_value=2000, max_value=2026)
    if st.button("Tester le téléchargement de la saison"):
        try:
            df = tennis_source.get_saison(annee, circuit)
            st.success(f"{len(df)} matchs récupérés")
            st.session_state["tennis_df"] = df
        except Exception as e:
            st.error(f"Échec du téléchargement : {e}")

with onglet_exploration:
    st.subheader("Ce que la donnée permet de calculer")
    df = st.session_state.get("tennis_df")
    if df is None:
        st.info("Télécharge d'abord une saison dans l'onglet Ingestion.")
    else:
        st.write("Aperçu des colonnes disponibles :")
        st.dataframe(df.head(20))
        st.caption(
            "Features spécifiques exploitables ici : surface (terre/dur/gazon), "
            "round, cotes de plusieurs bookmakers pour la probabilité de marché."
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
