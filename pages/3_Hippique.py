import streamlit as st

from sources import hippique_source
from core.rating_engine import nouveau_rating, mettre_a_jour_classement, score_affichable

st.set_page_config(page_title="Hippique", page_icon="🐎", layout="wide")
st.title("🐎 Hippique")
st.info("Onglet en phase d'exploration — collecte plus lourde que foot/tennis (cf. cadrage projet).")

onglet_ingestion, onglet_exploration, onglet_sortie = st.tabs(
    ["1. Ingestion", "2. Exploration", "3. Sortie exploitable"]
)

with onglet_ingestion:
    st.subheader("Statut de connexion à la source")
    st.write("Source unique : **open-pmu-api** (résultats officiels PMU)")
    date = st.text_input("Date (MM/DD/YYYY)", value="08/18/2026")
    if st.button("Tester la récupération des arrivées"):
        try:
            courses = hippique_source.get_arrivees(date)
            st.success(f"{len(courses)} course(s) récupérée(s)")
            st.session_state["hippique_courses"] = courses
        except Exception as e:
            st.error(f"Échec de la connexion : {e}")

with onglet_exploration:
    st.subheader("Ce que la donnée permet de calculer")
    courses = st.session_state.get("hippique_courses", [])
    if not courses:
        st.info("Récupère d'abord des courses dans l'onglet Ingestion.")
    else:
        for c in courses:
            st.markdown(f"**{c.get('prix')}** — {c.get('lieu')} ({c.get('partants')} partants)")
        st.caption(
            "Features spécifiques exploitables ici : musique (forme codée), "
            "corde, jockey/entraîneur. Nécessite un travail de parsing dédié."
        )

with onglet_sortie:
    st.subheader("Rating à n participants (démonstration)")
    st.caption("Cas d'usage clé du moteur mutualisé TrueSkill : classement, pas un simple duel.")
    ratings_exemple = [nouveau_rating() for _ in range(5)]
    nouveaux = mettre_a_jour_classement(ratings_exemple)
    for i, r in enumerate(nouveaux, start=1):
        st.write(f"Position simulée {i} → score affichable : {score_affichable(r):.1f}")
