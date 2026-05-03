import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime
import plotly.express as px
import imaplib
import email

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")
# --- Σύστημα Password ---
def check_password():
    """Επιστρέφει True αν ο χρήστης έδωσε σωστό κωδικό."""
    def password_entered():
        # panatha1908
        if st.session_state["password"] == "panatha1908":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Διαγραφή κωδικού από το state για ασφάλεια
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Πρώτη φορά που ανοίγει η εφαρμογή
        st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Λάθος κωδικός
        st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
        st.error("❌ Λάθος κωδικός. Προσπαθήστε ξανά.")
        return False
    else:
        # Σωστός κωδικός
        return True

if not check_password():
    st.stop()  # Σταματάει την εκτέλεση της εφαρμογής εδώ αν δεν είναι σωστός ο κωδικός

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
st.sidebar.image("https://cabclub.gr/wp-content/uploads/2021/12/logo.png", use_container_width=True)
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "📝 Νέα Συνταγή", "📊 Διαχείριση", "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "🛒 Παραγγελίες", "🌐 Shop Sync", "📦 Lot Παραγωγής", "📈 Dashboard"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ (ΕΝΗΜΕΡΩΜΕΝΗ ΜΕ ΒΑΡΟΣ ΓΙΑ ΑΝΑΓΩΓΗ) ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών & Τιμών")
    
    # Προσθέσαμε τη στήλη "Weight_Full" (Γραμμάρια ανά φιάλη)
    # Αν το df_ing δεν έχει τη στήλη, τη δημιουργούμε με 0
    if "Weight_Full" not in df_ing.columns:
        df_ing["Weight_Full"] = 0.0

    cols_to_show = ["Name", "Price", "Volume", "Weight_Full", "Τιμή/ml", "Αλκοόλ %"]
    
    column_config_ing = {
        "Name": st.column_config.TextColumn("Όνομα Υλικού"),
        "Price": st.column_config.NumberColumn("Τιμή Αγοράς (€)", format="%.2f €"),
        "Volume": st.column_config.NumberColumn("ML Φιάλης (ml)", min_value=1),
        "Weight_Full": st.column_config.NumberColumn("Βάρος Περιεχομένου (g)", help="Πόσο ζυγίζουν τα ML της φιάλης στη ζυγαριά", format="%d g"),
        "Τιμή/ml": st.column_config.NumberColumn("Τιμή/ml", disabled=True, format="%.4f €"),
        "Αλκοόλ %": st.column_config.NumberColumn("Alc %", format="%.1f %%")
    }
    
    # Ο data_editor επιτρέπει πλέον την εισαγωγή των γραμμαρίων
    edited_ing = st.data_editor(
        df_ing[cols_to_show], 
        column_config=column_config_ing, 
        num_rows="dynamic", 
        use_container_width=True
    )
    
    if st.button("💾 Αποθήκευση Υλικών"):
        temp_df = edited_ing.copy()
        
        # Υπολογισμός τιμής ανά ml
        temp_df["Τιμή/ml"] = temp_df["Price"] / temp_df["Volume"].replace(0, 1)
        
        # Συγχώνευση με το υπόλοιπο df (π.χ. απόθεμα) για να μη χαθούν δεδομένα
        # Σιγουρευόμαστε ότι κρατάμε όλες τις απαραίτητες στήλες
        if "Απόθεμα (ml)" in df_ing.columns:
            final_df = temp_df.merge(df_ing[["Name", "Απόθεμα (ml)"]], on="Name", how="left")
            final_df["Απόθεμα (ml)"] = final_df["Απόθεμα (ml)"].fillna(0.0)
        else:
            final_df = temp_df
            
        final_df.to_csv(DB_INGREDIENTS, index=False, encoding='utf-8-sig')
        st.success("✅ Η αποθήκη και οι συντελεστές βάρους ενημερώθηκαν!")
        st.rerun()


