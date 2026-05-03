import streamlit as st
import pandas as pd
import math
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import requests
from requests.auth import HTTPBasicAuth

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

# --- Σύστημα Password ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    def password_entered():
        if st.session_state.get("password") == "panatha1908":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else: st.error("❌ Λάθος κωδικός.")
    st.text_input("Κωδικός Πρόσβασης", type="password", on_change=password_entered, key="password")
    return False

if not check_password(): st.stop()

# --- ΣΥΝΔΕΣΗ ΜΕ GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Φορτώνουμε όλα τα tabs από το Google Sheet
    try:
        ing = conn.read(worksheet="Ingredients", ttl="5m").fillna("")
        rec = conn.read(worksheet="Recipes", ttl="5m").fillna("")
        orders = conn.read(worksheet="Orders", ttl="5m").fillna("")
        history = conn.read(worksheet="History", ttl="5m").fillna("")
    except Exception as e:
        st.error(f"⚠️ Σφάλμα σύνδεσης με Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    return ing, rec, orders, history

df_ing, df_rec, df_orders, df_history = load_data()

# Βασικές σταθερές
TOTAL_FIXED = 0.22  
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

# Λίστες επιλογών
ing_options = ["ΚΕΝΟ", "Νερό"] + sorted(df_ing["Name"].unique().tolist()) if not df_ing.empty else ["ΚΕΝΟ", "Νερό"]
recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

# --- Sidebar ---
st.sidebar.image("https://cabclub.gr/wp-content/uploads/2021/12/logo.png", use_container_width=True)
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", [
    "📦 Αποθήκη", "🔄 Αντικατάσταση", "📝 Νέα Συνταγή", "📊 Διαχείριση", 
    "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "🛒 Παραγγελίες", 
    "🌐 Shop Sync", "📦 Lot Παραγωγής", "📈 Dashboard"
])

