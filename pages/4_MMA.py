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
    st.caption("Tape au moins 3 lettres — les suggestions apparaissent automatiquement en dessous.")
    col1, col2 = st.columns(2)
    nom_a = col1.text_input("Combattant 1", placeholder="ex: Jon Jones")
    nom_b = col2.text_input("Combattant 2", placeholder="ex: Stipe Miocic")

    choix_a, choix_b = None, None

    with col1:
        if len(nom_a.strip()) >= 3:
            try:
                resultats_a = mma_source.rechercher_combattant(nom_a.strip())
                if resultats_a:
                    choix_a = st.selectbox(
                        "Suggestions",
                        resultats_a,
                        format_func=lambda f: f"{f.get('name')} — id {f.get('id')}" + (f" — {f.get('nickname')}" if f.get('nickname') else ""),
                        key="select_a",
                    )
                else:
                    st.caption("Aucune suggestion trouvée.")
            except Exception as e:
                st.caption(f"Erreur de recherche : {e}")

    with col2:
        if len(nom_b.strip()) >= 3:
            try:
                resultats_b = mma_source.rechercher_combattant(nom_b.strip())
                if resultats_b:
                    choix_b = st.selectbox(
                        "Suggestions",
                        resultats_b,
                        format_func=lambda f: f"{f.get('name')} — id {f.get('id')}" + (f" — {f.get('nickname')}" if f.get('nickname') else ""),
                        key="select_b",
                    )
                else:
                    st.caption("Aucune suggestion trouvée.")
            except Exception as e:
                st.caption(f"Erreur de recherche : {e}")

    if choix_a and choix_b:
        with st.expander("Voir la fiche brute des deux combattants sélectionnés (pour vérifier l'ID)"):
            st.json({"combattant_1": choix_a, "combattant_2": choix_b})

        if st.button("Charger l'historique de ces deux combattants"):
            try:
                combats_a = mma_source.get_combats_du_combattant(choix_a["id"])
                combats_b = mma_source.get_combats_du_combattant(choix_b["id"])
                combats_fusion = {c["fight"]["id"]: c for c in combats_a + combats_b}.values()

                st.session_state["mma_combattant_a"] = choix_a
                st.session_state["mma_combattant_b"] = choix_b
                st.session_state["mma_combats"] = list(combats_fusion)
                st.success(
                    f"{choix_a['name']} ({len(combats_a)} combats) vs "
                    f"{choix_b['name']} ({len(combats_b)} combats) — {len(combats_fusion)} combats uniques au total"
                )
                if len(combats_a) == 0 or len(combats_b) == 0:
                    st.warning(
                        "Un des deux combattants ressort avec 0 combat — c'est suspect si c'est "
                        "un combattant connu. Utilise le mode diagnostic ci-dessous pour comprendre pourquoi."
                    )
            except Exception as e:
                st.error(f"Échec de la connexion : {e}")

    with st.expander("🔧 Mode diagnostic : voir pourquoi la recherche ne renvoie rien"):
        st.caption(
            "Le nom exact du paramètre de recherche n'a pas pu être confirmé à l'avance "
            "dans la documentation publique. Ce bouton teste plusieurs noms possibles "
            "(search, name, lastname, q) sur le nom du Combattant 1 et montre la réponse "
            "brute de chacun, pour identifier lequel fonctionne réellement."
        )
        if st.button("Lancer le diagnostic sur Combattant 1"):
            if not nom_a:
                st.warning("Renseigne au moins le nom du Combattant 1.")
            else:
                essais = mma_source.rechercher_combattant_debug(nom_a)
                for nom_param, resultat in essais.items():
                    st.write(f"**Paramètre testé : `{nom_param}`**")
                    st.json(resultat)

    with st.expander("🔧 Mode diagnostic : voir pourquoi l'historique de combats est vide"):
        st.caption(
            "Recherche confirmée fonctionnelle (paramètre 'search'). Ce diagnostic teste "
            "maintenant plusieurs noms de paramètre pour /fights (fighter, id, fighter_id) "
            "sur l'ID du combattant sélectionné."
        )
        id_test = st.number_input("ID du combattant à tester", value=choix_a["id"] if choix_a else 214)
        if st.button("Lancer le diagnostic sur /fights"):
            essais = mma_source.get_combats_du_combattant_debug(id_test)
            for nom_param, resultat in essais.items():
                st.write(f"**Paramètre testé : `{nom_param}`**")
                st.json(resultat)

        with st.expander("🔧 Mode diagnostic : tester plusieurs noms de paramètre pour /fights"):
            st.caption(
                "La documentation publique du paramètre exact de l'endpoint /fights n'a pas pu "
                "être confirmée à l'avance. Ce bouton teste plusieurs noms possibles et montre "
                "la réponse brute de chacun, pour identifier lequel fonctionne réellement."
            )
            if st.button("Lancer le diagnostic sur Combattant 1"):
                essais = mma_source.get_combats_du_combattant_debug(choix_a["id"])
                for nom_param, resultat in essais.items():
                    st.write(f"**Paramètre testé : `{nom_param}`**")
                    st.json(resultat)

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