# --- 2. ΝΕΑ ΣΥΝΤΑΓΗ (ΒΕΛΤΙΩΜΕΝΗ ΕΚΔΟΣΗ) ---
elif page == "📝 Νέα Συνταγή":
    st.header("📝 Καταχώρηση Νέας Συνταγής")
    
    with st.form("new_recipe_form"):
        # Προσθήκη Barcode και Ονόματος στην ίδια γραμμή
        c_top1, c_top2 = st.columns([1, 2])
        with c_top1: 
            barcode = st.text_input("Barcode (SKU Site)")
        with c_top2: 
            name = st.text_input("Όνομα Cocktail")
            
        cat_price = st.number_input("Τιμή Καταλόγου (€)", min_value=0.0, step=0.10)
        
        st.markdown("---")
        st.subheader("Συστατικά Συνταγής")
        
        recipe_data = {}
        # Δημιουργία των 13 πεδίων για υλικά και ποσότητες
        for i in range(1, 14):
            c1, c2 = st.columns([3, 1])
            with c1: 
                # Χρήση του ing_options που ήδη έχεις ορίσει
                val_ing = st.selectbox(f"Συστατικό {i}", ing_options, key=f"n_s_{i}")
                recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = val_ing if val_ing else "ΚΕΝΟ"
            with c2: 
                recipe_data[f"ML{i}"] = st.number_input(f"ML {i}", min_value=0.0, key=f"n_m_{i}")
        
        if st.form_submit_button("💾 Αποθήκευση Συνταγής"):
            if name:
                # 1. Προετοιμασία της νέας γραμμής
                new_row = {
                    "Barcode": str(barcode).strip(),
                    "Ονομα": name, 
                    "Τιμή Καταλόγου": cat_price, 
                    **recipe_data
                }
                new_df = pd.DataFrame([new_row])
                
                # Ορίζουμε την ακριβή σειρά στηλών που θέλουμε να έχει το CSV μας
                cols_order = ["Barcode", "Ονομα", "Τιμή Καταλόγου"]
                for i in range(1, 14):
                    cols_order.append(f"ΣΥΣΤΑΤΙΚΟ{i}")
                    cols_order.append(f"ML{i}")

                # 2. Φόρτωση και Συγχώνευση
                if os.path.exists(DB_RECIPES):
                    old_df = pd.read_csv(DB_RECIPES)
                    
                    # Διόρθωση στηλών αν το αρχείο είναι παλιό
                    for col in cols_order:
                        if col not in old_df.columns:
                            old_df[col] = "ΚΕΝΟ" if "ΣΥΣΤΑΤΙΚΟ" in col else 0.0
                    
                    # Εξασφάλιση ότι το Barcode είναι string για τη σύγκριση
                    old_df["Barcode"] = old_df["Barcode"].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
                    
                    # Ένωση
                    combined_df = pd.concat([old_df, new_df], ignore_index=True)
                else:
                    combined_df = new_df

                # 3. Τελική Τακτοποίηση στηλών και αφαίρεση διπλοτύπων
                combined_df = combined_df.reindex(columns=cols_order)
                combined_df = combined_df.drop_duplicates(subset=["Barcode", "Ονομα"], keep="last")
                
                # 4. Αποθήκευση με σωστό Encoding για Ελληνικά
                combined_df.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                
                st.success(f"✅ Το Cocktail '{name}' αποθηκεύτηκε επιτυχώς!")
                st.rerun()
            else:
                st.error("❌ Παρακαλώ εισάγετε το όνομα του Cocktail.")

