import streamlit as st
import pandas as pd
import plotly.express as px

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

# Το ID του Google Sheet σου
SHEET_ID = "18vCTHJk-3b5yrGQgZvD512bEPZhozOlWNHrkDu6j2Fc"

def load_data_from_gsheets():
    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"
    try:
        # Διαβάζουμε απευθείας τις ΔΙΚΕΣ ΣΟΥ καρτέλες
        ing = pd.read_csv(f"{base_url}&sheet=Κόστος%20Α'%20Υλών")
        rec = pd.read_csv(f"{base_url}&sheet=ΣΥΝΤΑΓΕΣ")
        
        # Καθαρισμός κενών διαστημάτων από τα ονόματα των στηλών
        ing.columns = ing.columns.str.strip()
        rec.columns = rec.columns.str.strip()
        
        return ing, rec
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Φόρτωση δεδομένων
df_ing, df_rec = load_data_from_gsheets()

# --- Sidebar ---
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "🔍 Οικονομική Ανάλυση"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", ["Ελλάδα", "Γερμανία", "Κύπρος"])

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Αποθήκη (Live)")
    if not df_ing.empty:
        # Μετατροπή τιμών σε αριθμούς (αφαιρούμε το € και αλλάζουμε το κόμμα σε τελεία)
        df_display = df_ing.copy()
        st.dataframe(df_display, use_container_width=True)
    else:
        st.warning("Δεν βρέθηκαν δεδομένα στο φύλλο 'Κόστος Α' Υλών'.")

# --- 2. ΟΙΚΟΝΟΜΙΚΗ ΑΝΑΛΥΣΗ ---
elif page == "🔍 Οικονομική Ανάλυση":
    st.header("🔍 Ανάλυση Κόστους Συνταγής")
    
    if not df_rec.empty and not df_ing.empty:
        # Επιλογή Cocktail (στήλη 'Όνομα' από το φύλλο ΣΥΝΤΑΓΕΣ)
        cocktail_list = df_rec['Όνομα'].dropna().unique()
        choice = st.selectbox("Επιλέξτε Cocktail:", cocktail_list)
        
        r = df_rec[df_rec["Όνομα"] == choice].iloc[0]
        
        total_cost = 0.0
        breakdown = []
        
        # Σύμφωνα με τη φωτό σου, έχεις ΣΥΣΤΑΤΙΚΟ1, ML1, ΣΥΣΤΑΤΙΚΟ2, ML2...
        for i in range(1, 6): # Έλεγχος για τα πρώτα 5 συστατικά
            ing_col = f"ΣΥΣΤΑΤΙΚΟ{i}"
            ml_col = f"ML{i}"
            
            ing_name = str(r.get(ing_col, ""))
            ml_val = r.get(ml_col, 0)
            
            if ing_name and ing_name != "nan" and ing_name != "NEPO" and ing_name != "ΝΕΡΟ":
                # Ψάχνουμε το υλικό στο φύλλο 'Κόστος Α' Υλών' στη στήλη 'Name'
                match = df_ing[df_ing["Name"] == ing_name]
                
                if not match.empty:
                    # Καθαρισμός τιμής (π.χ. '14,780 €' -> 14.78)
                    price_raw = str(match.iloc[0]["Price"]).replace('€', '').replace(',', '.').strip()
                    vol_raw = str(match.iloc[0]["Volume"]).replace(',', '.').strip()
                    
                    try:
                        price_per_ml = float(price_raw) / float(vol_raw)
                        cost = float(ml_val) * price_per_ml
                        total_cost += cost
                        breakdown.append({"Υλικό": ing_name, "ML": ml_val, "Κόστος (€)": round(cost, 3)})
                    except:
                        continue

        st.subheader(f"Συνολικό Κόστος Υλικών: {round(total_cost, 3)} €")
        st.table(pd.DataFrame(breakdown))
        
        st.info("Σημείωση: Για να βγει το σωστό αποτέλεσμα, το όνομα του υλικού στις 'ΣΥΝΤΑΓΕΣ' πρέπει να είναι ολόιδιο με το 'Name' στο 'Κόστος Α' Υλών'.")