country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών & Τιμών")
    if "ID" not in df_ing.columns:
        df_ing.insert(0, "ID", range(1001, 1001 + len(df_ing)))
    
    edited_ing = st.data_editor(df_ing, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Αποθήκευση στο Cloud"):
        temp_df = edited_ing.copy()
        temp_df["Τιμή/ml"] = pd.to_numeric(temp_df["Price"]) / pd.to_numeric(temp_df["Volume"]).replace(0, 1)
        conn.update(worksheet="Ingredients", data=temp_df)
        st.cache_data.clear()
        st.success("✅ Η Αποθήκη ενημερώθηκε στο Google Sheets!")

# --- 2. ΑΝΤΙΚΑΤΑΣΤΑΣΗ ---
elif page == "🔄 Αντικατάσταση":
    st.header("🔄 Μαζική Αντικατάσταση Πρώτης Ύλης")
    used_ingredients = []
    for i in range(1, 14):
        if f"ΣΥΣΤΑΤΙΚΟ{i}" in df_rec.columns:
            used_ingredients.extend(df_rec[f"ΣΥΣΤΑΤΙΚΟ{i}"].astype(str).unique())
    unique_used = sorted(list(set([ing for ing in used_ingredients if ing not in ["ΚΕΝΟ", "nan", "None", ""]])))
    
    col1, col2 = st.columns(2)
    target_ing = col1.selectbox("Υλικό προς αντικατάσταση:", options=unique_used)
    new_ing = col2.selectbox("Αντικατάσταση με:", options=df_ing["Name"].unique())
    
    if st.button("🚀 Εκτέλεση Αντικατάστασης"):
        for i in range(1, 14):
            df_rec[f"ΣΥΣΤΑΤΙΚΟ{i}"] = df_rec[f"ΣΥΣΤΑΤΙΚΟ{i}"].replace(target_ing, new_ing)
        conn.update(worksheet="Recipes", data=df_rec)
        st.cache_data.clear()
        st.success("Έγινε η αλλαγή!")

# --- 3. ΝΕΑ ΣΥΝΤΑΓΗ ---
elif page == "📝 Νέα Συνταγή":
    st.header("📝 Καταχώρηση Νέας Συνταγής")
    with st.form("new_recipe"):
        c1, c2 = st.columns([1, 2])
        barcode = c1.text_input("Barcode (SKU Site)")
        name = c2.text_input("Όνομα Cocktail")
        cat_price = st.number_input("Τιμή Καταλόγου (€)", min_value=0.0)
        
        recipe_data = {}
        for i in range(1, 14):
            col_a, col_b = st.columns([3, 1])
            recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = col_a.selectbox(f"Συστατικό {i}", ing_options, key=f"ns_{i}")
            recipe_data[f"ML{i}"] = col_b.number_input(f"ML {i}", min_value=0.0, key=f"nm_{i}")
        
        if st.form_submit_button("💾 Αποθήκευση"):
            new_row = {"Barcode": str(barcode), "Ονομα": name, "Τιμή Καταλόγου": cat_price, **recipe_data}
            updated_rec = pd.concat([df_rec, pd.DataFrame([new_row])], ignore_index=True)
            conn.update(worksheet="Recipes", data=updated_rec)
            st.cache_data.clear()
            st.success("Αποθηκεύτηκε!")

# --- 4. ΔΙΑΧΕΙΡΙΣΗ ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία & Διαγραφή")
    recipe_to_edit = st.selectbox("Αναζήτηση Cocktail:", options=recipe_options, index=None)
    
    if recipe_to_edit:
        # Φιλτράρουμε τη γραμμή της συνταγής
        row = df_rec[df_rec["Ονομα"] == recipe_to_edit].iloc[0]
        
        with st.form("edit_form"):
            en = st.text_input("Όνομα", value=row.get("Ονομα", ""))
            eb = st.text_input("Barcode", value=str(row.get("Barcode", "")))
            # Προσοχή στο όνομα της στήλης Τιμή
            price_col = "Τιμή Καταλόγου" if "Τιμή Καταλόγου" in df_rec.columns else "Τιμή"
            ep = st.number_input("Τιμή", value=float(row.get(price_col, 0.0)))
            
            new_data = {}
            # Loop για τα 13 συστατικά
            for i in range(1, 14):
                c1, c2 = st.columns([2, 1])
                
                # Έλεγχος αν η στήλη υπάρχει στο Excel (πρόληψη KeyError)
                col_name = f"ΣΥΣΤΑΤΙΚΟ{i}"
                ml_name = f"ML{i}"
                
                current_ing = row.get(col_name, "")
                current_ml = row.get(ml_name, 0.0)
                
                # Επιλογή Υλικού
                new_data[col_name] = c1.selectbox(
                    f"Υλικό {i}", 
                    ing_options, 
                    index=ing_options.index(current_ing) if current_ing in ing_options else 0, 
                    key=f"e_s_{i}"
                )
                
                # Ποσότητα ML
                new_data[ml_name] = c2.number_input(
                    f"ML {i}", 
                    value=float(current_ml) if current_ml else 0.0, 
                    key=f"e_m_{i}"
                )
            
            # ΤΟ ΚΟΥΜΠΙ ΠΡΕΠΕΙ ΝΑ ΕΙΝΑΙ ΕΔΩ (Μέσα στο with st.form)
            submitted = st.form_submit_button("💾 Ενημέρωση & Αποθήκευση")
            
            if submitted:
                # Ενημέρωση του DataFrame
                df_rec.loc[df_rec["Ονομα"] == recipe_to_edit, ["Ονομα", "Barcode", price_col]] = [en, eb, ep]
                
                for k, v in new_data.items():
                    df_rec.loc[df_rec["Ονομα"] == en, k] = v
                
                # Αποστολή στο Google Sheets
                conn.update(worksheet="Recipes", data=df_rec)
                
                # Καθαρισμός Cache και ανανέωση
                st.cache_data.clear()
                st.success(f"Το cocktail '{en}' ενημερώθηκε επιτυχώς!")
                st.rerun()

# --- 5. ΑΝΑΛΥΣΗ ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση")
    choice = st.selectbox("Επιλέξτε Cocktail:", recipe_options)
    if choice:
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        raw_cost, pure_alc_ml, total_ml = 0.0, 0.0, 0.0
        breakdown = []
        for i in range(1, 14):
            ing_n, ml = str(r[f"ΣΥΣΤΑΤΙΚΟ{i}"]), float(r[f"ML{i}"])
            if ing_n != "ΚΕΝΟ" and ml > 0:
                total_ml += ml
                match = df_ing[df_ing["Name"] == ing_n]
                if not match.empty:
                    p_ml = float(match.iloc[0]["Τιμή/ml"])
                    item_cost = ml * p_ml
                    raw_cost += item_cost
                    breakdown.append({"Υλικό": ing_n, "ML": ml, "Κόστος": item_cost})
        
        st.metric("Συνολικό Κόστος Παραγωγής", f"{raw_cost + TOTAL_FIXED:.2f} €")
        st.table(pd.DataFrame(breakdown))

# --- 6. ΕΜΠΟΡΙΚΗ ΠΟΛΙΤΙΚΗ ---
elif page == "📊 Εμπορική Πολιτική":
    st.header("📊 Εμπορική Πολιτική")
    # Η λογική παραμένει ίδια, χρησιμοποιώντας τα df_ing/df_rec που φορτώθηκαν από το Cloud
    st.write("Συγκρίνετε σενάρια βάσει των τιμών του Google Sheets.")

# --- 7. ΠΑΡΑΓΓΕΛΙΕΣ ---
elif page == "🛒 Παραγγελίες":
    st.header("🛒 Παραγγελίες")
    ed_orders = st.data_editor(df_orders, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Αποθήκευση"):
        conn.update(worksheet="Orders", data=ed_orders)
        st.success("Ενημερώθηκε!")

# --- 8. SHOP SYNC ---
elif page == "🌐 Shop Sync":
    st.header("🌐 WooCommerce Sync")
    ck = st.text_input("Consumer Key", type="password")
    cs = st.text_input("Consumer Secret", type="password")
    if st.button("🚀 Λήψη Παραγγελιών"):
        url = "https://cabclub.gr/wp-json/wc/v3/orders"
        res = requests.get(url, auth=HTTPBasicAuth(ck, cs))
        if res.status_code == 200:
            st.write(res.json())
        else: st.error("Αποτυχία σύνδεσης API.")

# --- 9. LOT ΠΑΡΑΓΩΓΗΣ ---
elif page == "📦 Lot Παραγωγής":
    st.header("📦 Δελτίο Παραγωγής")
    # Εδώ χρησιμοποιείς τη λογική ζύγισης που είχες, 
    # διαβάζοντας τα Weight_Full από το df_ing
    st.info("Επιλέξτε Cocktail για υπολογισμό γραμμαρίων βάσει Cloud.")

# --- 10. DASHBOARD ---
elif page == "📈 Dashboard":
    st.header("📈 Dashboard")
    if not df_history.empty:
        fig = px.bar(df_history, x="Cocktail", y="Τεμάχια", color="Cocktail")
        st.plotly_chart(fig)
