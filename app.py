import streamlit as st
import pandas as pd
import plotly.express as px

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

# Το ID του Google Sheet σου (από το link που μου έστειλες)
SHEET_ID = "18vCTHJk-3b5yrGQgZvD512bEPZhozOlWNHrkDu6j2Fc"

def load_data_from_gsheets():
    # Κατασκευή URL για απευθείας λήψη CSV από κάθε tab
    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"
    
    try:
        # Διαβάζουμε τα φύλλα χρησιμοποιώντας το όνομά τους (sheet_name)
        ing = pd.read_csv(f"{base_url}&sheet=Ingredients")
        rec = pd.read_csv(f"{base_url}&sheet=Recipes")
        orders = pd.read_csv(f"{base_url}&sheet=Orders")
        history = pd.read_csv(f"{base_url}&sheet=History")
        return ing, rec, orders, history
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης με το Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Φόρτωση δεδομένων
df_ing, df_rec, df_orders, df_history = load_data_from_gsheets()

# Σταθερές & Ρυθμίσεις
TOTAL_FIXED = 0.22  
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

def format_greek(value):
    if isinstance(value, (int, float)):
        return "{:.3f}".format(value).replace('.', ',')
    return str(value)

# --- Sidebar ---
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "📝 Συνταγές", "🔍 Ανάλυση", "🛒 Παραγγελίες", "📈 Dashboard"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Αποθήκη (Live από Google Sheets)")
    if not df_ing.empty:
        st.dataframe(df_ing, use_container_width=True)
        st.info("💡 Για να αλλάξετε τις τιμές, επεξεργαστείτε το Google Sheet σας απευθείας. Η εφαρμογή θα ενημερωθεί με ένα Refresh.")
    else:
        st.warning("Δεν βρέθηκαν δεδομένα στο φύλλο Ingredients.")

# --- 2. ΣΥΝΤΑΓΕΣ ---
elif page == "📝 Συνταγές":
    st.header("📝 Λίστα Συνταγών")
    if not df_rec.empty:
        st.dataframe(df_rec, use_container_width=True)
    else:
        st.warning("Δεν βρέθηκαν δεδομένα στο φύλλο Recipes.")

# --- 3. ΑΝΑΛΥΣΗ ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση")
    if not df_rec.empty and not df_ing.empty:
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        raw_cost = 0.0
        pure_alc_ml = 0.0
        breakdown = []
        
        # Υπολογισμός κόστους από τα 13 πιθανά συστατικά
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", ""))
            ml = r.get(f"ML{i}", 0)
            if ing_n and ing_n != "nan" and ing_n != "Νερό" and ml > 0:
                match = df_ing[df_ing["Name"] == ing_n]
                if not match.empty:
                    price_per_ml = float(match.iloc[0]["Price"]) / float(match.iloc[0]["Volume"])
                    cost = ml * price_per_ml
                    raw_cost += cost
                    pure_alc_ml += (ml * float(match.iloc[0]["Αλκοόλ %"]) / 100)
                    breakdown.append({"Υλικό": ing_n, "ML": ml, "Κόστος": cost})

        efk = pure_alc_ml * tax_factor * 100
        total_production = raw_cost + efk + TOTAL_FIXED
        price_retail = float(r["Τιμή Καταλόγου"])
        profit = price_retail - total_production

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Κόστος Υλικών", f"{format_greek(raw_cost)}€")
        col2.metric("ΕΦΚ", f"{format_greek(efk)}€")
        col3.metric("Σύνολο Κόστους", f"{format_greek(total_production)}€")
        col4.metric("Κέρδος", f"{format_greek(profit)}€")
        
        st.table(pd.DataFrame(breakdown))

# --- 4. ΠΑΡΑΓΓΕΛΙΕΣ ---
elif page == "🛒 Παραγγελίες":
    st.header("🛒 Τρέχουσες Παραγγελίες")
    if not df_orders.empty:
        st.table(df_orders)
    else:
        st.write("Καμία εκκρεμής παραγγελία.")

# --- 5. DASHBOARD ---
elif page == "📈 Dashboard":
    st.header("📈 Ιστορικό Πωλήσεων")
    if not df_history.empty:
        fig = px.bar(df_history, x="Cocktail", y="Τεμάχια", color="Πελάτης", title="Ανάλυση Πωλήσεων")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Το ιστορικό είναι κενό.")
