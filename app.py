import streamlit as st
import pandas as pd

st.set_page_config(page_title="DC CABCLUB 2026", layout="wide")

# Το ID του εγγράφου σου
SHEET_ID = "18vCTHJk-3b5yrGQgZvD512bEPZhozOlWNHrkDu6j2Fc"

def load_data():
    # Χρήση του visualization URL που είναι το πιο σταθερό
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"
    try:
        # Φόρτωση Υλικών (gid=1439247167) και Συνταγών (gid=1224898150)
        ing = pd.read_csv(f"{url}&gid=1439247167")
        rec = pd.read_csv(f"{url}&gid=1224898150")
        
        # Καθαρισμός κενών στις κεφαλίδες
        ing.columns = ing.columns.str.strip()
        rec.columns = rec.columns.str.strip()
        return ing, rec
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_ing, df_rec = load_data()

st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "🔍 Οικονομική Ανάλυση"])

if page == "📦 Αποθήκη":
    st.header("📦 Αποθήκη (Live)")
    if not df_ing.empty:
        st.dataframe(df_ing, use_container_width=True)
    else:
        st.info("Αναμονή για δεδομένα... Βεβαιωθείτε ότι κάνατε 'Δημοσίευση στον ιστό'.")

elif page == "🔍 Οικονομική Ανάλυση":
    st.header("🔍 Ανάλυση Κόστους")
    if not df_rec.empty and not df_ing.empty:
        # Το πρόγραμμα βρίσκει μόνο του τα cocktail από τη στήλη 'Όνομα'
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec['Όνομα'].dropna().unique())
        st.success(f"Το Cocktail '{choice}' φορτώθηκε με επιτυχία από τη βάση σας!")
