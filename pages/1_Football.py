import streamlit as st
import pandas as pd

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

    # --- Sélection en 2 temps : pays puis ligue, pour éviter une liste trop longue ---
    try:
        leagues = football_api.get_leagues()

        pays_disponibles = sorted({l["country"]["name"] for l in leagues if l["country"]["name"]})
        pays = st.selectbox("Pays", pays_disponibles, index=pays_disponibles.index("France") if "France" in pays_disponibles else 0)

        leagues_du_pays = [l for l in leagues if l["country"]["name"] == pays]
        options_ligues = {l["league"]["name"]: l["league"]["id"] for l in leagues_du_pays}
        nom_ligue = st.selectbox("Ligue", sorted(options_ligues.keys()))
        league_id = options_ligues[nom_ligue]
    except Exception as e:
        st.warning(f"Impossible de charger la liste des ligues ({e}) — saisie manuelle de l'ID en secours.")
        league_id = st.number_input("ID de la ligue", value=61)

    # --- Sélection de plusieurs saisons ---
    annee_courante = 2026
    saisons_disponibles = list(range(annee_courante - 15, annee_courante + 1))
    saisons = st.multiselect(
        "Saison(s)", options=saisons_disponibles, default=[annee_courante - 1]
    )

    if st.button("Tester la récupération des matchs"):
        if not saisons:
            st.warning("Sélectionne au moins une saison.")
        else:
            try:
                fixtures = football_api.get_fixtures_multi_saisons(league_id, saisons)
                st.success(f"{len(fixtures)} matchs récupérés sur {len(saisons)} saison(s)")
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

        with st.expander("Voir toutes les données brutes renvoyées par l'API (tous les champs)"):
            # aplatit le JSON imbriqué en un tableau avec une colonne par champ disponible
            df_brut = pd.json_normalize(fixtures)
            st.write(f"{df_brut.shape[1]} colonnes disponibles au total")
            st.dataframe(df_brut)

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
