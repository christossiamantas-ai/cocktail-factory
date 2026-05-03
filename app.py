import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

# --- Σύστημα Password ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    def password_entered():
        if st.session_state["password"] == "panatha1908":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.error("❌ Λάθος κωδικός.")
    st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
    return False

if not check_password():
    st.stop()

# --- ΣΥΝΔΕΣΗ ΜΕ GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Φόρτωση Υλικών
    try:
        ing = conn.read(worksheet="Ingredients", ttl=0).fillna("")
    except:
        ing = pd.DataFrame(columns=["ID", "Name", "Price", "Volume", "Weight_Full", "Τιμή/ml", "Αλκοόλ %"])
    
    # Φόρτωση Συνταγών
    try:
        rec = conn.read(worksheet="Recipes", ttl=0).fillna("")
    except:
        cols_rec = ["Barcode", "Ονομα", "Τιμή Καταλόγου"] + [f"ΣΥΣΤΑΤΙΚΟ{i}" for i in range(1,14)] + [f"ML{i}" for i in range(1,14)]
        rec = pd.DataFrame(columns=cols_rec)
        
    # Φόρτωση Παραγγελιών & Ιστορικού (Από Sheets)
    try:
        orders = conn.read(worksheet="Orders", ttl=0).fillna("")
    except:
        orders = pd.DataFrame(columns=["Πελάτης", "Cocktail", "Τεμάχια"])

    try:
        history = conn.read(worksheet="History", ttl=0).fillna("")
    except:
        history = pd.DataFrame(columns=["Ημερομηνία", "Πελάτης", "Cocktail", "Τεμάχια"])
        
    return ing, rec, orders, history

# Αρχικοποίηση Δεδομένων
df_ing, df_rec, df_orders, df_history = load_data()
ing_options = ["ΚΕΝΟ", "Νερό"] + sorted(df_ing["Name"].unique().tolist()) if not df_ing.empty else ["ΚΕΝΟ", "Νερό"]
recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

