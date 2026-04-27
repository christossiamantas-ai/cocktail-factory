import streamlit as st
import pandas as pd

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

SHEET_ID = "18vCTHJk-3b5yrGQgZvD512bEPZhozOlWNHrkDu6j2Fc"

def load_data_from_gsheets():
    # Χρησιμοποιούμε το GID για να αποφύγουμε προβλήματα με τα Ελληνικά ονόματα στο URL
    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    
    try:
        # gid=1439247167 είναι το φύλλο "Κόστος Α' Υλών"
        # gid=1224898150 είναι το φύλλο "ΣΥΝΤΑΓΕΣ"
        ing = pd.read_csv(f"{base_url}&gid=1439247167")
        rec = pd.read_csv(f"{base_url}&gid=1224898150")
        
        # Καθαρισμός κενών από τις κεφαλίδες
        ing.columns = ing.columns.str.strip()
        rec.columns = rec.columns.str.strip()
        
        return ing, rec
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_ing, df_rec = load_data_from_gsheets()

# --- Sidebar ---
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "🔍 Οικονομική Ανάλυση"])

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Αποθήκη (Live)")
    if not df_ing.empty:
        st.dataframe(df_ing, use_container_width=True)
    else:
        st.warning("Δεν βρέθηκαν δεδομένα.")

# --- 2. ΟΙΚΟΝΟΜΙΚΗ ΑΝΑΛΥΣΗ ---
elif page == "🔍 Οικονομική Ανάλυση":
    st.header("🔍 Ανάλυση Κόστους Συνταγής")
    
    if not df_rec.empty and not df_ing.empty:
        # Στο φύλλο σου η στήλη λέγεται 'Όνομα'
        cocktail_list = df_rec['Όνομα'].dropna().unique()
        choice = st.selectbox("Επιλέξτε Cocktail:", cocktail_list)
        
        r = df_rec[df_rec["Όνομα"] == choice].iloc[0]
        
        total_cost = 0.0
        breakdown = []
        
        # Έλεγχος για 5 συστατικά (ΣΥΣΤΑΤΙΚΟ1, ML1 κλπ)
        for i in range(1, 6):
            ing_col = f"ΣΥΣΤΑΤΙΚΟ{i}"
            ml_col = f"ML{i}"
            
            ing_name = str(r.get(ing_col, "")).strip()
            ml_val = r.get(ml_col, 0)
            
            if ing_name and ing_name.upper() not in ["NAN", "NEPO", "ΝΕΡΟ", ""]:
                # Ψάχνουμε το υλικό στη στήλη 'Name' του φύλλου υλικών
                match = df_ing[df_ing["Name"].str.strip() == ing_name]
                
                if not match.empty:
                    try:
                        # Μετατροπή τιμής (π.χ. 14,780 € -> 14.78)
                        price_str = str(match.iloc[0]["Price"]).replace('€', '').replace('.', '').replace(',', '.').strip()
                        vol_str = str(match.iloc[0]["Volume"]).replace('.', '').replace(',', '.').strip()
                        
                        price_per_ml = float(price_str) / float(vol_str)
                        cost = float(ml_val) * price_per_ml
                        total_cost += cost
                        breakdown.append({"Υλικό": ing_name, "ML": ml_val, "Κόστος (€)": round(cost, 3)})
                    except:
                        continue

        st.subheader(f"Συνολικό Κόστος Υλικών: {round(total_cost, 3)} €")
        if breakdown:
            st.table(pd.DataFrame(breakdown))
        else:
            st.info("Δεν βρέθηκαν αντιστοιχίες υλικών. Ελέγξτε αν τα ονόματα στις 'ΣΥΝΤΑΓΕΣ' είναι ολόιδια με το 'Name' στην 'Αποθήκη'.")
