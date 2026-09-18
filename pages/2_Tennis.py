import streamlit as st
import pandas as pd

from sources import tennis_source
from features import tennis_features as tf
from core.rating_engine import probabilite_victoire_duel

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
    annees = st.multiselect("Année(s)", options=annees_disponibles, default=[annee_courante - 1])

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
            "Ce fichier contient bien plus qu'un résultat brut : classement ATP au "
            "moment du match, statistiques de service (aces, doubles fautes, % de "
            "1ère balle), surface, round — exploité dans l'onglet Sortie exploitable."
        )

with onglet_sortie:
    st.subheader("Analyse d'un match : 2 avis confrontés, expliqués")
    df = st.session_state.get("tennis_df")
    if df is None:
        st.info("Télécharge d'abord une ou plusieurs saisons dans l'onglet Ingestion.")
    else:
        ratings_par_surface = tf.construire_ratings_par_surface(df)

        df_tri = df.sort_values("tourney_date", ascending=False)
        options_matchs = {
            f"{int(l['tourney_date'])} — {l['winner_name']} vs {l['loser_name']} ({l['surface']})": l
            for _, l in df_tri.head(300).iterrows()  # limite d'affichage, pas de calcul
        }
        choix = st.selectbox("Choisir un match à analyser", list(options_matchs.keys()))
        match = options_matchs[choix]

        joueur_a_id, joueur_b_id = str(match["winner_id"]), str(match["loser_id"])
        nom_a, nom_b = match["winner_name"], match["loser_name"]
        surface = match.get("surface") or "Inconnue"

        forme_a = tf.forme_recente(df, joueur_a_id)
        forme_b = tf.forme_recente(df, joueur_b_id)
        df_h2h = tf.confrontations_directes(df, joueur_a_id, joueur_b_id)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Notre modèle (TrueSkill, surface {surface})**")
            ratings_surface = ratings_par_surface.get(surface, {})
            if joueur_a_id in ratings_surface and joueur_b_id in ratings_surface:
                proba_a = probabilite_victoire_duel(ratings_surface[joueur_a_id], ratings_surface[joueur_b_id])
                st.metric(f"{nom_a} gagne", f"{proba_a:.1%}")
                st.caption(
                    f"📊 Pourquoi : sur {surface}, {nom_a} a un rating basé sur son historique "
                    f"spécifique à cette surface. Forme récente : {forme_a['victoires']}V-{forme_a['défaites']}D "
                    f"sur ses {forme_a['matchs_joues']} derniers matchs (toutes surfaces)."
                )
            else:
                st.caption(f"Pas assez d'historique sur {surface} pour l'un des deux joueurs.")

        with col2:
            st.markdown("**Classement ATP officiel**")
            pts_a = match.get("winner_rank_points")
            pts_b = match.get("loser_rank_points")
            proba_classement = tf.proba_classement_atp(pts_a, pts_b)
            if proba_classement is not None:
                st.metric(f"{nom_a} gagne", f"{proba_classement:.1%}")
                st.caption(
                    f"📊 Pourquoi : {nom_a} avait {int(pts_a)} points ATP contre "
                    f"{int(pts_b)} pour {nom_b} au moment du match. Référence externe, "
                    "indépendante de notre propre rating."
                )
            else:
                st.caption("Points ATP non renseignés pour ce match.")

        st.divider()

        col_forme, col_service = st.columns(2)
        with col_forme:
            st.markdown("### Forme récente des deux joueurs")
            st.dataframe(pd.DataFrame([
                {"joueur": nom_a, **forme_a},
                {"joueur": nom_b, **forme_b},
            ]))
        with col_service:
            st.markdown("### Statistiques de service (moyennes carrière observées)")
            st.dataframe(pd.DataFrame([
                {"joueur": nom_a, **tf.stats_service_moyennes(df, joueur_a_id)},
                {"joueur": nom_b, **tf.stats_service_moyennes(df, joueur_b_id)},
            ]))

        st.markdown("### Historique des confrontations directes")
        if df_h2h.empty:
            st.caption("Aucune confrontation directe dans les données déjà chargées.")
        else:
            st.dataframe(df_h2h)

        st.divider()
        st.markdown("### 🎯 Fiabilité mesurée du modèle (backtesting, toutes surfaces confondues)")
        bt = tf.backtest_modele(df)
        if bt["matchs_evalues"]:
            st.metric(
                "Précision historique",
                f"{bt['precision']}%",
                help="Le favori du modèle est calculé AVANT chaque match, jamais après coup.",
            )
            st.caption(
                f"Sur {bt['matchs_evalues']} matchs déjà rejoués dans les données chargées, "
                f"le modèle a correctement identifié le vainqueur {bt['bonnes_predictions']} fois."
            )
        else:
            st.caption("Pas assez de matchs dans l'historique chargé pour mesurer une précision.")