# --- CSS Στυλ ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc; }
    div[data-testid="stMetric"] { background-color: #1e2129; border: 1px solid #333; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #3e4451; color: white; }
    .stButton>button:hover { border: 1px solid #00ffcc; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}
TOTAL_FIXED = 0.22

# --- Sidebar ---
st.sidebar.image("https://cabclub.gr/wp-content/uploads/2021/12/logo.png", use_container_width=True)
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "📝 Νέα Συνταγή", "📊 Διαχείριση", "🔍 Ανάλυση", "🛒 Παραγγελίες", "📊 Εμπορική Πολιτική"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών στο Cloud")
    if "ID" not in df_ing.columns:
        df_ing.insert(0, "ID", range(1001, 1001 + len(df_ing)))
    
    edited_ing = st.data_editor(df_ing[["ID", "Name", "Price", "Volume", "Weight_Full", "Τιμή/ml", "Αλκοόλ %"]], num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Αποθήκευση στο Cloud"):
        temp_df = edited_ing.copy()
        if temp_df["ID"].isnull().any():
            max_id = df_ing["ID"].max() if not df_ing.empty else 1000
            temp_df.loc[temp_df["ID"].isnull(), "ID"] = range(int(max_id)+1, int(max_id)+1 + temp_df["ID"].isnull().sum())
        
        temp_df["Τιμή/ml"] = temp_df["Price"] / temp_df["Volume"].replace(0, 1)
        conn.update(worksheet="Ingredients", data=temp_df)
        st.cache_data.clear()
        st.success("✅ Η Αποθήκη ενημερώθηκε στο Cloud!")
        st.rerun()

# --- 2. ΝΕΑ ΣΥΝΤΑΓΗ ---
elif page == "📝 Νέα Συνταγή":
    st.header("📝 Καταχώρηση Νέας Συνταγής")
    with st.form("new_recipe_form"):
        c1, c2 = st.columns([1, 2])
        barcode = c1.text_input("Barcode (SKU)")
        name = c2.text_input("Όνομα Cocktail")
        cat_price = st.number_input("Τιμή Καταλόγου (€)", min_value=0.0, step=0.10)
        
        recipe_data = {}
        for i in range(1, 14):
            col1, col2 = st.columns([3, 1])
            recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = col1.selectbox(f"Υλικό {i}", ing_options, key=f"ns_{i}")
            recipe_data[f"ML{i}"] = col2.number_input(f"ML {i}", min_value=0.0, key=f"nm_{i}")
            
        if st.form_submit_button("💾 Αποθήκευση Συνταγής στο Cloud"):
            if name:
                new_row = {"Barcode": str(barcode), "Ονομα": name, "Τιμή Καταλόγου": cat_price, **recipe_data}
                updated_rec = pd.concat([df_rec, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(worksheet="Recipes", data=updated_rec)
                st.cache_data.clear()
                st.success(f"✅ Η συνταγή {name} αποθηκεύτηκε!")
                st.rerun()

# --- 3. ΔΙΑΧΕΙΡΙΣΗ ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία & Διαγραφή")
    if not df_rec.empty:
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique(), index=None)
        if choice:
            row = df_rec[df_rec["Ονομα"] == choice].iloc[0]
            tab1, tab2 = st.tabs(["📝 Επεξεργασία", "🗑️ Διαγραφή"])
            
            with tab1:
                with st.form(f"edit_{choice}"):
                    en = st.text_input("Όνομα", value=row["Ονομα"])
                    eb = st.text_input("Barcode", value=str(row.get("Barcode", "")))
                    ep = st.number_input("Τιμή", value=float(row.get("Τιμή Καταλόγου", 0.0)))
                    
                    new_recipe_data = {}
                    for i in range(1, 14):
                        c1, c2 = st.columns([3, 1])
                        curr_ing = str(row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        idx = ing_options.index(curr_ing) if curr_ing in ing_options else 0
                        new_recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = c1.selectbox(f"Υλικό {i}", ing_options, index=idx, key=f"ei_{i}")
                        new_recipe_data[f"ML{i}"] = c2.number_input(f"ML {i}", value=float(row.get(f"ML{i}", 0.0)), key=f"em_{i}")
                    
                    if st.form_submit_button("💾 Αποθήκευση Αλλαγών στο Cloud"):
                        df_rec.loc[df_rec["Ονομα"] == choice, ["Ονομα", "Barcode", "Τιμή Καταλόγου"]] = [en, eb, ep]
                        for k, v in new_recipe_data.items():
                            df_rec.loc[df_rec["Ονομα"] == en, k] = v
                        conn.update(worksheet="Recipes", data=df_rec)
                        st.cache_data.clear()
                        st.success("✅ Ενημερώθηκε!")
                        st.rerun()
            
            with tab2:
                if st.button("🗑️ Οριστική Διαγραφή"):
                    df_rec = df_rec[df_rec["Ονομα"] != choice]
                    conn.update(worksheet="Recipes", data=df_rec)
                    st.cache_data.clear()
                    st.error("❌ Διαγράφηκε!")
                    st.rerun()

# --- 4. ΑΝΑΛΥΣΗ (ΔΙΟΡΘΩΜΕΝΗ ΓΙΑ ΣΥΜΒΑΤΟΤΗΤΑ ΜΕ ID & ΟΝΟΜΑΤΑ) ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση & Κερδοφορία")
    
    if not df_rec.empty:
        # Sidebar Ρυθμίσεις
        st.sidebar.subheader("Ρυθμίσεις Ανάλυσης")
        discount = st.sidebar.slider("Έκπτωση Προσφοράς %", 0, 100, 0)
        
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        # Βασικές Τιμές
        p_retail = float(r.get("Τιμή Καταλόγου", 0))
        p_agent = p_retail * 0.74
        p_custom = p_retail * (1 - discount/100)
        
        raw_cost, pure_alc_ml, total_ml_cocktail = 0.0, 0.0, 0.0
        breakdown = []
        missing_ingredients = [] # Λίστα για υλικά που δεν βρέθηκαν
        
        # --- ΣΥΛΛΟΓΗ ΔΕΔΟΜΕΝΩΝ ΣΥΝΤΑΓΗΣ ---
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
            ml = float(r.get(f"ML{i}", 0))
            
            if ing_n != "ΚΕΝΟ" and ml > 0:
                total_ml_cocktail += ml
                if ing_n == "Νερό":
                    breakdown.append({"Υλικό": "Νερό", "ML": ml, "Κόστος": 0.0, "Alc %": 0.0})
                elif ing_n not in ["nan", ""]:
                    # ΕΔΩ Η ΔΙΟΡΘΩΣΗ: Αναζήτηση στην Αποθήκη
                    match = df_ing[df_ing["Name"] == ing_n]
                    
                    if not match.empty:
                        # Αν το βρει, παίρνει τα δεδομένα
                        ing_row = match.iloc[0]
                        alc_val = float(ing_row.get("Αλκοόλ %", 0))
                        actual_alc_pct = alc_val if alc_val <= 1 else alc_val / 100
                        pure_alc_ml += (ml * actual_alc_pct)
                        
                        # Χρήση της σωστής στήλης "Τιμή/ml"
                        price_ml = float(ing_row.get("Τιμή/ml", 0))
                        item_cost = ml * price_ml
                        raw_cost += item_cost
                        
                        breakdown.append({
                            "Υλικό": ing_n, 
                            "ML": ml, 
                            "Κόστος": item_cost, 
                            "Alc %": actual_alc_pct * 100
                        })
                    else:
                        # Αν δεν το βρει, το καταγράφει για να σε ενημερώσει
                        missing_ingredients.append(ing_n)
                        breakdown.append({
                            "Υλικό": f"⚠️ {ing_n} (Μη διαθέσιμο)", 
                            "ML": ml, 
                            "Κόστος": 0.0, 
                            "Alc %": 0.0
                        })

        # Εμφάνιση προειδοποίησης αν λείπουν υλικά
        if missing_ingredients:
            st.error(f"⚠️ Τα παρακάτω υλικά της συνταγής δεν βρέθηκαν στην Αποθήκη: {', '.join(missing_ingredients)}. Παρακαλώ ελέγξτε αν αλλάξατε το όνομά τους στη Διαχείριση.")

        # --- ΥΠΟΛΟΓΙΣΜΟΙ ---
        final_abv = (pure_alc_ml / total_ml_cocktail * 100) if total_ml_cocktail > 0 else 0
        efk_informational = pure_alc_ml * tax_factor
        total_production = raw_cost + TOTAL_FIXED 
        
        profit_retail = p_retail - total_production
        profit_agent = p_agent - total_production
        profit_custom = p_custom - total_production
        margin_retail = (profit_retail / p_retail * 100) if p_retail > 0 else 0

        # --- ΕΜΦΑΝΙΣΗ ΣΤΗΝ ΟΘΟΝΗ ---
        st.subheader(f"Στατιστικά για: {choice}")
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Συνολική Ποσότητα", f"{total_ml_cocktail:.1f} ml".replace('.', ','))
        m_col2.metric("Αλκοολικός Βαθμός (ABV)", f"{final_abv:.2f} %".replace('.', ','))
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Τιμή Λιανικής", f"{p_retail:.2f} €".replace('.', ','))
        c2.metric("Τιμή Αντιπροσώπου", f"{p_agent:.2f} €".replace('.', ','))
        c3.metric("Τιμή με Έκπτωση", f"{p_custom:.2f} €".replace('.', ','), delta=f"-{discount}%")

        st.markdown("---")
        st.write("### 💰 Ανάλυση Πραγματικής Κερδοφορίας")
        p_c1, p_c2, p_c3 = st.columns(3)
        p_c1.metric("Κέρδος Λιανικής", f"{profit_retail:.2f} €".replace('.', ','))
        p_c2.metric("Κέρδος Αντιπροσώπου", f"{profit_agent:.2f} €".replace('.', ','))
        p_c3.metric("Κέρδος με Έκπτωση", f"{profit_custom:.2f} €".replace('.', ','))

        st.markdown("---")
        st.write("### 🛠️ Ανάλυση Κόστους & Φόρων")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Κόστος Υλικών", f"{raw_cost:.2f} €".replace('.', ','))
        k2.metric("ΕΦΚ (Ενσωμ.)", f"{efk_informational:.2f} €".replace('.', ','))
        k3.metric("Σταθερά Έξοδα", f"{TOTAL_FIXED:.2f} €".replace('.', ','))
        k4.metric("ΣΥΝΟΛΟ ΚΟΣΤΟΥΣ", f"{total_production:.2f} €".replace('.', ','))

        # --- ΠΙΝΑΚΑΣ ΥΛΙΚΩΝ ΣΤΗΝ ΟΘΟΝΗ ---
        st.markdown("---")
        st.write("### 🍹 Σύνθεση Υλικών")
        df_screen = pd.DataFrame(breakdown)
        if not df_screen.empty:
            df_render = df_screen.copy()
            for col in ["ML", "Alc %", "Κόστος"]:
                if col in df_render.columns:
                    df_render[col] = df_render[col].apply(lambda x: f"{x:.2f}".replace('.', ','))
            st.table(df_render[["Υλικό", "ML", "Alc %", "Κόστος"]])

        # --- ΕΝΟΤΗΤΑ ΕΞΑΓΩΓΗΣ REPORT ---
        st.markdown("### 📜 Εξαγωγή Επαγγελματικού Report")
        
        def clean_val(val, decimals=3):
            try:
                return f"{float(val):.{decimals}f}".replace('.', ',')
            except:
                return str(val).replace('.', ',')

        try:
            current_barcode = df_rec[df_rec['Ονομα'] == choice]['Barcode'].values[0]
            if not current_barcode or str(current_barcode).lower() == 'nan':
                current_barcode = "Δεν ορίστηκε"
        except:
            current_barcode = "Δεν βρέθηκε"

        report_data = [
            ["ΗΜΕΡΟΜΗΝΙΑ REPORT", datetime.now().strftime("%d/%m/%Y %H:%M")],
            ["COCKTAIL", choice],
            ["BARCODE (SKU)", current_barcode],
            ["ΣΥΝΟΛΙΚΗ ΠΟΣΟΤΗΤΑ (ML)", clean_val(total_ml_cocktail, 1)],
            ["ΑΛΚΟΟΛΙΚΟΣ ΒΑΘΜΟΣ (ABV) %", clean_val(final_abv, 2)],
            ["---------------------------", "---------------------------"],
            ["ΟΙΚΟΝΟΜΙΚΗ ΑΝΑΛΥΣΗ", ""],
            ["Κόστος Υλικών (με ΕΦΚ)", f"{clean_val(raw_cost)} €"],
            ["ΕΦΚ (Ενημερωτικά)", f"{clean_val(efk_informational)} €"],
            ["Σταθερά Έξοδα Μονάδας", f"{clean_val(TOTAL_FIXED)} €"],
            ["ΣΥΝΟΛΙΚΟ ΚΟΣΤΟΣ ΠΑΡΑΓΩΓΗΣ", f"{clean_val(total_production)} €"],
            ["---------------------------", "---------------------------"],
            ["ΤΙΜΕΣ & ΚΕΡΔΗ", ""],
            ["Τιμή Λιανικής", f"{clean_val(p_retail, 2)} €"],
            ["Κέρδος Λιανικής", f"{clean_val(profit_retail)} €"],
            ["Margin Λιανικής %", f"{clean_val(margin_retail, 2)} %"],
            ["---------------------------", "---------------------------"]
        ]
        
        for item in breakdown:
            val_alc = item.get('Alc %', 0.0)
            report_data.append([
                f"Υλικό: {item['Υλικό']}", 
                f"{clean_val(item['ML'], 1)} ml | {clean_val(val_alc, 1)}% Alc | {clean_val(item['Κόστος'])} €"
            ])

        df_export = pd.DataFrame(report_data, columns=["ΠΕΡΙΓΡΑΦΗ", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ"])
        csv_final = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig')
        
        st.download_button(
            label=f"📥 Λήψη Πλήρους Report: {choice}", 
            data=csv_final, 
            file_name=f"Report_{choice.replace(' ', '_')}.csv",
            mime="text/csv",
            key="download_report_btn"
        )
# --- 5. ΠΑΡΑΓΓΕΛΙΕΣ ---
elif page == "🛒 Παραγγελίες":
    st.header("🛒 Παραγγελίες & Ανάγκες")
    col_a, col_b = st.columns([1, 1.3])
    with col_a:
        order_config = {
            "Πελάτης": st.column_config.TextColumn("Πελάτης"),
            "Cocktail": st.column_config.SelectboxColumn("Cocktail", options=recipe_options),
            "Τεμάχια": st.column_config.NumberColumn("Τεμάχια", min_value=1)
        }
        ed_orders = st.data_editor(df_orders, column_config=order_config, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Αποθήκευση Παραγγελιών"):
            ed_orders.to_csv(DB_ORDERS, index=False)
            st.rerun()

        if st.button("✅ ΟΛΟΚΛΗΡΩΣΗ & ΑΡΧΕΙΟΘΕΤΗΣΗ"):
            if not ed_orders.empty:
                new_h = ed_orders.copy()
                new_h["Ημερομηνία"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                df_history = pd.concat([df_history, new_h], ignore_index=True)
                df_history.to_csv(DB_HISTORY, index=False)
                pd.DataFrame(columns=["Πελάτης", "Cocktail", "Τεμάχια"]).to_csv(DB_ORDERS, index=False)
                st.success("Η παραγγελία μεταφέρθηκε στο ιστορικό!")
                st.rerun()

    with col_b:
        st.subheader("Υπολογισμός με Κενό Απόθεμα")
        if not ed_orders.empty:
            needs = {}
            for _, o in ed_orders.iterrows():
                r_m = df_rec[df_rec["Ονομα"] == o["Cocktail"]]
                if not r_m.empty:
                    for i in range(1,14):
                        ing, ml = str(r_m.iloc[0][f"ΣΥΣΤΑΤΙΚΟ{i}"]), float(r_m.iloc[0][f"ML{i}"])
                        if ing not in ["ΚΕΝΟ", "nan", "Νερό", ""]:
                            needs[ing] = needs.get(ing, 0) + (ml * o["Τεμάχια"])
            
            if needs:
                calc_data = []
                for ing, total_ml in needs.items():
                    ing_info = df_ing[df_ing["Name"] == ing]
                    vol = float(ing_info.iloc[0]["Volume"]) if not ing_info.empty else 700
                    calc_data.append({"Υλικό": ing, "Ανάγκη (ml)": total_ml, "Απόθεμα στο Ράφι (ml)": 0.0, "_vol": vol})
                
                df_c = pd.DataFrame(calc_data)
                ed_c = st.data_editor(df_c, column_config={"Ανάγκη (ml)": st.column_config.NumberColumn(disabled=True), "Απόθεμα στο Ράφι (ml)": st.column_config.NumberColumn(min_value=0.0), "_vol": None}, use_container_width=True)
                
                ed_c["Προς Αγορά (Φιάλες)"] = ed_c.apply(lambda x: math.ceil(max(0, x["Ανάγκη (ml)"] - x["Απόθεμα στο Ράφι (ml)"]) / x["_vol"]) if x["_vol"] > 0 else 0, axis=1)
                st.subheader("📋 Λίστα Αγορών")
                st.dataframe(ed_c[ed_c["Προς Αγορά (Φιάλες)"] > 0][["Υλικό", "Προς Αγορά (Φιάλες)"]], use_container_width=True)

# --- 6. ΕΜΠΟΡΙΚΗ ΠΟΛΙΤΙΚΗ (COMPLETE PRO VERSION WITH GLOSSARY) ---
elif page == "📊 Εμπορική Πολιτική":
    st.header("📊 Εμπορική Πολιτική & Σύγκριση Σεναρίων")
    st.write("Συγκρίνετε τη στρατηγική Δώρων έναντι της Έκπτωσης % και δείτε την ανάλυση κερδοφορίας.")

    if not df_rec.empty:
        # 1. Επιλογή Cocktail & Υπολογισμός Κόστους
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]

        raw_cost = 0.0
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
            ml = float(r.get(f"ML{i}", 0))
            if ing_n not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml > 0:
                match = df_ing[df_ing["Name"] == ing_n]
                if not match.empty:
                    raw_cost += ml * float(match.iloc[0]["Τιμή/ml"])
        
        unit_cost = raw_cost + TOTAL_FIXED
        p_retail = float(r["Τιμή Καταλόγου"])
        p_agent_base = p_retail * 0.74  # Κανονική τιμή προ προσφορών
        normal_profit_per_unit = p_agent_base - unit_cost

        st.divider()

        # 2. Είσοδος Δεδομένων (Ξεκινάνε από 0)
        col_in_a, col_in_b = st.columns(2)

        with col_in_a:
            st.subheader("Σενάριο Α: Δώρα (Free Goods)")
            sA_paid = st.number_input("Τεμάχια προς Πώληση (Paid)", min_value=0, value=0, key="sa_paid")
            sA_free = st.number_input("Τεμάχια Δώρο (Free)", min_value=0, value=0, key="sa_free")
            
            sA_total_units = sA_paid + sA_free
            sA_revenue = sA_paid * p_agent_base
            sA_cost = sA_total_units * unit_cost
            sA_profit = sA_revenue - sA_cost
            sA_effective = sA_revenue / sA_total_units if sA_total_units > 0 else 0
            sA_margin = (sA_profit / sA_revenue * 100) if sA_revenue > 0 else 0
            sA_markup = (sA_profit / sA_cost * 100) if sA_cost > 0 else 0
            sA_loss = (normal_profit_per_unit * sA_total_units) - sA_profit if sA_total_units > 0 else 0

        with col_in_b:
            st.subheader("Σενάριο Β: Έκπτωση επί της Τιμής")
            sB_total_units = st.number_input("Συνολικά Τεμάχια (Β)", min_value=0, value=0, key="sb_total")
            sB_discount = st.number_input("Ποσοστό Έκπτωσης %", min_value=0.0, value=0.0, key="sb_disc")
            
            sB_price_per_unit = p_agent_base * (1 - sB_discount/100)
            sB_revenue = sB_total_units * sB_price_per_unit
            sB_cost = sB_total_units * unit_cost
            sB_profit = sB_revenue - sB_cost
            sB_effective = sB_price_per_unit
            sB_margin = (sB_profit / sB_revenue * 100) if sB_revenue > 0 else 0
            sB_markup = (sB_profit / sB_cost * 100) if sB_cost > 0 else 0
            sB_loss = (normal_profit_per_unit * sB_total_units) - sB_profit if sB_total_units > 0 else 0

        # 3. Εμφάνιση Επαγγελματικού Πίνακα
        if sA_total_units > 0 or sB_total_units > 0:
            st.divider()
            
            winner_text = "ΣΕΝΑΡΙΟ Α" if sA_profit > sB_profit else "ΣΕΝΑΡΙΟ Β"
            diff_val = abs(sA_profit - sB_profit)

            # Σχεδιασμός Πίνακα (HTML format)
            html_table = """
            <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #444;">
                <table style="width: 100%; border-collapse: collapse; color: white; font-family: sans-serif;">
                    <tr style="background-color: #1a3a5f;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #444;">ΠΕΡΙΓΡΑΦΗ ΑΝΑΛΥΣΗΣ</th>
                        <th style="padding: 12px; text-align: center; border: 1px solid #444;">ΣΕΝΑΡΙΟ Α</th>
                        <th style="padding: 12px; text-align: center; border: 1px solid #444;">ΣΕΝΑΡΙΟ Β</th>
                    </tr>
                    <tr style="background-color: #333; font-weight: bold;">
                        <td colspan="3" style="padding: 10px; border: 1px solid #444;">ΟΙΚΟΝΟΜΙΚΑ ΜΕΓΕΘΗ</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Κανονική Τιμή Αντιπρ.</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{0:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{0:.2f} €</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Effective Τιμή/Τμχ</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{1:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{2:.2f} €</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Συνολικά Έσοδα</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{3:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{4:.2f} €</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Συνολικό Κόστος</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{5:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{6:.2f} €</td>
                    </tr>
                    <tr style="font-weight: bold; background-color: #222;">
                        <td style="padding: 10px; border: 1px solid #444;">ΚΑΘΑΡΟ ΚΕΡΔΟΣ</td>
                        <td style="text-align:center; color: #4caf50; font-size: 1.2em; border: 1px solid #444;">{7:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; font-size: 1.2em; border: 1px solid #444;">{8:.2f} €</td>
                    </tr>
                    <tr style="background-color: #333; font-weight: bold;">
                        <td colspan="3" style="padding: 10px; border: 1px solid #444;">ΔΕΙΚΤΕΣ</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Margin %</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{9:.1f}%</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{10:.1f}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Markup %</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{11:.1f}%</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{12:.1f}%</td>
                    </tr>
                </table>
                <div style="margin-top: 20px; padding: 15px; background-color: #1b5e20; border-radius: 8px; text-align: center; color: white;">
                    <h2 style="margin:0;">🏆 ΝΙΚΗΤΗΣ: {13}</h2>
                    <p style="margin:5px 0 0 0;">Επιπλέον κέρδος: <b>{14:.2f} €</b></p>
                </div>
            </div>
            """.format(
                p_agent_base, sA_effective, sB_effective, 
                sA_revenue, sB_revenue, sA_cost, sB_cost, 
                sA_profit, sB_profit, sA_margin, sB_margin, 
                sA_markup, sB_markup, winner_text, diff_val
            )
            
            st.markdown(html_table, unsafe_allow_html=True)

            # --- ΝΕΟ: ΕΠΕΞΗΓΗΣΗ ΟΙΚΟΝΟΜΙΚΩΝ ΟΡΩΝ ---
            with st.expander("ℹ️ Ερμηνεία Οικονομικών Όρων & Δεικτών"):
                st.info("""
                * **Effective Τιμή:** Η πραγματική τιμή που εισπράττει η εταιρεία ανά μονάδα προϊόντος, αφού υπολογιστούν τα δώρα ή οι εκπτώσεις.
                * **Margin (Περιθώριο Κέρδους %):** Το ποσοστό του τζίρου που παραμένει ως κέρδος. Υπολογίζεται ως: `(Κέρδος / Έσοδα) * 100`.
                * **Markup (Ποσοστό Επιβάρυνσης %):** Το ποσοστό πάνω στο κόστος παραγωγής που προστίθεται για να προκύψει η τιμή πώλησης. Υπολογίζεται ως: `(Κέρδος / Κόστος) * 100`.
                * **Κόστος Εμπορικής Ενέργειας:** Το "διαφυγόν κέρδος". Πόσα χρήματα επενδύει η εταιρεία στην προσφορά σε σχέση με την κανονική τιμή πώλησης.
                """)
            
            st.divider()
            
            # 5. ΥΠΕΡ-ΑΝΑΛΥΤΙΚΟ ΕΠΑΓΓΕΛΜΑΤΙΚΟ REPORT
            if st.button("💾 Λήψη Πλήρους Φακέλου Ανάλυσης (Full Audit Report)"):
                now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                # Υπολογισμός Έμμεσης Έκπτωσης για το Σενάριο Α
                sA_indirect_disc = ((1 - sA_effective/p_agent_base)*100) if p_agent_base > 0 else 0
                
                full_audit_data = [
                    {"ΚΑΤΗΓΟΡΙΑ": "1. ΤΑΥΤΟΤΗΤΑ ΣΥΜΦΩΝΙΑΣ", "ΣΤΟΙΧΕΙΟ": "Cocktail / Προϊόν", "ΣΕΝΑΡΙΟ Α": choice, "ΣΕΝΑΡΙΟ Β": choice},
                    {"ΚΑΤΗΓΟΡΙΑ": "1. ΤΑΥΤΟΤΗΤΑ ΣΥΜΦΩΝΙΑΣ", "ΣΤΟΙΧΕΙΟ": "Ημερομηνία & Ώρα", "ΣΕΝΑΡΙΟ Α": now_str, "ΣΕΝΑΡΙΟ Β": ""},
                    {"ΚΑΤΗΓΟΡΙΑ": "1. ΤΑΥΤΟΤΗΤΑ ΣΥΜΦΩΝΙΑΣ", "ΣΤΟΙΧΕΙΟ": "Υπεύθυνος Ανάλυσης", "ΣΕΝΑΡΙΟ Α": "DC CABCLUB System", "ΣΕΝΑΡΙΟ Β": ""},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},
                    
                    {"ΚΑΤΗΓΟΡΙΑ": "2. ΤΙΜΟΛΟΓΙΑΚΗ ΒΑΣΗ", "ΣΤΟΙΧΕΙΟ": "Τιμή Καταλόγου (Retail)", "ΣΕΝΑΡΙΟ Α": f"{p_retail:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{p_retail:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "2. ΤΙΜΟΛΟΓΙΑΚΗ ΒΑΣΗ", "ΣΤΟΙΧΕΙΟ": "Βασική Τιμή Αντιπροσώπου (Gross)", "ΣΕΝΑΡΙΟ Α": f"{p_agent_base:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{p_agent_base:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "2. ΤΙΜΟΛΟΓΙΑΚΗ ΒΑΣΗ", "ΣΤΟΙΧΕΙΟ": "Πραγματική Τιμή Μονάδας (Net)", "ΣΕΝΑΡΙΟ Α": f"{sA_effective:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_effective:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},

                    {"ΚΑΤΗΓΟΡΙΑ": "3. ΑΝΑΛΥΣΗ ΟΓΚΩΝ (UNITS)", "ΣΤΟΙΧΕΙΟ": "Τεμάχια προς Τιμολόγηση", "ΣΕΝΑΡΙΟ Α": f"{sA_paid} τμχ", "ΣΕΝΑΡΙΟ Β": f"{sB_total_units} τμχ"},
                    {"ΚΑΤΗΓΟΡΙΑ": "3. ΑΝΑΛΥΣΗ ΟΓΚΩΝ (UNITS)", "ΣΤΟΙΧΕΙΟ": "Δωρεάν Τεμάχια (Free Goods)", "ΣΕΝΑΡΙΟ Α": f"{sA_free} τμχ", "ΣΕΝΑΡΙΟ Β": "0 τμχ"},
                    {"ΚΑΤΗΓΟΡΙΑ": "3. ΑΝΑΛΥΣΗ ΟΓΚΩΝ (UNITS)", "ΣΤΟΙΧΕΙΟ": "Συνολικό Stock που θα φύγει", "ΣΕΝΑΡΙΟ Α": f"{sA_total_units} τμχ", "ΣΕΝΑΡΙΟ Β": f"{sB_total_units} τμχ"},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},

                    {"ΚΑΤΗΓΟΡΙΑ": "4. ΟΙΚΟΝΟΜΙΚΟ P&L", "ΣΤΟΙΧΕΙΟ": "Συνολικά Έσοδα (Revenue)", "ΣΕΝΑΡΙΟ Α": f"{sA_revenue:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_revenue:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "4. ΟΙΚΟΝΟΜΙΚΟ P&L", "ΣΤΟΙΧΕΙΟ": "Συνολικό Κόστος Παραγωγής (COGS)", "ΣΕΝΑΡΙΟ Α": f"{sA_cost:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_cost:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "4. ΟΙΚΟΝΟΜΙΚΟ P&L", "ΣΤΟΙΧΕΙΟ": "Μικτό Κέρδος (Gross Profit)", "ΣΕΝΑΡΙΟ Α": f"{sA_profit:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_profit:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "4. ΟΙΚΟΝΟΜΙΚΟ P&L", "ΣΤΟΙΧΕΙΟ": "Κόστος Εμπορικής Ενέργειας", "ΣΕΝΑΡΙΟ Α": f"{sA_loss:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_loss:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},

                    {"ΚΑΤΗΓΟΡΙΑ": "5. KPIs & PERFORMANCE", "ΣΤΟΙΧΕΙΟ": "Margin % (Επί του Τζίρου)", "ΣΕΝΑΡΙΟ Α": f"{sA_margin:.2f}%", "ΣΕΝΑΡΙΟ Β": f"{sB_margin:.2f}%"},
                    {"ΚΑΤΗΓΟΡΙΑ": "5. KPIs & PERFORMANCE", "ΣΤΟΙΧΕΙΟ": "Markup % (Επί του Κόστους)", "ΣΕΝΑΡΙΟ Α": f"{sA_markup:.2f}%", "ΣΕΝΑΡΙΟ Β": f"{sB_markup:.2f}%"},
                    {"ΚΑΤΗΓΟΡΙΑ": "5. KPIs & PERFORMANCE", "ΣΤΟΙΧΕΙΟ": "Ποσοστό Έκπτωσης (Direct/Indirect)", "ΣΕΝΑΡΙΟ Α": f"{sA_indirect_disc:.1f}%", "ΣΕΝΑΡΙΟ Β": f"{sB_discount:.1f}%"},
                    {"ΚΑΤΗΓΟΡΙΑ": "", "ΣΤΟΙΧΕΙΟ": "", "ΣΕΝΑΡΙΟ Α": "", "ΣΕΝΑΡΙΟ Β": ""},

                    {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "Κερδοφορία ανά τμχ (Net)", "ΣΕΝΑΡΙΟ Α": f"{(sA_profit/sA_total_units):.2f} €", "ΣΕΝΑΡΙΟ Β": f"{(sB_profit/sB_total_units):.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "Διαφορά Κέρδους Συμφωνίας", "ΣΕΝΑΡΙΟ Α": f"{diff_val:.2f} €" if sA_profit > sB_profit else "-", "ΣΕΝΑΡΙΟ Β": f"{diff_val:.2f} €" if sB_profit > sA_profit else "-"},
                    {"ΚΑΤΗΓΟΡΙΑ": "6. ΤΕΛΙΚΗ ΑΞΙΟΛΟΓΗΣΗ", "ΣΤΟΙΧΕΙΟ": "ΚΑΤΑΣΤΑΣΗ ΕΓΚΡΙΣΗΣ", "ΣΕΝΑΡΙΟ Α": "ΕΠΙΛΟΓΗ" if sA_profit > sB_profit else "-", "ΣΕΝΑΡΙΟ Β": "ΕΠΙΛΟΓΗ" if sB_profit > sA_profit else "-"}
                ]
                
                df_rep = pd.DataFrame(full_audit_data)
                csv = df_rep.to_csv(index=False, sep=';', encoding='utf-8-sig')
                
                st.download_button(
                    label="📥 Λήψη Πλήρους Φακέλου (CSV)", 
                    data=csv, 
                    file_name=f"Full_Audit_Report_{choice}.csv",
                    mime="text/csv"
                )
# --- 7. DASHBOARD ---
elif page == "📈 Dashboard":
    st.header("📈 Στατιστικά Πωλήσεων & Ιστορικό")
    if not df_history.empty:
        fig = px.bar(df_history.groupby("Cocktail")["Τεμάχια"].sum().reset_index(), 
                     x="Cocktail", y="Τεμάχια", 
                     title="Συνολικές Πωλήσεις ανά Cocktail", 
                     color="Cocktail")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Πλήρες Ιστορικό")
        st.dataframe(df_history.sort_values("Ημερομηνία", ascending=False), use_container_width=True)
        
        st.divider()
        st.subheader("⚠️ Διαχείριση Δεδομένων")
        
        if "delete_confirm" not in st.session_state:
            st.session_state.delete_confirm = False

        if not st.session_state.delete_confirm:
            if st.button("🗑️ Καθαρισμός Ιστορικού"):
                st.session_state.delete_confirm = True
                st.rerun()
        else:
            st.warning("Είστε σίγουροι ότι θέλετε να διαγράψετε όλο το ιστορικό;")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Ναι, Διαγραφή"):
                    new_df = pd.DataFrame(columns=["Ημερομηνία", "Πελάτης", "Cocktail", "Τεμάχια"])
                    new_df.to_csv(DB_HISTORY, index=False)
                    st.session_state.delete_confirm = False
                    st.success("Διαγράφηκε!")
                    st.rerun()
            with c2:
                if st.button("❌ Άκυρο"):
                    st.session_state.delete_confirm = False
                    st.rerun()
    else:
        st.info("Δεν υπάρχουν ακόμα δεδομένα στο ιστορικό.")

       # --- 7. SHOP SYNC (V30 - WOOCOMMERCE API & ANALYSIS) ---
elif page == "🌐 Shop Sync":
    st.header("🌐 Συγχρονισμός & Ανάλυση Ημέρας (WooCommerce API)")
    
    # Διαδρομές αρχείων
    recipes_path = r"/Users/christossiamantas/Documents/recipes.xlsx"
    WC_URL = "https://your-site-url.gr" # <--- Βάλε το URL του site σου εδώ

    if 'sync_results' not in st.session_state:
        st.session_state['sync_results'] = []

    tab1, tab2 = st.tabs(["📥 Λήψη από WooCommerce", "📊 Ανάλυση Υλικών"])

    with tab1:
        st.subheader("Σύνδεση με το Κατάστημα")
        c1, c2 = st.columns(2)
        ck = c1.text_input("Consumer Key (ck_...)", type="password")
        cs = c2.text_input("Consumer Secret (cs_...)", type="password")
        g_date = st.date_input("Επιλέξτε Ημερομηνία:", value=datetime.now().date())

        if st.button("🚀 Λήψη Παραγγελιών"):
            if not ck or not cs:
                st.warning("Παρακαλώ εισάγετε τα API Keys.")
            else:
                import requests
                from requests.auth import HTTPBasicAuth
                
                # ISO Format για το API
                date_start = f"{g_date}T00:00:00"
                date_end = f"{g_date}T23:59:59"
                
                endpoint = f"{WC_URL}/wp-json/wc/v3/orders"
                params = {"after": date_start, "before": date_end, "per_page": 100}
                
                try:
                    with st.spinner("Επικοινωνία με το WooCommerce..."):
                        response = requests.get(endpoint, auth=HTTPBasicAuth(ck, cs), params=params)
                        
                        if response.status_code == 200:
                            orders = response.json()
                            results = []
                            
                            for order in orders:
                                # Λήψη Επωνυμίας ή Ονόματος
                                customer = order.get("billing", {}).get("company", "")
                                if not customer:
                                    customer = f"{order.get('billing', {}).get('first_name')} {order.get('billing', {}).get('last_name')}"
                                
                                # Ανάλυση προϊόντων στην παραγγελία
                                for item in order.get("line_items", []):
                                    prod_name = item.get("name")
                                    qty = item.get("quantity", 0)
                                    
                                    results.append({
                                        "Ημερομηνία": g_date.strftime("%d/%m/%Y"),
                                        "Πελάτης": customer.upper(),
                                        "Cocktail": prod_name,
                                        "Τεμάχια": int(qty) * 24 # Μετατροπή σε μπουκάλια
                                    })
                            
                            st.session_state['sync_results'] = results
                            if results:
                                st.success(f"✅ Βρέθηκαν {len(results)} εγγραφές προϊόντων!")
                                st.dataframe(pd.DataFrame(results), use_container_width=True)
                            else:
                                st.warning("Δεν βρέθηκαν παραγγελίες για αυτή την ημερομηνία.")
                        else:
                            st.error(f"Σφάλμα API: {response.status_code} - Ελέγξτε τα κλειδιά και το URL.")
                except Exception as e:
                    st.error(f"Αποτυχία σύνδεσης: {e}")

    with tab2:
        st.subheader("📊 Συνολικά Υλικά προς Προετοιμασία")
        
        if st.session_state['sync_results']:
            if os.path.exists(recipes_path):
                df_orders = pd.DataFrame(st.session_state['sync_results'])
                df_recipes = pd.read_excel(recipes_path)
                analysis = []
                
                for _, order in df_orders.iterrows():
                    # Ψάχνουμε τη συνταγή (προσπάθησε να ταιριάξεις το όνομα)
                    # Χρησιμοποιούμε "in" για να πιάνουμε ονόματα όπως "Aegean Kings 200ml"
                    recipe = df_recipes[df_recipes['Cocktail'].apply(lambda x: str(x).lower() in order['Cocktail'].lower())]
                    
                    if recipe.empty:
                        # Δεύτερη προσπάθεια αν το όνομα στη συνταγή είναι πιο μικρό
                        recipe = df_recipes[df_recipes['Cocktail'].apply(lambda x: order['Cocktail'].lower() in str(x).lower())]

                    for _, ing in recipe.iterrows():
                        # Υπολογισμός (ml ανά 1L / 5) * συνολικά μπουκάλια 200ml
                        total_needed = (ing['Ποσότητα'] / 5) * order['Τεμάχια']
                        analysis.append({
                            "Συστατικό": ing['Συστατικό'],
                            "Ποσότητα": total_needed
                        })
                
                if analysis:
                    df_ana = pd.DataFrame(analysis)
                    final_sum = df_ana.groupby("Συστατικό")["Ποσότητα"].sum().reset_index()
                    
                    st.write(f"**Ανάλυση για την ημέρα: {g_date.strftime('%d/%m/%Y')}**")
                    st.dataframe(final_sum.style.format({"Ποσότητα": "{:.0f} ml/gr"}), use_container_width=True)
                    
                    if st.button("📉 Ενημέρωση Αποθήκης"):
                        st.info("Η λειτουργία ενημέρωσης αποθήκης είναι έτοιμη για διασύνδεση.")
                else:
                    st.error("⚠️ Δεν βρέθηκαν αντιστοιχίες στις Συνταγές για τα προϊόντα του Shop.")
            else:
                st.error(f"❌ Δεν βρέθηκε το αρχείο συνταγών στο: {recipes_path}")
        else:
            st.info("Κάντε πρώτα λήψη παραγγελιών από το Tab 1.")

      # --- 8. LOT ΠΑΡΑΓΩΓΗΣ (ΜΕ ΑΥΤΟΜΑΤΗ ΑΝΑΚΤΗΣΗ & ΠΛΗΡΕΣ ΙΣΤΟΡΙΚΟ) ---
elif page == "📦 Lot Παραγωγής":
    st.header("📦 Αναλυτικό Δελτίο Παραγωγής")
    
    import glob
    from requests.auth import HTTPBasicAuth
    import requests

    selected_date = st.date_input("Ημερομηνία Παραγωγής", value=datetime.now(), format="DD/MM/YYYY")
    date_display = selected_date.strftime('%d/%m/%Y')
    current_time = datetime.now().strftime('%H:%M')

    # Αρχικοποίηση session_state για την ανάκτηση
    if "auto_cocktails" not in st.session_state:
        st.session_state.auto_cocktails = []
    if "auto_counts" not in st.session_state:
        st.session_state.auto_counts = {}

    # --- ΤΜΗΜΑ ΑΝΑΚΤΗΣΗΣ ΑΠΟ E-SHOP ---
    st.subheader("🌐 Αυτόματη Ανάκτηση από E-shop")
    col_api1, col_api2, col_api3 = st.columns([1, 1, 1])
    ck_input = col_api1.text_input("Consumer Key", type="password", key="lot_ck_ui")
    cs_input = col_api2.text_input("Consumer Secret", type="password", key="lot_cs_ui")
    
    if col_api3.button("📥 Φόρτωση Παραγγελιών"):
        try:
            url = "https://cabclub.gr/wp-json/wc/v3/orders?status=processing&per_page=100"
            res = requests.get(url, auth=HTTPBasicAuth(ck_input, cs_input))
            if res.status_code == 200:
                wc_data = res.json()
                found_names = []
                temp_counts = {}
                for order in wc_data:
                    for item in order.get('line_items', []):
                        sku = str(item.get('sku')).strip()
                        qty = int(item.get('quantity', 0))
                        match = df_rec[df_rec["Barcode"].astype(str) == sku]
                        if not match.empty:
                            c_name = match.iloc[0]["Ονομα"]
                            found_names.append(c_name)
                            temp_counts[c_name] = temp_counts.get(c_name, 0) + qty
                
                st.session_state.auto_cocktails = list(set(found_names))
                st.session_state.auto_counts = temp_counts
                st.success(f"✅ Φορτώθηκαν {len(st.session_state.auto_cocktails)} κωδικοί!")
                st.rerun()
            else:
                st.error("Αποτυχία σύνδεσης. Ελέγξτε τα κλειδιά.")
        except Exception as e:
            st.error(f"Σφάλμα: {e}")

    st.divider()
    
    if not df_rec.empty:
        st.subheader("🍸 1. Επιλογή Προϊόντων")
        selected_cocktails = st.multiselect(
            "Ποια cocktail φτιάχνετε;", 
            options=df_rec["Ονομα"].unique(),
            default=st.session_state.auto_cocktails
        )
        
        counts = {}
        if selected_cocktails:
            col_counts = st.columns(len(selected_cocktails))
            for i, name in enumerate(selected_cocktails):
                default_val = st.session_state.auto_counts.get(name, 1)
                counts[name] = col_counts[i].number_input(f"Τεμάχια: {name}", min_value=1, value=int(default_val), key=f"cnt_{name}")

            st.subheader("⚖️ 2. Οδηγίες Ζύγισης & Ιχνηλασιμότητα")
            lot_entries = []
            
            with st.form("detailed_lot_form"):
                for cocktail_name in selected_cocktails:
                    st.markdown(f"#### 🏷️ {cocktail_name} (LOT: {date_display})")
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    
                    h1, h2, h3, h4, h5 = st.columns([2, 1.2, 1.3, 1, 1])
                    h1.caption("Πρώτη Ύλη")
                    h2.caption("Σύνολο ml")
                    h3.caption("Στόχος (g)")
                    h4.caption("Lot Number")
                    h5.caption("Ημ. Λήξης")
                    
                    for i in range(1, 14):
                        ing_name = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        ml_unit = recipe_row.get(f"ML{i}", 0.0)
                        
                        if ing_name and ing_name not in ["ΚΕΝΟ", "nan", "Νερό", ""]:
                            total_ml = ml_unit * counts[cocktail_name]
                            target_grams = total_ml 
                            
                            ing_data = df_ing[df_ing["Name"] == ing_name]
                            if not ing_data.empty:
                                vol_pack = ing_data.iloc[0].get("Volume", 700)
                                weight_pack = ing_data.iloc[0].get("Weight_Full", 0)
                                if weight_pack > 0:
                                    target_grams = (total_ml / vol_pack) * weight_pack

                            c1, c2, c3, c4, c5 = st.columns([2, 1.2, 1.3, 1, 1])
                            c1.write(f"**{ing_name}**")
                            c2.write(f"{total_ml:.0f} ml")
                            c3.markdown(f"<span style='color:#d32f2f; font-weight:bold;'>{target_grams:.1f} g</span>", unsafe_allow_html=True)
                            
                            l_num = c4.text_input("Lot", key=f"lot_{cocktail_name}_{ing_name}_{i}", label_visibility="collapsed", placeholder="Lot")
                            l_exp = c5.text_input("Λήξη", key=f"exp_{cocktail_name}_{ing_name}_{i}", label_visibility="collapsed", placeholder="MM/YY")
                            
                            lot_entries.append({
                                "Ημερομηνία": date_display,
                                "Ώρα": current_time,
                                "Cocktail": cocktail_name,
                                "Τεμάχια": counts[cocktail_name],
                                "Υλικό": ing_name,
                                "Σύνολο_ML": total_ml,
                                "Στόχος_Γραμμάρια": round(target_grams, 1),
                                "Lot Number": l_num,
                                "Ημ_Λήξης": l_exp
                            })
                    st.markdown("---")
                
                if st.form_submit_button("💾 Οριστικοποίηση & Αποθήκευση"):
                    if lot_entries:
                        csv_file = f"Lot_Report_{selected_date.strftime('%d_%m_%Y')}.csv"
                        new_data = pd.DataFrame(lot_entries)
                        if os.path.exists(csv_file):
                            final_df = pd.concat([pd.read_csv(csv_file), new_data], ignore_index=True).drop_duplicates()
                        else:
                            final_df = new_data
                        final_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                        st.success(f"✅ Η παραγωγή αποθηκεύτηκε επιτυχώς!")
                        st.rerun()

    # --- ΤΜΗΜΑ ΙΣΤΟΡΙΚΟΥ & ΕΚΤΥΠΩΣΗΣ ---
    st.markdown("---")
    st.subheader("📂 Ιστορικό & Διαχείριση Αρχείου")
    past_files = glob.glob("Lot_Report_*.csv")
    
    if past_files:
        dates = sorted([f.replace("Lot_Report_", "").replace(".csv", "").replace("_", "/") for f in past_files], reverse=True)
        col_select, col_delete = st.columns([3, 1])
        sel_date = col_select.selectbox("Επιλέξτε Ημερομηνία:", dates)
        
        if sel_date:
            file_path = f"Lot_Report_{sel_date.replace('/', '_')}.csv"
            
            if col_delete.button("🗑️ Διαγραφή Δελτίου", use_container_width=True):
                try:
                    os.remove(file_path)
                    st.error(f"Το δελτίο {sel_date} διαγράφηκε.")
                    st.rerun()
                except Exception as e:
                    st.warning(f"Σφάλμα: {e}")

            if os.path.exists(file_path):
                df_past = pd.read_csv(file_path)
                column_mapping = {"Cocktails": "Cocktail", "Ημ_Λήξης": "Ημ_Λήξης", "Ημ. Λήξης": "Ημ_Λήξης"}
                df_past = df_past.rename(columns=column_mapping)
                
                for col in ["Στόχος_Γραμμάρια", "Σύνολο_ML", "Ημ_Λήξης", "Ώρα", "Τεμάχια"]:
                    if col not in df_past.columns:
                        df_past[col] = "N/A"

                st.dataframe(df_past, use_container_width=True)
                
                html = f"""
                <html><head><meta charset='UTF-8'><style>
                    body {{ font-family: sans-serif; padding: 20px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 14px; }}
                    th, td {{ border: 1px solid #000; padding: 8px; text-align: left; }}
                    th {{ background: #f2f2f2; }}
                    .section-title {{ background: #444; color: #fff; padding: 8px; margin-top: 20px; font-weight: bold; }}
                </style></head><body>
                    <h1>ΔΕΛΤΙΟ ΠΑΡΑΓΩΓΗΣ: {sel_date}</h1>
                    <p>Ημερομηνία Εκτύπωσης: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                """
                
                if not df_past.empty:
                    html += "<h3>1. Σύνοψη Παρτίδων</h3><table><tr><th>Προϊόν</th><th>Ποσότητα</th><th>Ώρα</th></tr>"
                    summary = df_past.groupby(["Cocktail", "Ώρα"])["Τεμάχια"].first().reset_index()
                    for _, row in summary.iterrows():
                        html += f"<tr><td>{row['Cocktail']} (LOT: {sel_date})</td><td>{row['Τεμάχια']} τμχ</td><td>{row['Ώρα']}</td></tr>"
                    html += "</table>"

                    html += "<h3>2. Αναλυτική Ζύγιση & Lot Υλικών</h3>"
                    for t_val in df_past["Ώρα"].unique():
                        time_df = df_past[df_past["Ώρα"] == t_val]
                        for c_name in time_df["Cocktail"].unique():
                            c_data = time_df[time_df["Cocktail"] == c_name]
                            qty = c_data['Τεμάχια'].iloc[0]
                            html += f"<div class='section-title'>{c_name} | LOT: {sel_date} | Ποσότητα: {qty} τμχ</div>"
                            html += "<table><tr><th>Πρώτη Ύλη</th><th>Σύνολο ml</th><th>Βάρος (g)</th><th>Lot Number</th><th>Λήξη</th></tr>"
                            for _, r in c_data.iterrows():
                                html += f"""<tr>
                                    <td>{r['Υλικό']}</td>
                                    <td>{r['Σύνολο_ML']}</td>
                                    <td><b>{r['Στόχος_Γραμμάρια']}</b></td>
                                    <td>{r['Lot Number']}</td>
                                    <td>{r['Ημ_Λήξης']}</td>
                                </tr>"""
                            html += "</table>"
                
                html += "<br><p>Υπογραφή Υπευθύνου: __________________________</p></body></html>"
                st.download_button("🖨️ Λήψη Δελτίου για Εκτύπωση", data=html, file_name=f"Production_{sel_date.replace('/','_')}.html", mime="text/html")

                # --- 9. ΑΝΤΙΚΑΤΑΣΤΑΣΗ ΥΛΙΚΟΥ (BULK UPDATE) ---
elif page == "🔄 Αντικατάσταση":
    st.header("🔄 Μαζική Αντικατάσταση Πρώτης Ύλης")
    st.info("Βρείτε σε ποιες συνταγές υπάρχει ένα υλικό και αντικαταστήστε το παντού με ένα νέο.")

    if not df_rec.empty:
        # 1. Συλλογή όλων των υλικών που χρησιμοποιούνται στις συνταγές
        used_ingredients = []
        for i in range(1, 14):
            col_name = f"ΣΥΣΤΑΤΙΚΟ{i}"
            if col_name in df_rec.columns:
                used_ingredients.extend(df_rec[col_name].astype(str).unique())
        
        # Καθαρισμός λίστας από κενά και nan
        unique_used = sorted(list(set([ing for ing in used_ingredients if ing not in ["ΚΕΝΟ", "nan", "None", ""]])))
        
        col_src, col_dst = st.columns(2)
        
        with col_src:
            target_ing = st.selectbox("1. Επιλέξτε υλικό προς αντικατάσταση:", options=unique_used)
        
        # 2. Εύρεση συνταγών που το περιέχουν
        found_recipes = []
        for index, row in df_rec.iterrows():
            for i in range(1, 14):
                if str(row.get(f"ΣΥΣΤΑΤΙΚΟ{i}")) == target_ing:
                    found_recipes.append(row["Ονομα"])
                    break
        
        if found_recipes:
            st.warning(f"🔎 Το υλικό **{target_ing}** βρέθηκε σε **{len(found_recipes)}** συνταγές:")
            st.write(", ".join(found_recipes))
            
            with col_dst:
                # Επιλογή νέου υλικού από την Αποθήκη (df_ing)
                new_ing = st.selectbox("2. Αντικατάσταση με:", options=df_ing["Name"].unique())
            
            st.markdown("---")
            if st.button("🚀 Εκτέλεση Αντικατάστασης ΠΑΝΤΟΥ"):
                # Δημιουργούμε αντίγραφο
                temp_recipes = df_rec.copy()
                total_changes = 0
                
                for i in range(1, 14):
                    col = f"ΣΥΣΤΑΤΙΚΟ{i}"
                    mask = temp_recipes[col].astype(str) == target_ing
                    total_changes += mask.sum()
                    temp_recipes.loc[mask, col] = new_ing
                
                # Αποθήκευση στο CSV
                temp_recipes.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                st.success(f"✅ Επιτυχία! Το '{target_ing}' αντικαταστάθηκε από το '{new_ing}' σε {total_changes} σημεία.")
                st.balloons()
                st.rerun()
        else:
            st.info("Δεν βρέθηκαν συνταγές που να περιέχουν αυτό το υλικό.")
