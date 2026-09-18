import streamlit as st

from sources import mma_source
from core.rating_engine import nouveau_rating, probabilite_victoire_duel

st.set_page_config(page_title="MMA", page_icon="🥊", layout="wide")
st.title("🥊 MMA")

onglet_ingestion, onglet_exploration, onglet_sortie = st.tabs(
    ["1. Ingestion", "2. Exploration", "3. Sortie exploitable"]
)

with onglet_ingestion:
    st.subheader("Statut de connexion à la source")
    st.write("Source unique : **API-Sports MMA** (même compte que le football)")
    if "football" in st.secrets and st.secrets["football"].get("api_key"):
        st.success("Clé API détectée (partagée avec le football)")
    else:
        st.error("Aucune clé API trouvée dans .streamlit/secrets.toml")

    date = st.date_input("Date à interroger")
    if st.button("Tester la récupération des combats"):
        try:
            fights = mma_source.get_fights(date.isoformat())
            st.success(f"{len(fights)} combat(s) récupéré(s)")
            st.session_state["mma_fights"] = fights
        except Exception as e:
            st.error(f"Échec de la connexion : {e}")

with onglet_exploration:
    st.subheader("Ce que la donnée permet de calculer")
    fights = st.session_state.get("mma_fights", [])
    if not fights:
        st.info("Récupère d'abord des combats dans l'onglet Ingestion.")
    else:
        events = [mma_source.vers_schema_commun(f) for f in fights]
        st.dataframe(
            [{"date": e.date, "combattants": " vs ".join(p.name for p in e.participants),
              "catégorie": e.competition} for e in events]
        )
        st.caption(
            "Features spécifiques exploitables ici : catégorie de poids, "
            "organisation, cotes des bookmakers référencés par l'API."
        )

with onglet_sortie:
    st.subheader("Rating et probabilités (démonstration)")
    a, b = nouveau_rating(), nouveau_rating()
    proba = probabilite_victoire_duel(a, b)
    st.metric("Probabilité modèle (combattant A)", f"{proba:.1%}")
