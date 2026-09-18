import streamlit as st
import pandas as pd

from sources import football_api
from features import football_features as ff
from core.rating_engine import probabilite_victoire_duel
from core.probability import normaliser_marche

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

        with st.expander("Voir toutes les données brutes renvoyées par l'API (tous les champs)"):
            df_brut = pd.json_normalize(fixtures)
            st.write(f"{df_brut.shape[1]} colonnes disponibles au total")
            st.dataframe(df_brut)

with onglet_sortie:
    st.subheader("Analyse d'un match : 3 avis confrontés, expliqués")
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

        home_id, away_id = str(match["teams"]["home"]["id"]), str(match["teams"]["away"]["id"])
        home_nom, away_nom = match["teams"]["home"]["name"], match["teams"]["away"]["name"]
        fixture_id = match["fixture"]["id"]
        arbitre_match = match["fixture"].get("referee")

        forme_home = ff.forme_recente(fixtures, home_id)
        forme_away = ff.forme_recente(fixtures, away_id)
        df_h2h = ff.confrontations_directes(fixtures, home_id, away_id)

        col1, col2, col3 = st.columns(3)

        # --- 1. Notre rating TrueSkill, avec justification ---
        with col1:
            st.markdown("**Notre modèle (TrueSkill)**")
            if home_id in ratings and away_id in ratings:
                proba_home = probabilite_victoire_duel(ratings[home_id], ratings[away_id])
                st.metric(f"{home_nom} gagne", f"{proba_home:.1%}")
                raison = (
                    f"{home_nom} : {forme_home['points']} pts sur ses {forme_home['matchs_joues']} derniers "
                    f"matchs ({forme_home['points_par_match']} pts/match). "
                    f"{away_nom} : {forme_away['points']} pts sur {forme_away['matchs_joues']} "
                    f"({forme_away['points_par_match']} pts/match)."
                )
                if not df_h2h.empty:
                    raison += f" Historique direct : {len(df_h2h)} confrontation(s) déjà connue(s) (voir plus bas)."
                st.caption(f"📊 Pourquoi : {raison}")
            else:
                st.caption("Pas assez d'historique pour ces équipes.")

        # --- 2. Pronostic natif API-Football, avec ses propres explications ---
        with col2:
            st.markdown("**Pronostic API-Football**")
            try:
                pred = football_api.get_predictions(fixture_id)
                if pred:
                    winner = pred.get("predictions", {}).get("winner", {}).get("name", "?")
                    comment = pred.get("predictions", {}).get("winner", {}).get("comment", "")
                    st.metric("Favori algorithmique", winner)
                    st.caption(comment)

                    conseil = pred.get("predictions", {}).get("advice")
                    if conseil:
                        st.caption(f"💡 Conseil de l'algorithme : {conseil}")

                    comparaison = pred.get("comparison", {})
                    if comparaison:
                        st.caption("📊 Pourquoi (comparaison interne à l'API) :")
                        lignes_comp = {
                            critere: [valeurs.get("home"), valeurs.get("away")]
                            for critere, valeurs in comparaison.items()
                        }
                        st.dataframe(
                            pd.DataFrame(lignes_comp, index=[home_nom, away_nom]).T
                        )
                else:
                    st.caption("Aucun pronostic disponible pour ce match.")
            except Exception as e:
                st.caption(f"Indisponible : {e}")

        # --- 3. Probabilité implicite du marché, avec explication de ce qu'elle représente ---
        with col3:
            st.markdown("**Marché (cotes)**")
            try:
                odds_bruts = football_api.get_odds(fixture_id)
                cotes = football_api.extraire_cotes_1x2(odds_bruts)
                if cotes:
                    probas_marche = normaliser_marche([cotes["home"], cotes["draw"], cotes["away"]])
                    st.metric(f"{home_nom} gagne", f"{probas_marche[0]:.1%}")
                    st.caption(f"Cote moyenne : {cotes['home']:.2f}")
                    st.caption(
                        "📊 Pourquoi : cette probabilité vient de la moyenne des cotes de "
                        "plusieurs bookmakers. Elle intègre potentiellement des informations "
                        "non publiques (blessures, mise en forme interne) — à traiter comme "
                        "un signal de référence, pas une vérité absolue."
                    )
                else:
                    st.caption("Pas de cotes disponibles pour ce match (fréquent sur divisions amateurs ou matchs anciens).")
            except Exception as e:
                st.caption(f"Indisponible : {e}")

        st.divider()

        col_forme, col_arbitre = st.columns(2)
        with col_forme:
            st.markdown("### Forme récente des deux équipes")
            st.dataframe(pd.DataFrame([
                {"équipe": home_nom, **forme_home},
                {"équipe": away_nom, **forme_away},
            ]))
        with col_arbitre:
            st.markdown("### Statistiques de l'arbitre de ce match")
            if arbitre_match:
                df_arbitres = ff.stats_arbitres(fixtures)
                ligne_arbitre = df_arbitres[df_arbitres["arbitre"] == arbitre_match]
                if not ligne_arbitre.empty:
                    st.dataframe(ligne_arbitre)
                else:
                    st.caption(f"{arbitre_match} : pas assez de matchs dans l'historique chargé (seuil : 3 minimum).")
            else:
                st.caption("Arbitre non renseigné pour ce match.")

        st.markdown("### Historique des confrontations directes")
        if df_h2h.empty:
            st.caption("Aucune confrontation directe dans les données déjà chargées.")
        else:
            st.dataframe(df_h2h)

        st.divider()
        st.markdown("### 🎯 Fiabilité mesurée du modèle sur cette ligue (backtesting)")
        bt = ff.backtest_modele(fixtures)
        if bt["matchs_evalues"]:
            st.metric(
                "Précision historique (hors nuls, hors 1ers matchs de chaque équipe)",
                f"{bt['precision']}%",
                help="Le favori du modèle a été calculé AVANT chaque match, jamais après coup.",
            )
            st.caption(
                f"Sur {bt['matchs_evalues']} matchs déjà rejoués dans les données chargées, "
                f"le modèle a correctement identifié le vainqueur {bt['bonnes_predictions']} fois. "
                "Cette mesure sert à juger la confiance à accorder au modèle sur cette ligue précise, "
                "pas à garantir un résultat futur."
            )
        else:
            st.caption("Pas assez de matchs terminés dans l'historique chargé pour mesurer une précision.")
