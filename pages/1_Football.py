import streamlit as st

from sources import football_api
from core.rating_engine import nouveau_rating, probabilite_victoire_duel
from core.probability import normaliser_marche, ecart_modele_vs_marche

st.set_page_config(page_title="Football", page_icon="⚽", layout="wide")
st.title("⚽ Football")

onglet_ingestion, onglet_exploration, onglet_sortie = st.tabs(
    ["1. Ingestion", "2. Exploration", "3. Sortie exploitable"]
)

with onglet_ingestion:
    st.subheader("Statut de connexion à la source")
    st.write("Source unique : **API-Football (api-sports.io)**")
    if "football" in st.secrets and st.secrets["football"].get("api_key"):
        st.success("Clé API détectée dans .streamlit/secrets.toml")
    else:
        st.error(
            "Aucune clé API trouvée. Ajoute-la dans .streamlit/secrets.toml :\n\n"
            "[football]\napi_key = \"ta_cle\""
        )

    league_id = st.number_input("ID de la ligue (ex: 61 = Ligue 1)", value=61)
    season = st.number_input("Saison", value=2025)
    if st.button("Tester la récupération des matchs"):
        try:
            fixtures = football_api.get_fixtures(league_id, season)
            st.success(f"{len(fixtures)} matchs récupérés")
            st.session_state["football_fixtures"] = fixtures
        except Exception as e:
            st.error(f"Échec de la connexion : {e}")

with onglet_exploration:
    st.subheader("Ce que la donnée permet de calculer")
    fixtures = st.session_state.get("football_fixtures", [])
    if not fixtures:
        st.info("Récupère d'abord des matchs dans l'onglet Ingestion.")
    else:
        events = [football_api.vers_schema_commun(f) for f in fixtures]
        st.write(f"{len(events)} événements convertis dans le schéma commun")
        st.dataframe(
            [{"date": e.date, "équipes": " vs ".join(p.name for p in e.participants),
              "compétition": e.competition} for e in events]
        )

with onglet_sortie:
    st.subheader("Rating et probabilités (démonstration)")
    st.caption(
        "Exemple avec deux ratings neutres — à remplacer par les ratings "
        "réels calculés sur l'historique une fois l'ingestion en place."
    )
    a, b = nouveau_rating(), nouveau_rating()
    proba_modele = probabilite_victoire_duel(a, b)
    st.metric("Probabilité modèle (équipe A)", f"{proba_modele:.1%}")

    st.markdown("**Comparaison avec le marché** (exemple avec des cotes saisies manuellement)")
    col1, col2, col3 = st.columns(3)
    cote_a = col1.number_input("Cote équipe A", value=2.10)
    cote_nul = col2.number_input("Cote nul", value=3.30)
    cote_b = col3.number_input("Cote équipe B", value=3.40)
    probas_marche = normaliser_marche([cote_a, cote_nul, cote_b])
    ecart = ecart_modele_vs_marche(proba_modele, probas_marche[0])
    st.metric("Écart modèle vs marché (équipe A)", f"{ecart:+.1%}")
