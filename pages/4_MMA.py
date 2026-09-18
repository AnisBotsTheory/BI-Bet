import streamlit as st
import pandas as pd

from sources import mma_source
from features import mma_features as mf
from core.rating_engine import probabilite_victoire_duel

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

    st.markdown("### Choisir les deux combattants à comparer")
    col1, col2 = st.columns(2)
    nom_a = col1.text_input("Combattant 1", placeholder="ex: Jon Jones")
    nom_b = col2.text_input("Combattant 2", placeholder="ex: Stipe Miocic")

    if st.button("Rechercher et comparer"):
        if not nom_a or not nom_b:
            st.warning("Renseigne les deux noms.")
        else:
            try:
                resultats_a = mma_source.rechercher_combattant(nom_a)
                resultats_b = mma_source.rechercher_combattant(nom_b)
                if not resultats_a or not resultats_b:
                    st.error("Un des deux combattants n'a pas été trouvé — vérifie l'orthographe.")
                else:
                    fighter_a = resultats_a[0]  # si plusieurs homonymes, on prend le premier résultat
                    fighter_b = resultats_b[0]
                    combats_a = mma_source.get_combats_du_combattant(fighter_a["id"])
                    combats_b = mma_source.get_combats_du_combattant(fighter_b["id"])
                    # fusion en évitant les doublons (un combat commun apparaît dans les deux historiques)
                    combats_fusion = {c["fight"]["id"]: c for c in combats_a + combats_b}.values()

                    st.session_state["mma_combattant_a"] = fighter_a
                    st.session_state["mma_combattant_b"] = fighter_b
                    st.session_state["mma_combats"] = list(combats_fusion)
                    st.success(
                        f"{fighter_a['name']} ({len(combats_a)} combats) vs "
                        f"{fighter_b['name']} ({len(combats_b)} combats) — {len(combats_fusion)} combats uniques au total"
                    )
            except Exception as e:
                st.error(f"Échec de la connexion : {e}")

with onglet_exploration:
    st.subheader("Ce que la donnée permet de calculer")
    combats = st.session_state.get("mma_combats", [])
    if not combats:
        st.info("Recherche d'abord deux combattants dans l'onglet Ingestion.")
    else:
        st.dataframe([
            {"date": c["fight"]["date"], "combat": f"{c['fighters']['first']['name']} vs {c['fighters']['second']['name']}",
             "vainqueur": c.get("winner", {}).get("name"), "méthode": c.get("fight", {}).get("method")}
            for c in combats
        ])
        with st.expander("Voir toutes les données brutes renvoyées par l'API (tous les champs)"):
            df_brut = pd.json_normalize(combats)
            st.write(f"{df_brut.shape[1]} colonnes disponibles au total")
            st.dataframe(df_brut)

with onglet_sortie:
    st.subheader("Pronostic : qui bat qui ?")
    combats = st.session_state.get("mma_combats", [])
    fighter_a = st.session_state.get("mma_combattant_a")
    fighter_b = st.session_state.get("mma_combattant_b")

    if not combats or not fighter_a or not fighter_b:
        st.info("Recherche d'abord deux combattants dans l'onglet Ingestion.")
    else:
        id_a, id_b = str(fighter_a["id"]), str(fighter_b["id"])
        ratings = mf.construire_ratings(combats)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**{fighter_a['name']}**")
            if id_a in ratings and id_b in ratings:
                proba_a = probabilite_victoire_duel(ratings[id_a], ratings[id_b])
                st.metric("Probabilité de victoire", f"{proba_a:.1%}")
            else:
                st.caption("Pas assez d'historique pour l'un des deux combattants.")
            forme_a = mf.forme_recente(combats, id_a)
            st.caption(f"📊 Forme récente : {forme_a['victoires']}V-{forme_a['défaites']}D sur {forme_a['combats']} combats")

        with col2:
            st.markdown(f"**{fighter_b['name']}**")
            if id_a in ratings and id_b in ratings:
                proba_b = probabilite_victoire_duel(ratings[id_b], ratings[id_a])
                st.metric("Probabilité de victoire", f"{proba_b:.1%}")
            forme_b = mf.forme_recente(combats, id_b)
            st.caption(f"📊 Forme récente : {forme_b['victoires']}V-{forme_b['défaites']}D sur {forme_b['combats']} combats")

        st.caption(
            "⚠️ Si les deux combattants n'ont jamais affronté d'adversaires communs, "
            "la comparaison reste indicative — le rating est bâti sur des historiques "
            "en partie indépendants."
        )

        st.markdown("### Historique de confrontation directe")
        df_h2h = mf.confrontation_directe(combats, id_a, id_b)
        if df_h2h.empty:
            st.caption("Ces deux combattants ne se sont jamais affrontés dans les données disponibles.")
        else:
            st.dataframe(df_h2h)
