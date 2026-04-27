import streamlit as st
import pandas as pd

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

SHEET_ID = "18vCTHJk-3b5yrGQgZvD512bEPZhozOlWNHrkDu6j2Fc"

def load_data_from_gsheets():
    # Χρησιμοποιούμε τη μέθοδο pub?output=csv που είναι η πιο συμβατή
    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/pub?output=csv"
    
    try:
        # Φόρτωση Υλικών (gid=1439247167)
        ing = pd.read_csv(f"{base_url}&gid=1439247167")
        # Φόρτωση Συνταγών (gid=1224898150)
        rec = pd.read_csv(f"{base_url}&gid=1224898150")
        
        # Καθαρισμός κενών από τις κεφαλίδες
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

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Αποθήκη (Live)")
    if not df_ing.empty:
        # Εμφανίζουμε τον πίνακα όπως είναι στο Google Sheet
        st.dataframe(df_ing, use_container_width=True)
    else:
        st.warning("Δεν βρέθηκαν δεδομένα. Βεβαιωθείτε ότι το Google Sheet είναι προσβάσιμο.")

# --- 2. ΟΙΚΟΝΟΜΙΚΗ ΑΝΑΛΥΣΗ ---
elif page == "🔍 Οικονομική Ανάλυση":
    st.header("🔍 Ανάλυση Κόστους Συνταγής")
    
    if not df_rec.empty and not df_ing.empty:
        # Επιλογή Cocktail από τη στήλη 'Όνομα'
        cocktail_list = df_rec['Όνομα'].dropna().unique()
        choice = st.selectbox("Επιλέξτε Cocktail:", cocktail_list)
        
        r = df_rec[df_rec["Όνομα"] == choice].iloc[0]
        
        total_cost = 0.0
        breakdown = []
        
        # Υπολογισμός για 5 συστατικά
        for i in range(1, 6):
            ing_col = f"ΣΥΣΤΑΤΙΚΟ{i}"
            ml_col = f"ML{i}"
            
            ing_name = str(r.get(ing_col, "")).strip()
            ml_val = r.get(ml_col, 0)
            
            # Αγνοούμε το νερό και τα κενά
            if ing_name and ing_name.upper() not in ["NAN", "NEPO", "ΝΕΡΟ", ""]:
                # Αναζήτηση στην αποθήκη (στήλη 'Name')
                match = df_ing[df_ing["Name"].str.strip() == ing_name]
                
                if not match.empty:
                    try:
                        # Καθαρισμός τιμών από € και μετατροπή κόμματος σε τελεία
                        p_raw = str(match.iloc[0]["Price"]).replace('€', '').replace('.', '').replace(',', '.').strip()
                        v_raw = str(match.iloc[0]["Volume"]).replace('.', '').replace(',', '.').strip()
                        
                        price_per_ml = float(p_raw) / float(v_raw)
                        cost = float(ml_val) * price_per_ml
                        total_cost += cost
                        breakdown.append({"Υλικό": ing_name, "ML": ml_val, "Κόστος (€)": round(cost, 3)})
                    except:
                        continue

        # Εμφάνιση Αποτελεσμάτων
        st.metric("Συνολικό Κόστος Υλικών", f"{round(total_cost, 3)} €")
        if breakdown:
            st.table(pd.DataFrame(breakdown))
        else:
            st.info("Δεν βρέθηκαν αντιστοιχίες υλικών. Βεβαιωθείτε ότι τα ονόματα στις 'ΣΥΝΤΑΓΕΣ' είναι ίδια με το 'Name' στην 'Αποθήκη'.")
