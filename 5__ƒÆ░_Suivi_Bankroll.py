import streamlit as st
import pandas as pd

st.set_page_config(page_title="Suivi / Bankroll", page_icon="💰", layout="wide")
st.title("💰 Suivi / Bankroll")

st.caption(
    "Historique transparent des mises — objectif : garder une vision réelle "
    "des gains/pertes, sans enjoliver (cf. positionnement anti-impulsivité)."
)

if "historique_mises" not in st.session_state:
    st.session_state["historique_mises"] = pd.DataFrame(
        columns=["date", "sport", "montant", "cote", "resultat", "gain_perte"]
    )

with st.form("ajouter_mise"):
    col1, col2, col3, col4 = st.columns(4)
    sport = col1.selectbox("Sport", ["Football", "Tennis", "Hippique", "MMA"])
    montant = col2.number_input("Montant misé (€)", min_value=0.0, step=1.0)
    cote = col3.number_input("Cote", min_value=1.0, step=0.1)
    resultat = col4.selectbox("Résultat", ["Gagné", "Perdu"])
    submit = st.form_submit_button("Ajouter")

if submit:
    gain_perte = montant * (cote - 1) if resultat == "Gagné" else -montant
    nouvelle_ligne = pd.DataFrame([{
        "date": pd.Timestamp.now(), "sport": sport, "montant": montant,
        "cote": cote, "resultat": resultat, "gain_perte": gain_perte,
    }])
    st.session_state["historique_mises"] = pd.concat(
        [st.session_state["historique_mises"], nouvelle_ligne], ignore_index=True
    )

df = st.session_state["historique_mises"]
if not df.empty:
    st.subheader("Historique")
    st.dataframe(df)

    st.subheader("P&L cumulé")
    df["pl_cumule"] = df["gain_perte"].cumsum()
    st.line_chart(df.set_index("date")["pl_cumule"])

    st.subheader("ROI par sport")
    roi = df.groupby("sport").apply(
        lambda g: g["gain_perte"].sum() / g["montant"].sum() if g["montant"].sum() else 0
    )
    st.bar_chart(roi)
else:
    st.info("Aucune mise enregistrée pour le moment.")
