import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import math
import plotly.express as px

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026 - Cloud DB", layout="wide", page_icon="🍸")

# --- Σύνδεση με Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Διαβάζουμε τα δεδομένα από τα αντίστοιχα tabs του Google Sheet
    # Το ttl=0 σημαίνει ότι δεν κρατάει cache, ώστε να βλέπουμε αμέσως τις αλλαγές των άλλων
    ing = conn.read(worksheet="Ingredients", ttl=0).dropna(how="all")
    rec = conn.read(worksheet="Recipes", ttl=0).dropna(how="all")
    orders = conn.read(worksheet="Orders", ttl=0).dropna(how="all")
    history = conn.read(worksheet="History", ttl=0).dropna(how="all")
    return ing, rec, orders, history

df_ing, df_rec, df_orders, df_history = load_data()

# Σταθερές
TOTAL_FIXED = 0.22  
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

def format_greek(value):
    if isinstance(value, (int, float)):
        return "{:.3f}".format(value).replace('.', ',')
    return value

# Επιλογές για τα Selectboxes
ing_options = ["ΚΕΝΟ", "Νερό"] + sorted(df_ing["Name"].unique().tolist()) if not df_ing.empty else ["ΚΕΝΟ", "Νερό"]
recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

# --- Sidebar ---
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "📝 Νέα Συνταγή", "📊 Διαχείριση", "🔍 Ανάλυση", "🛒 Παραγγελίες", "📈 Dashboard"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών (Google Sheets)")
    edited_ing = st.data_editor(df_ing, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Αποθήκευση στο Cloud"):
        # Υπολογισμός τιμής ανά ml πριν την αποθήκευση
        edited_ing["Τιμή/ml"] = edited_ing["Price"] / edited_ing["Volume"].replace(0, 1)
        conn.update(worksheet="Ingredients", data=edited_ing)
        st.success("Η Αποθήκη ενημερώθηκε στο Google Sheet!")
        st.rerun()

# --- 2. ΝΕΑ ΣΥΝΤΑΓΗ ---
elif page == "📝 Νέα Συνταγή":
    st.header("📝 Καταχώρηση Νέας Συνταγής")
    with st.form("new_recipe_form"):
        name = st.text_input("Όνομα Cocktail")
        cat_price = st.number_input("Τιμή Καταλόγου (€)", min_value=0.0, step=0.10)
        recipe_data = {}
        for i in range(1, 14):
            c1, c2 = st.columns([3, 1])
            with c1: recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = st.selectbox(f"Συστατικό {i}", ing_options, key=f"n_s_{i}")
            with c2: recipe_data[f"ML{i}"] = st.number_input(f"ML {i}", min_value=0.0, key=f"n_m_{i}")
        if st.form_submit_button("💾 Αποθήκευση"):
            if name:
                new_row = pd.DataFrame([{"Ονομα": name, "Τιμή Καταλόγου": cat_price, **recipe_data}])
                df_updated = pd.concat([df_rec, new_row], ignore_index=True)
                conn.update(worksheet="Recipes", data=df_updated)
                st.success("Η συνταγή προστέθηκε!")
                st.rerun()

# --- 3. ΔΙΑΧΕΙΡΙΣΗ ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία Συνταγών")
    ed = st.data_editor(df_rec, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Αποθήκευση Αλλαγών"):
        conn.update(worksheet="Recipes", data=ed)
        st.success("Οι συνταγές ενημερώθηκαν!")
        st.rerun()

# --- 4. ΑΝΑΛΥΣΗ ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση")
    if not df_rec.empty:
        discount = st.sidebar.slider("Έκπτωση Προσφοράς %", 0, 100, 0)
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        p_retail = float(r["Τιμή Καταλόγου"])
        p_custom = p_retail * (1 - discount/100)
        
        raw_cost, pure_alc_ml = 0.0, 0.0
        breakdown = []
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
            ml = float(r.get(f"ML{i}", 0))
            if ing_n not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml > 0:
                match = df_ing[df_ing["Name"] == ing_n]
                if not match.empty:
                    c_ml = float(match.iloc[0]["Τιμή/ml"])
                    raw_cost += (ml * c_ml)
                    pure_alc_ml += (ml * float(match.iloc[0]["Αλκοόλ %"]) / 100)
                    breakdown.append({"Υλικό": ing_n, "ML": ml, "Κόστος": ml * c_ml})

        efk = pure_alc_ml * tax_factor * 100
        total_production = raw_cost + TOTAL_FIXED 
        profit = p_custom - total_production

        st.subheader(f"Ανάλυση: {choice}")
        m = st.columns(5)
        m[0].metric("Υλικά", f"{format_greek(raw_cost)}€")
        m[1].metric("ΕΦΚ", f"{format_greek(efk)}€")
        m[2].metric("Σταθερά", f"{format_greek(TOTAL_FIXED)}€")
        m[3].metric("Σύνολο Κόστους", f"{format_greek(total_production)}€")
        m[4].metric("Καθαρό Κέρδος", f"{format_greek(profit)}€")
        
        st.table(pd.DataFrame(breakdown))

# --- 5. ΠΑΡΑΓΓΕΛΙΕΣ ---
elif page == "🛒 Παραγγελίες":
    st.header("🛒 Παραγγελίες (Shared)")
    col_a, col_b = st.columns([1, 1.3])
    with col_a:
        ed_orders = st.data_editor(df_orders, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Αποθήκευση Παραγγελιών"):
            conn.update(worksheet="Orders", data=ed_orders)
            st.rerun()

        if st.button("✅ ΟΛΟΚΛΗΡΩΣΗ & ΑΡΧΕΙΟΘΕΤΗΣΗ"):
            if not ed_orders.empty:
                new_h = ed_orders.copy()
                new_h["Ημερομηνία"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                updated_history = pd.concat([df_history, new_h], ignore_index=True)
                conn.update(worksheet="History", data=updated_history)
                conn.update(worksheet="Orders", data=pd.DataFrame(columns=df_orders.columns))
                st.success("Η παραγγελία αρχειοθετήθηκε στο Google Sheet!")
                st.rerun()

    with col_b:
        st.subheader("Ανάγκες Αγοράς")
        # (Εδώ παραμένει ο κώδικας υπολογισμού αναγκών όπως πριν)

# --- 6. DASHBOARD ---
elif page == "📈 Dashboard":
    st.header("📈 Στατιστικά από Google Sheets")
    if not df_history.empty:
        fig = px.bar(df_history.groupby("Cocktail")["Τεμάχια"].sum().reset_index(), x="Cocktail", y="Τεμάχia", title="Πωλήσεις")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_history.sort_values("Ημερομηνία", ascending=False))
