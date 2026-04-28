import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime
import plotly.express as px

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

# Προσθήκη CSS
st.markdown("""
    <style>
    /* Φόντο όλης της εφαρμογής */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Στυλ για τα Metrics (Κέρδος, Κόστος κλπ) */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00ffcc; /* Ένα neon κυανό χρώμα για τις τιμές */
    }
    
    /* Στυλ για τα κουτιά των metrics */
    div[data-testid="stMetric"] {
        background-color: #1e2129;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }

    /* Κουμπιά με πιο έντονο στυλ */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #3e4451;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        border: 1px solid #00ffcc;
        color: #00ffcc;
    }
    </style>
    """, unsafe_allow_html=True)

# Αρχεία Βάσης
DB_INGREDIENTS = "db_ingredients.csv"
DB_RECIPES = "db_recipes.csv"
DB_ORDERS = "db_orders.csv"
DB_HISTORY = "db_history.csv"

TOTAL_FIXED = 0.22  
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

def format_greek(value):
    if isinstance(value, (int, float)):
        return "{:.3f}".format(value).replace('.', ',')
    return value

def load_data():
    if os.path.exists(DB_INGREDIENTS):
        ing = pd.read_csv(DB_INGREDIENTS)
    else:
        ing = pd.DataFrame(columns=["Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Απόθεμα (ml)"])
    
    for col in ["Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Απόθεμα (ml)"]:
        if col not in ing.columns:
            ing[col] = 0.0 if col != "Name" else "Νέο Υλικό"
            
    if os.path.exists(DB_RECIPES):
        rec = pd.read_csv(DB_RECIPES)
    else:
        cols_rec = ["Ονομα", "Τιμή Καταλόγου"] + [f"ΣΥΣΤΑΤΙΚΟ{i}" for i in range(1,14)] + [f"ML{i}" for i in range(1,14)]
        rec = pd.DataFrame(columns=cols_rec)
        
    if os.path.exists(DB_ORDERS):
        orders = pd.read_csv(DB_ORDERS, dtype={"Πελάτης": str, "Cocktail": str})
    else:
        orders = pd.DataFrame(columns=["Πελάτης", "Cocktail", "Τεμάχια"])
    orders["Πελάτης"] = orders["Πελάτης"].astype(str).replace("nan", "")

    if os.path.exists(DB_HISTORY):
        history = pd.read_csv(DB_HISTORY)
    else:
        history = pd.DataFrame(columns=["Ημερομηνία", "Πελάτης", "Cocktail", "Τεμάχια"])
        
    return ing, rec, orders, history

df_ing, df_rec, df_orders, df_history = load_data()
ing_options = ["ΚΕΝΟ", "Νερό"] + sorted(df_ing["Name"].unique().tolist()) if not df_ing.empty else ["ΚΕΝΟ", "Νερό"]
recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

