import streamlit as st
import pandas as pd
import os
import math
import plotly.express as px

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026 - Ultimate", layout="wide", page_icon="🍸")

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
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "📝 Νέα Συνταγή", "📊 Διαχείριση", "🔍 Ανάλυση", "🛒 Παραγγελίες", "📈 Dashboard"])
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
    st.header("🔍 Οικονομική Ανάλυση")
    if not df_rec.empty:
        discount = st.sidebar.slider("Έκπτωση Προσφοράς %", 0, 100, 0)
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        p_retail = float(r["Τιμή Καταλόγου"])
        p_agent = p_retail * 0.74
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
        c1, c2, c3 = st.columns(3)
        c1.metric("Λιανική", f"{format_greek(p_retail)}€")
        c2.metric("Αντιπρόσωπος", f"{format_greek(p_agent)}€")
        c3.metric("Πώληση (με έκπτωση)", f"{format_greek(p_custom)}€")

        m = st.columns(5)
        m[0].metric("Υλικά", f"{format_greek(raw_cost)}€")
        m[1].metric("ΕΦΚ", f"{format_greek(efk)}€")
        m[2].metric("Σταθερά", f"{format_greek(TOTAL_FIXED)}€")
        m[3].metric("Σύνολο Κόστους", f"{format_greek(total_production)}€")
        m[4].metric("Καθαρό Κέρδος", f"{format_greek(profit)}€")
        
        st.write("**Σύνθεση Συνταγής:**")
        st.table(pd.DataFrame(breakdown))

        detailed_export = [
            ["Όνομα Cocktail", choice],
            ["Τιμή Καταλόγου", format_greek(p_retail)],
            ["Τιμή Αντιπροσώπου", format_greek(p_agent)],
            ["Τιμή Πώλησης (Με Έκπτωση)", format_greek(p_custom)],
            ["--- ΑΝΑΛΥΣΗ ΚΟΣΤΟΥΣ ΥΛΙΚΩΝ ---", ""]
        ]
        for item in breakdown:
            detailed_export.append([f"{item['Υλικό']} ({item['ML']}ml)", format_greek(item['Κόστος'])])
        
        detailed_export.extend([
            ["ΕΦΚ", format_greek(efk)],
            ["Σταθερά Έξοδα", format_greek(TOTAL_FIXED)],
            ["ΣΥΝΟΛΙΚΟ ΚΟΣΤΟΣ", format_greek(total_production)],
            ["ΚΑΘΑΡΟ ΚΕΡΔΟΣ", format_greek(profit)]
        ])
        
        csv_final = pd.DataFrame(detailed_export).to_csv(index=False, header=False, sep=';', encoding='utf-8-sig')
        st.download_button("📥 Λήψη Αναφοράς (Excel)", csv_final, f"Analysis_{choice}.csv")

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

# --- 6. DASHBOARD ---
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