# --- 5. ΔΙΑΧΕΙΡΙΣΗ ΣΥΝΤΑΓΩΝ (ΒΕΛΤΙΩΜΕΝΗ ΕΚΔΟΣΗ) ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία & Διαγραφή Συνταγών")
    
    # Σιγουρευόμαστε ότι έχουμε τα τελευταία δεδομένα
    if os.path.exists(DB_RECIPES):
        df_rec = pd.read_csv(DB_RECIPES)
    
    if not df_rec.empty:
        # Διασφάλιση σωστού format για τα Barcodes
        if "Barcode" not in df_rec.columns:
            df_rec.insert(0, "Barcode", "")
        df_rec["Barcode"] = df_rec["Barcode"].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
        
        # 1. Επιλογή Cocktail
        recipe_to_edit = st.selectbox(
            "Αναζήτηση Cocktail:", 
            options=df_rec["Ονομα"].unique(),
            index=None,
            placeholder="Επιλέξτε ένα Cocktail..."
        )
        
        if recipe_to_edit:
            # Φέρνουμε τη γραμμή της συγκεκριμένης συνταγής
            row = df_rec[df_rec["Ονομα"] == recipe_to_edit].iloc[0]
            
            # Χωρισμός σε Tabs: Επεξεργασία και Διαγραφή
            tab_edit, tab_del = st.tabs(["📝 Επεξεργασία Στοιχείων", "🗑️ Διαγραφή Συνταγής"])
            
            with tab_edit:
                with st.form(f"form_{recipe_to_edit}"): # Μοναδικό ID φόρμας
                    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                    edit_name = col_h1.text_input("Όνομα Cocktail", value=str(row["Ονομα"]))
                    edit_barcode = col_h2.text_input("Barcode Shop", value=str(row["Barcode"]))
                    current_price = float(row["Τιμή Καταλόγου"]) if "Τιμή Καταλόγου" in row else 0.0
                    edit_price = col_h3.number_input("Τιμή (€)", value=current_price, step=0.10)
                    
                    st.write("---")
                    new_recipe_data = {}
                    c1, c2 = st.columns(2)
                    
                    # Καθαρισμός λίστας επιλογών για σύγκριση
                    clean_options = [str(opt).strip() for opt in ing_options]
                    
                    for i in range(1, 14):
                        target_col = c1 if i <= 7 else c2
                        with target_col:
                            # Παίρνουμε την τιμή από το CSV και καθαρίζουμε κενά
                            val_from_db = str(row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                            ml_from_db = float(row.get(f"ML{i}", 0.0))
                            
                            # Εύρεση σωστού index (αν δεν υπάρχει, πάει στο 0 -> ΚΕΝΟ)
                            try:
                                current_idx = clean_options.index(val_from_db)
                            except ValueError:
                                current_idx = 0
                            
                            sub_c1, sub_c2 = st.columns([2, 1])
                            
                            # Χρήση δυναμικού key (recipe_to_edit) για να ανανεώνονται τα πεδία
                            new_recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = sub_c1.selectbox(
                                f"Υλικό {i}", 
                                options=ing_options, 
                                index=current_idx, 
                                key=f"s_{i}_{recipe_to_edit}"
                            )
                            new_recipe_data[f"ML{i}"] = sub_c2.number_input(
                                f"ML {i}", 
                                value=ml_from_db, 
                                key=f"m_{i}_{recipe_to_edit}"
                            )

                    if st.form_submit_button("💾 Αποθήκευση Αλλαγών"):
                        idx_to_update = df_rec[df_rec["Ονομα"] == recipe_to_edit].index
                        df_rec.loc[idx_to_update, "Ονομα"] = edit_name
                        df_rec.loc[idx_to_update, "Barcode"] = edit_barcode
                        df_rec.loc[idx_to_update, "Τιμή Καταλόγου"] = edit_price
                        for k, v in new_recipe_data.items():
                            df_rec.loc[idx_to_update, k] = v
                        
                        df_rec.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                        st.success(f"✅ Η συνταγή '{edit_name}' ενημερώθηκε!")
                        st.rerun()

            with tab_del:
                st.warning(f"⚠️ Είστε σίγουροι ότι θέλετε να διαγράψετε το **{recipe_to_edit}**; Αυτή η ενέργεια δεν αναιρείται.")
                if st.button(f"🗑️ Οριστική Διαγραφή {recipe_to_edit}", key=f"del_{recipe_to_edit}"):
                    df_rec = df_rec[df_rec["Ονομα"] != recipe_to_edit]
                    df_rec.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                    st.error(f"❌ Η συνταγή '{recipe_to_edit}' διαγράφηκε.")
                    st.rerun()

        st.write("---")
        with st.expander("📋 Προεπισκόπηση Όλων των Συνταγών (Πίνακας)"):
            st.dataframe(df_rec, use_container_width=True)
            
    else:
        st.info("Δεν βρέθηκαν αποθηκευμένες συνταγές. Πηγαίνετε στη 'Νέα Συνταγή' για να ξεκινήσετε.")

# # --- 4. ΑΝΑΛΥΣΗ (ΠΛΗΡΗΣ ΑΠΟΚΑΤΑΣΤΑΣΗ & ΔΙΟΡΘΩΣΗ) ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση & Κερδοφορία")
    
    if not df_rec.empty:
        # Sidebar Ρυθμίσεις
        st.sidebar.subheader("Ρυθμίσεις Ανάλυσης")
        discount = st.sidebar.slider("Έκπτωση Προσφοράς %", 0, 100, 0)
        
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        # Βασικές Τιμές
        p_retail = float(r["Τιμή Καταλόγου"])
        p_agent = p_retail * 0.74
        p_custom = p_retail * (1 - discount/100)
        
        raw_cost, pure_alc_ml, total_ml_cocktail = 0.0, 0.0, 0.0
        breakdown = []
        
        # --- ΣΥΛΛΟΓΗ ΔΕΔΟΜΕΝΩΝ ΣΥΝΤΑΓΗΣ ---
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
            ml = float(r.get(f"ML{i}", 0))
            
            if ing_n != "ΚΕΝΟ" and ml > 0:
                total_ml_cocktail += ml
                if ing_n == "Νερό":
                    breakdown.append({"Υλικό": "Νερό", "ML": ml, "Κόστος": 0.0, "Alc %": 0.0})
                elif ing_n not in ["nan", ""]:
                    match = df_ing[df_ing["Name"] == ing_n]
                    if not match.empty:
                        alc_val = float(match.iloc[0]["Αλκοόλ %"])
                        actual_alc_pct = alc_val if alc_val <= 1 else alc_val / 100
                        pure_alc_ml += (ml * actual_alc_pct)
                        
                        item_cost = ml * float(match.iloc[0]["Τιμή/ml"])
                        raw_cost += item_cost
                        breakdown.append({
                            "Υλικό": ing_n, 
                            "ML": ml, 
                            "Κόστος": item_cost, 
                            "Alc %": actual_alc_pct * 100
                        })

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

        # --- ΕΝΟΤΗΤΑ ΕΞΑΓΩΓΗΣ REPORT (ΜΕ BARCODE) ---
        st.markdown("### 📜 Εξαγωγή Επαγγελματικού Report")
        
        def clean_val(val, decimals=3):
            try:
                return f"{float(val):.{decimals}f}".replace('.', ',')
            except:
                return str(val).replace('.', ',')

        # Εύρεση του Barcode από το dataframe των συνταγών (df_rec)
        try:
            current_barcode = df_rec[df_rec['Ονομα'] == choice]['Barcode'].values[0]
            if not current_barcode or str(current_barcode).lower() == 'nan':
                current_barcode = "Δεν ορίστηκε"
        except:
            current_barcode = "Δεν βρέθηκε"

        # Προετοιμασία δεδομένων CSV
        report_data = [
            ["ΗΜΕΡΟΜΗΝΙΑ REPORT", datetime.now().strftime("%d/%m/%Y %H:%M")],
            ["COCKTAIL", choice],
            ["BARCODE (SKU)", current_barcode], # <--- Η ΝΕΑ ΠΡΟΣΘΗΚΗ
            ["ΣΥΝΟΛΙΚΗ ΠΟΣΟΤΗΤΑ (ML)", clean_val(total_ml_cocktail, 1)],
            ["ΑΛΚΟΟΛΙΚΟΣ ΒΑΘΜΟΣ (ABV) %", clean_val(final_abv, 2)],
            ["ΧΩΡΑ ΦΟΡΟΛΟΓΙΑΣ", country],
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
            ["Τιμή Αντιπροσώπου (26%)", f"{clean_val(p_agent, 2)} €"],
            ["Κέρδος Αντιπροσώπου", f"{clean_val(profit_agent)} €"],
            ["Τιμή με Έκπτωση", f"{clean_val(p_custom, 2)} €"],
            ["Κέρδος με Έκπτωση", f"{clean_val(profit_custom)} €"],
            ["---------------------------", "---------------------------"],
            ["ΑΝΑΛΥΣΗ ΥΛΙΚΩΝ ΑΝΑ ΣΥΣΤΑΤΙΚΟ", ""]
        ]
        
        for item in breakdown:
            val_alc = item.get('Alc %', 0.0)
            report_data.append([
                f"Υλικό: {item['Υλικό']}", 
                f"{clean_val(item['ML'], 1)} ml | {clean_val(val_alc, 1)}% Alc | {clean_val(item['Κόστος'])} €"
            ])

        # Δημιουργία αρχείου
        df_export = pd.DataFrame(report_data, columns=["ΠΕΡΙΓΡΑΦΗ", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ"])
        csv_final = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig')
        
        # ΤΟ ΚΟΥΜΠΙ
        st.info(f"Το report για το '{choice}' είναι έτοιμο με το Barcode: {current_barcode}")
        st.download_button(
            label=f"📥 Λήψη Πλήρους Report: {choice}", 
            data=csv_final, 
            file_name=f"Professional_Report_{choice.replace(' ', '_')}.csv",
            mime="text/csv",
            key="download_report_button"
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
