import streamlit as st

from sources import mma_source
from core.rating_engine import nouveau_rating, probabilite_victoire_duel

st.set_page_config(page_title="MMA", page_icon="🥊", layout="wide")
st.title("🥊 MMA")
st.info("Onglet en phase d'exploration — pas de cotes gratuites en temps réel disponibles.")

onglet_ingestion, onglet_exploration, onglet_sortie = st.tabs(
    ["1. Ingestion", "2. Exploration", "3. Sortie exploitable"]
)

with onglet_ingestion:
    st.subheader("Statut de connexion à la source")
    st.write("Source unique : **Ultimate UFC Dataset** (Kaggle, mdabbert) — dataset statique")
    if st.button("Charger le dataset local"):
        try:
            df = mma_source.charger_dataset()
            st.success(f"{len(df)} combats chargés")
            st.session_state["mma_df"] = df
        except FileNotFoundError as e:
            st.error(str(e))

with onglet_exploration:
    st.subheader("Ce que la donnée permet de calculer")
    df = st.session_state.get("mma_df")
    if df is None:
        st.info("Charge d'abord le dataset dans l'onglet Ingestion.")
    else:
        st.dataframe(df.head(20))
        st.caption(
            "Features spécifiques exploitables ici : catégorie de poids, "
            "méthode de victoire (finish), cotes historiques incluses au dataset."
        )

with onglet_sortie:
    st.subheader("Rating et probabilités (démonstration)")
    a, b = nouveau_rating(), nouveau_rating()
    proba = probabilite_victoire_duel(a, b)
    st.metric("Probabilité modèle (combattant A)", f"{proba:.1%}")
