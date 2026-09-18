import streamlit as st
import pandas as pd

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

    col1, col2 = st.columns(2)
    annee = col1.selectbox("Année", options=list(range(2004, 2027))[::-1])
    mois = col2.selectbox(
        "Mois",
        options=list(range(1, 13)),
        format_func=lambda m: ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                                "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"][m - 1],
    )
    st.caption(
        "L'API interroge jour par jour en coulisses (contrainte technique) — "
        "le premier chargement d'un mois peut prendre quelques secondes."
    )

    if st.button("Tester la récupération du mois"):
        try:
            courses = hippique_source.get_arrivees_mois(annee, mois)
            st.success(f"{len(courses)} course(s) récupérée(s) sur le mois")
            st.session_state["hippique_courses"] = courses
        except Exception as e:
            st.error(f"Échec de la connexion : {e}")

    with st.expander("🔧 Mode diagnostic : voir la réponse brute d'un jour précis"):
        st.caption(
            "Vérifie si le champ arrivee_details (noms de chevaux, jockeys, cotes) "
            "est bien présent pour une date donnée, ou si seules les infos "
            "générales de la course sont disponibles."
        )
        jour_test = st.text_input("Date à tester (MM/DD/YYYY)", value="08/18/2026")
        if st.button("Voir la réponse brute de ce jour"):
            try:
                brut = hippique_source.get_arrivees_debug(jour_test)
                st.json(brut)
            except Exception as e:
                st.error(f"Échec : {e}")

with onglet_exploration:
    st.subheader("Ce que la donnée permet de calculer")
    courses = st.session_state.get("hippique_courses", [])
    if not courses:
        st.info("Récupère d'abord un mois de courses dans l'onglet Ingestion.")
    else:
        for c in courses[:20]:
            st.markdown(f"**{c.get('prix')}** — {c.get('lieu')} ({c.get('partants')} partants)")
        if len(courses) > 20:
            st.caption(f"... et {len(courses) - 20} autre(s) course(s), voir le tableau complet ci-dessous.")

        with st.expander("Voir toutes les données brutes renvoyées par l'API (tous les champs)"):
            df_brut = pd.json_normalize(courses)
            st.write(f"{df_brut.shape[1]} colonnes disponibles au total")
            st.dataframe(df_brut)

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
