import streamlit as st
import pandas as pd

from sources import football_api
from features import football_features as ff
from core.rating_engine import score_affichable, probabilite_victoire_duel
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
        nom_ligue = st.selectbox("Ligue", sorted(options_ligues.keys()),
                                  index=sorted(options_ligues.keys()).index("Ligue 1") if "Ligue 1" in options_ligues else 0)
        league_id = options_ligues[nom_ligue]
    except Exception as e:
        st.warning(f"Impossible de charger la liste des ligues ({e}) — saisie manuelle de l'ID en secours.")
        league_id = st.number_input("ID de la ligue", value=61)

    annee_courante = 2026
    saisons_disponibles = list(range(annee_courante - 15, annee_courante + 1))
    saisons = st.multiselect("Saison(s)", options=saisons_disponibles, default=[annee_courante - 1])

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
        events_apercu = [
            {"date": f["fixture"]["date"], "équipes": f"{f['teams']['home']['name']} vs {f['teams']['away']['name']}",
             "score": f"{f['goals']['home']} - {f['goals']['away']}", "compétition": f["league"]["name"]}
            for f in fixtures
        ]
        st.write(f"{len(fixtures)} événements chargés")
        st.dataframe(events_apercu)

        st.markdown("### Forme récente par équipe")
        equipes = sorted({f["teams"]["home"]["name"]: str(f["teams"]["home"]["id"]) for f in fixtures}.items()
                          | {f["teams"]["away"]["name"]: str(f["teams"]["away"]["id"]) for f in fixtures}.items())
        lignes_forme = []
        for nom, tid in dict(equipes).items():
            forme = ff.forme_recente(fixtures, tid)
            lignes_forme.append({"équipe": nom, **forme})
        st.dataframe(pd.DataFrame(lignes_forme).sort_values("points_par_match", ascending=False))

        st.markdown("### Statistiques par arbitre")
        df_arbitres = ff.stats_arbitres(fixtures)
        if df_arbitres.empty:
            st.caption("Pas assez de matchs par arbitre pour être significatif (seuil : 3 matchs minimum).")
        else:
            st.dataframe(df_arbitres)

        with st.expander("Voir toutes les données brutes renvoyées par l'API (tous les champs)"):
            df_brut = pd.json_normalize(fixtures)
            st.write(f"{df_brut.shape[1]} colonnes disponibles au total")
            st.dataframe(df_brut)

with onglet_sortie:
    st.subheader("Analyse d'un match : 3 avis confrontés")
    fixtures = st.session_state.get("football_fixtures", [])
    if not fixtures:
        st.info("Récupère d'abord des matchs dans l'onglet Ingestion pour analyser un match précis.")
    else:
        ratings = ff.construire_ratings(fixtures)

        options_matchs = {
            f"{f['fixture']['date'][:10]} — {f['teams']['home']['name']} vs {f['teams']['away']['name']}": f
            for f in sorted(fixtures, key=lambda x: x["fixture"]["date"], reverse=True)
        }
        choix = st.selectbox("Choisir un match à analyser", list(options_matchs.keys()))
        match = options_matchs[choix]

        home_id = str(match["teams"]["home"]["id"])
        away_id = str(match["teams"]["away"]["id"])
        fixture_id = match["fixture"]["id"]

        col1, col2, col3 = st.columns(3)

        # --- 1. Notre rating TrueSkill ---
        with col1:
            st.markdown("**Notre modèle (TrueSkill)**")
            if home_id in ratings and away_id in ratings:
                proba_home = probabilite_victoire_duel(ratings[home_id], ratings[away_id])
                st.metric(f"{match['teams']['home']['name']} gagne", f"{proba_home:.1%}")
            else:
                st.caption("Pas assez d'historique pour ces équipes.")

        # --- 2. Pronostic natif API-Football (indépendant des cotes) ---
        with col2:
            st.markdown("**Pronostic API-Football**")
            try:
                pred = football_api.get_predictions(fixture_id)
                if pred:
                    winner = pred.get("predictions", {}).get("winner", {}).get("name", "?")
                    comment = pred.get("predictions", {}).get("winner", {}).get("comment", "")
                    st.metric("Favori algorithmique", winner)
                    st.caption(comment)
                else:
                    st.caption("Aucun pronostic disponible pour ce match.")
            except Exception as e:
                st.caption(f"Indisponible : {e}")

        # --- 3. Probabilité implicite du marché (cotes) ---
        with col3:
            st.markdown("**Marché (cotes)**")
            try:
                odds_bruts = football_api.get_odds(fixture_id)
                cotes = football_api.extraire_cotes_1x2(odds_bruts)
                if cotes:
                    probas_marche = normaliser_marche([cotes["home"], cotes["draw"], cotes["away"]])
                    st.metric(f"{match['teams']['home']['name']} gagne", f"{probas_marche[0]:.1%}")
                    st.caption(f"Cote moyenne : {cotes['home']:.2f}")
                else:
                    st.caption("Pas de cotes disponibles pour ce match (fréquent sur divisions amateurs ou matchs anciens).")
            except Exception as e:
                st.caption(f"Indisponible : {e}")

        st.markdown("### Historique des confrontations directes")
        df_h2h = ff.confrontations_directes(fixtures, home_id, away_id)
        if df_h2h.empty:
            st.caption("Aucune confrontation directe dans les données déjà chargées.")
        else:
            st.dataframe(df_h2h)