# --- Sidebar ---
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "📝 Νέα Συνταγή", "📊 Διαχείριση", "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "🛒 Παραγγελίες", "📈 Dashboard"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών & Τιμών")
    cols_to_show = ["Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %"]
    column_config_ing = {
        "Name": st.column_config.TextColumn("Όνομα Υλικού"),
        "Price": st.column_config.NumberColumn("Τιμή Αγοράς (€)"),
        "Volume": st.column_config.NumberColumn("ML Φιάλης"),
        "Τιμή/ml": st.column_config.NumberColumn("Τιμή/ml", disabled=True),
        "Αλκοόλ %": st.column_config.NumberColumn("Alc %")
    }
    edited_ing = st.data_editor(df_ing[cols_to_show], column_config=column_config_ing, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Αποθήκευση Υλικών"):
        temp_df = edited_ing.copy()
        temp_df["Τιμή/ml"] = temp_df["Price"] / temp_df["Volume"].replace(0, 1)
        final_df = temp_df.merge(df_ing[["Name", "Απόθεμα (ml)"]], on="Name", how="left")
        final_df["Απόθεμα (ml)"] = final_df["Απόθεμα (ml)"].fillna(0.0)
        final_df.to_csv(DB_INGREDIENTS, index=False)
        st.success("Η αποθήκη ενημερώθηκε!")
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
                new_row = {"Ονομα": name, "Τιμή Καταλόγου": cat_price, **recipe_data}
                df_rec = pd.concat([df_rec, pd.DataFrame([new_row])], ignore_index=True)
                df_rec.to_csv(DB_RECIPES, index=False)
                st.success("Αποθηκεύτηκε!")
                st.rerun()

# --- 3. ΔΙΑΧΕΙΡΙΣΗ ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία Συνταγών")
    if not df_rec.empty:
        df_rec["Τιμή Αντιπροσώπου"] = df_rec["Τιμή Καταλόγου"] * 0.74
        config_rec = {"Ονομα": st.column_config.TextColumn("Όνομα", width="medium")}
        for i in range(1, 14):
            config_rec[f"ΣΥΣΤΑΤΙΚΟ{i}"] = st.column_config.SelectboxColumn(f"Υλικό {i}", options=ing_options)
            config_rec[f"ML{i}"] = st.column_config.NumberColumn(f"ML {i}")
        ed = st.data_editor(df_rec, column_config=config_rec, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Αποθήκευση"):
            to_save = ed.drop(columns=["Τιμή Αντιπροσώπου"]) if "Τιμή Αντιπροσώπου" in ed.columns else ed
            to_save.to_csv(DB_RECIPES, index=False)
            st.success("Ενημερώθηκε!")
            st.rerun()

# --- 4. ΑΝΑΛΥΣΗ ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση & Κερδοφορία")
    
    if not df_rec.empty:
        st.sidebar.subheader("Ρυθμίσεις Ανάλυσης")
        discount = st.sidebar.slider("Έκπτωση Προσφοράς %", 0, 100, 0)
        agent_rate = 0.74 

        choice = st.selectbox("Επιλέξτε Cocktail για ανάλυση:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        # --- 1. ΥΠΟΛΟΓΙΣΜΟΙ ΤΙΜΩΝ ---
        p_retail = float(r["Τιμή Καταλόγου"])
        p_agent = p_retail * agent_rate
        p_custom = p_retail * (1 - discount/100)
        
        # --- 2. ΥΠΟΛΟΓΙΣΜΟΣ ΚΟΣΤΟΥΣ & ML ---
        raw_cost, pure_alc_ml, total_ml_cocktail = 0.0, 0.0, 0.0
        breakdown = []
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
            ml = float(r.get(f"ML{i}", 0))
            
            if ing_n != "ΚΕΝΟ" and ml > 0:
                total_ml_cocktail += ml  # Προσθήκη στα συνολικά ML
                
                if ing_n not in ["nan", "Νερό", ""]:
                    match = df_ing[df_ing["Name"] == ing_n]
                    if not match.empty:
                        c_ml = float(match.iloc[0]["Τιμή/ml"])
                        item_cost = ml * c_ml
                        raw_cost += item_cost
                        pure_alc_ml += (ml * float(match.iloc[0]["Αλκοόλ %"]) / 100)
                        breakdown.append({"Υλικό": ing_n, "ML": ml, "Κόστος": item_cost})

        # Ο ΕΦΚ έχει ήδη υπολογιστεί στην τιμή κτήσης των υλικών
        efk_info = pure_alc_ml * tax_factor * 100
        total_production = raw_cost + TOTAL_FIXED 
        
        # --- 3. ΥΠΟΛΟΓΙΣΜΟΣ ΚΕΡΔΩΝ / MARGIN / MARKUP ---
        profit_retail = p_retail - total_production
        profit_agent = p_agent - total_production
        
        margin_retail = (profit_retail / p_retail * 100) if p_retail > 0 else 0
        margin_agent = (profit_agent / p_agent * 100) if p_agent > 0 else 0
        
        markup_retail = (profit_retail / total_production * 100) if total_production > 0 else 0
        markup_agent = (profit_agent / total_production * 100) if total_production > 0 else 0

        # --- ΕΜΦΑΝΙΣΗ ---
        st.subheader(f"Στατιστικά για: {choice}")
        
        # Γενικές Πληροφορίες Cocktail
        st.info(f"**Συνολική Ποσότητα Cocktail:** {total_ml_cocktail:.1f} ml")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Τιμή Λιανικής", f"{format_greek(p_retail)}€")
        c2.metric("Τιμή Αντιπροσώπου", f"{format_greek(p_agent)}€")
        c3.metric("Τιμή με Έκπτωση", f"{format_greek(p_custom)}€", delta=f"-{discount}%")

        st.markdown("---")

        # Ανάλυση Κερδοφορίας
        st.write("### 💰 Ανάλυση Κερδοφορίας (Margin & Markup)")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**Πώληση Λιανικής**")
            st.metric("Κέρδος", f"{format_greek(profit_retail)}€")
            st.write(f"**Margin:** {margin_retail:.1f}% | **Markup:** {markup_retail:.1f}%")
        with m2:
            st.markdown("**Πώληση Αντιπροσώπου**")
            st.metric("Κέρδος", f"{format_greek(profit_agent)}€")
            st.write(f"**Margin:** {margin_agent:.1f}% | **Markup:** {markup_agent:.1f}%")

        st.markdown("---")

        # Ανάλυση Κόστους
        st.write("### 🛠️ Ανάλυση Κόστους & Φόρων")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Κόστος Υλικών", f"{format_greek(raw_cost)}€")
        k2.metric("ΕΦΚ (Ενσωματωμένος)", f"{format_greek(efk_info)}€", help="Ο ΕΦΚ έχει ήδη υπολογιστεί στην τιμή αγοράς.")
        k3.metric("Σταθερά Έξοδα", f"{format_greek(TOTAL_FIXED)}€")
        k4.metric("ΣΥΝΟΛΟ ΚΟΣΤΟΥΣ", f"{format_greek(total_production)}€", delta_color="inverse")

        # Πίνακας Υλικών
        st.markdown("---")
        st.write("### 🍹 Αναλυτική Σύνθεση Συνταγής")
        df_br = pd.DataFrame(breakdown)
        if not df_br.empty:
            df_br["% στο Κόστος"] = (df_br["Κόστος"] / raw_cost * 100)
            st.dataframe(df_br.style.format({"ML": "{:.1f}", "Κόστος": "{:.3f}€", "% στο Κόστος": "{:.1f}%"}), use_container_width=True)

        # --- 5. ΕΞΕΛΙΓΜΕΝΟ ΑΝΑΛΥΤΙΚΟ REPORT (CSV) ---
        report_lines = []
        
        # Βοηθητική συνάρτηση για ομοιόμορφη προσθήκη γραμμών
        def add_line(desc, val):
            report_lines.append({"ΠΕΡΙΓΡΑΦΗ": desc, "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": val})

        add_line("--- ΓΕΝΙΚΑ ΣΤΟΙΧΕΙΑ ---", "")
        add_line("COCKTAIL:", choice)
        add_line("Ημερομηνία Αναφοράς:", datetime.now().strftime("%d/%m/%Y %H:%M"))
        add_line("Συνολική Ποσότητα:", f"{total_ml_cocktail:.1f} ml")
        
        add_line("--- ΟΙΚΟΝΟΜΙΚΗ ΑΝΑΛΥΣΗ ---", "")
        add_line("Κόστος Υλικών:", f"{format_greek(raw_cost)} €")
        add_line("Σταθερά Έξοδα:", f"{format_greek(TOTAL_FIXED)} €")
        add_line("ΣΥΝΟΛΙΚΟ ΚΟΣΤΟΣ:", f"{format_greek(total_production)} €")
        add_line("ΕΦΚ (Ενσωματωμένος):", f"{format_greek(efk_info)} €")
        
        add_line("--- ΠΩΛΗΣΗ ΛΙΑΝΙΚΗΣ ---", "")
        add_line("Τιμή Πώλησης:", f"{format_greek(p_retail)} €")
        add_line("Καθαρό Κέρδος:", f"{format_greek(profit_retail)} €")
        add_line("Margin %:", f"{margin_retail:.2f} %")
        add_line("Markup %:", f"{markup_retail:.2f} %")
        
        add_line("--- ΠΩΛΗΣΗ ΑΝΤΙΠΡΟΣΩΠΟΥ ---", "")
        add_line("Τιμή Πώλησης:", f"{format_greek(p_agent)} €")
        add_line("Καθαρό Κέρδος:", f"{format_greek(profit_agent)} €")
        add_line("Margin %:", f"{margin_agent:.2f} %")
        add_line("Markup %:", f"{markup_agent:.2f} %")
        
        add_line("--- ΑΝΑΛΥΤΙΚΗ ΣΥΝΤΑΓΗ ---", "")
        for item in breakdown:
            item_perc = (item['Κόστος'] / raw_cost * 100) if raw_cost > 0 else 0
            add_line(f"Συστατικό: {item['Υλικό']}", f"{item['ML']} ml | {format_greek(item['Κόστος'])} € | ({item_perc:.1f}%)")
            
        add_line("-----------------------", "-----------------------")
        add_line("APPLICATION:", "DC CABCLUB 2026")

        # Δημιουργία DataFrame
        df_export = pd.DataFrame(report_lines)

        # Μετατροπή σε CSV με UTF-8-SIG για τα Ελληνικά και ερωτηματικό για το Excel
        csv_final = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig')
        
        st.download_button(
            label=f"📥 Λήψη Report: {choice}", 
            data=csv_final, 
            file_name=f"Report_{choice.replace(' ', '_')}.csv",
            mime="text/csv"
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

# --- 6. ΕΜΠΟΡΙΚΗ ΠΟΛΙΤΙΚΗ (PROMOTIONS) ---
elif page == "📊 Εμπορική Πολιτική":
    st.header("📊 Εμπορική Πολιτική & Προσφορές")
    st.write("Εισάγετε τα τεμάχια για να ξεκινήσει ο υπολογισμός.")

    if not df_rec.empty:
        choice = st.selectbox("Επιλέξτε Cocktail για την προσφορά:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]

        # 1. Βασικοί Υπολογισμοί Κόστους Μονάδας
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
        p_agent_base = p_retail * 0.74 

        st.divider()

        # 2. Εισαγωγή Δεδομένων (Μηδενικά στην αρχή)
        col1, col2 = st.columns(2)
        with col1:
            # Χρησιμοποιούμε value=0 για να είναι μηδενικά
            qty_paid = st.number_input("Τεμάχια προς Πώληση (Πληρωτέα)", min_value=0, value=0, step=1)
            qty_free = st.number_input("Τεμάχια Δώρο (Free Goods)", min_value=0, value=0, step=1)
        
        # Έλεγχος: Αν δεν έχουν μπει τεμάχια πώλησης, σταμάτα εδώ
        if qty_paid > 0:
            total_units = qty_paid + qty_free
            total_revenue = qty_paid * p_agent_base
            total_production_cost = total_units * unit_cost
            company_total_profit = total_revenue - total_production_cost
            
            with col2:
                st.metric("Συνολικά Έσοδα", f"{total_revenue:.2f} €")
                st.metric("Συνολικό Κέρδος Εταιρείας", f"{company_total_profit:.2f} €")

            st.divider()

            # 3. Σύγκριση Τιμών
            new_effective_price = total_revenue / total_units
            price_diff_percent = (1 - new_effective_price / p_agent_base) * 100
            price_diff_euro = p_agent_base - new_effective_price

            st.write("### 🏷️ Σύγκριση Τιμολόγησης Αντιπροσώπου")
            c1, c2, c3 = st.columns(3)
            c1.metric("Κανονική Τιμή Αντιπροσώπου", f"{p_agent_base:.2f} €")
            c2.metric("Πραγματική Τιμή (Effective)", f"{new_effective_price:.2f} €", delta=f"-{price_diff_percent:.1f}%")
            c3.metric("Έκπτωση ανά Τεμάχιο", f"{price_diff_euro:.2f} €")

            st.divider()

            # 4. Δείκτες Κερδοφορίας
            profit_per_unit = new_effective_price - unit_cost
            new_margin = (profit_per_unit / new_effective_price * 100) if new_effective_price > 0 else 0
            new_markup = (profit_per_unit / unit_cost * 100) if unit_cost > 0 else 0
            
            normal_profit = p_agent_base - unit_cost
            normal_margin = (normal_profit / p_agent_base * 100) if p_agent_base > 0 else 0
            normal_markup = (normal_profit / unit_cost * 100) if unit_cost > 0 else 0

            st.write("### 📈 Δείκτες Κερδοφορίας Προσφοράς")
            m1, m2, m3 = st.columns(3)
            m1.metric("Κέρδος ανά Τεμάχιο", f"{profit_per_unit:.2f} €")
            m2.metric("Νέο Margin %", f"{new_margin:.1f} %")
            m3.metric("Νέο Markup %", f"{new_markup:.1f} %")

            st.write("### ⚖️ Σύγκριση με Κανονική Ροή")
            ref1, ref2, ref3 = st.columns(3)
            ref1.metric("Κανονικό Κέρδος / Τμχ", f"{normal_profit:.2f} €")
            ref2.metric("Κανονικό Margin %", f"{normal_margin:.1f} %")
            ref3.metric("Κανονικό Markup %", f"{normal_markup:.1f} %")

            total_promo_cost = (normal_profit * total_units) - company_total_profit
            st.warning(f"**Κόστος Εμπορικής Ενέργειας:** {total_promo_cost:.2f} €")

            st.divider()

            # 5. Report
            if st.button("💾 Λήψη Υπερ-Αναλυτικού Report"):
                # (Ο κώδικας του report που φτιάξαμε πριν...)
                now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                promo_data = [
                    {"ΠΕΡΙΓΡΑΦΗ": "--- ΓΕΝΙΚΑ ΣΤΟΙΧΕΙΑ ---", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": ""},
                    {"ΠΕΡΙΓΡΑΦΗ": "COCKTAIL", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": choice},
                    {"ΠΕΡΙΓΡΑΦΗ": "Τεμάχια Πώλησης", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": f"{qty_paid}"},
                    {"ΠΕΡΙΓΡΑΦΗ": "Τεμάχια Δώρο", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": f"{qty_free}"},
                    {"ΠΕΡΙΓΡΑΦΗ": "ΚΑΘΑΡΟ ΚΕΡΔΟΣ ΕΤΑΙΡΕΙΑΣ", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": f"{company_total_profit:.2f} €"},
                    {"ΠΕΡΙΓΡΑΦΗ": "Πραγματική Τιμή Μονάδας", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": f"{new_effective_price:.2f} €"},
                    {"ΠΕΡΙΓΡΑΦΗ": "Margin Προσφοράς", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": f"{new_margin:.2f} %"},
                    {"ΠΕΡΙΓΡΑΦΗ": "Markup Προσφοράς", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ": f"{new_markup:.2f} %"}
                ]
                df_p = pd.DataFrame(promo_data)
                csv_p = df_p.to_csv(index=False, sep=';', encoding='utf-8-sig')
                st.download_button("📥 Λήψη Report", csv_p, f"Promo_{choice}.csv")
        else:
            st.info("💡 Παρακαλώ πληκτρολογήστε τον αριθμό των τεμαχίων προς πώληση για να εμφανιστεί η ανάλυση.")
            
    else:
        st.warning("Δεν υπάρχουν συνταγές.")
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
