import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import math
from datetime import datetime
import plotly.express as px
import imaplib
import email
import time
import plotly.graph_objects as go

# 1. Ρύθμιση Σύνδεσης με Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    """Διαβάζει δεδομένα από το Google Sheet"""
    # Το ttl="0" διασφαλίζει ότι φέρνει πάντα τα πιο φρέσκα δεδομένα χωρίς cache
    return conn.read(worksheet=sheet_name, ttl="0")

def save_data(df, sheet_name):
    """Αποθηκεύει το DataFrame πίσω στο Google Sheet"""
    conn.update(worksheet=sheet_name, data=df)
    st.success(f"✅ Το φύλλο {sheet_name} ενημερώθηκε!")

# --- ΔΟΚΙΜΑΣΤΙΚΟ TEST (Πρόσθεσέ το προσωρινά για να δούμε αν δουλεύει) ---
st.title("Test Google Sheets Connection")

try:
    test_df = load_data("Ingredients")
    st.write("Σύνδεση επιτυχής! Να τι βρήκα στο φύλλο Ingredients:")
    st.dataframe(test_df)
except Exception as e:
    st.error(f"Κάτι πήγε στραβά: {e}")

# --- SIDEBAR & REFRESH LOGIC ---
with st.sidebar:
    st.header("⚙️ Διαχείριση")
    if st.button("🔄 Ανανέωση Δεδομένων"):
        # Καθαρίζει όλη τη μνήμη cache της εφαρμογής
        st.cache_data.clear()
        # Επανεκκινεί την εφαρμογή για να διαβάσει τα αρχεία από το Drive
        st.rerun()
    
    st.info("Πατήστε ανανέωση αν ο συνεργάτης σας έκανε αλλαγές στο Excel.")
    st.divider()
    # Στο sidebar, κάτω από το button:
now = datetime.now().strftime("%H:%M:%S") # Αφαίρεσα το ένα .datetime
st.write(f"Τελευταίος έλεγχος: {now}")

# --- ΣΥΣΤΗΜΑ LIVE STATUS ---
def update_live_status(user_name):
    # Γράφει το όνομα και την τρέχουσα ώρα σε ένα αρχείο status.txt
    with open("app_status.txt", "w", encoding="utf-8") as f:
        f.write(f"{user_name}|{time.time()}")

def get_who_is_online():
    if os.path.exists("app_status.txt"):
        with open("app_status.txt", "r", encoding="utf-8") as f:
            data = f.read().split("|")
            if len(data) == 2:
                user, last_time = data[0], float(data[1])
                # Αν η τελευταία ενημέρωση έγινε τα τελευταία 60 δευτερόλεπτα
                if time.time() - last_time < 60:
                    return user
    return None

# Επιλογή χρήστη στο sidebar (για να ξέρει το σύστημα ποιος είναι μέσα)
current_user = st.sidebar.selectbox("👤 Είσαι ο:", ["Χρήστης Α", "Χρήστης Β"])

# Ενημέρωση ότι είσαι ενεργός
update_live_status(current_user)

# Έλεγχος αν είναι ο άλλος μέσα
online_user = get_who_is_online()

# Εμφάνιση ένδειξης στο sidebar
if online_user and online_user != current_user:
    st.sidebar.success(f"🟢 Ο {online_user} είναι online!")
else:
    st.sidebar.info("⚪️ Μόνος στην εφαρμογή")

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
# --- Δυναμικά Paths για να παίζει σε Mac & Windows ταυτόχρονα ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

DB_INGREDIENTS = os.path.join(BASE_PATH, "db_ingredients.csv")
DB_RECIPES = os.path.join(BASE_PATH, "db_recipes.csv")
DB_ORDERS = os.path.join(BASE_PATH, "db_orders.csv")
DB_HISTORY = os.path.join(BASE_PATH, "db_history.csv")

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
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "🔄 Αντικατάσταση","📝 Νέα Συνταγή", "📊 Διαχείριση", "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "🛒 Παραγγελίες", "🌐 Shop Sync", "📦 Lot Παραγωγής", "📈 Dashboard", "🧼 Συντήρηση & HACCP"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ (GOOGLE SHEETS VERSION) ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών (Cloud)")
    
    # 1. ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ ΑΠΟ GOOGLE SHEETS
    df_ing = load_data("Ingredients")
    
    # Εξασφάλιση στηλών (αν το φύλλο είναι άδειο)
    if "ID" not in df_ing.columns:
        df_ing.insert(0, "ID", range(1001, 1001 + len(df_ing)))
    for col in ["Weight_Full", "Αλκοόλ %", "Price", "Volume"]:
        if col not in df_ing.columns: df_ing[col] = 0.0

    tab1, tab2, tab3 = st.tabs(["➕ Νέο Υλικό", "📝 Επεξεργασία / Διόρθωση", "📋 Προβολή Όλων"])

    # --- TAB 1: ΕΙΣΑΓΩΓΗ ΝΕΟΥ ΥΛΙΚΟΥ ---
    with tab1:
        st.subheader("Προσθήκη Νέας Πρώτης ύλης")
        with st.form("add_ing_form", clear_on_submit=True):
            new_name = st.text_input("Όνομα Υλικού (π.χ. Gin Mare)")
            c1, c2, c3 = st.columns(3)
            new_price = c1.number_input("Τιμή Αγοράς (€)", min_value=0.0, step=0.1)
            new_vol = c2.number_input("ML Φιάλης", min_value=1.0, value=700.0)
            new_alc = c3.number_input("Alc %", min_value=0.0, max_value=100.0, step=0.1)
            new_weight = st.number_input("Βάρος Περιεχομένου σε Γραμμάρια (g)", min_value=0.0)
            
            if st.form_submit_button("💾 Αποθήκευση στο Google Sheets"):
                if new_name:
                    max_id = df_ing["ID"].max() if not df_ing.empty else 1000
                    new_row = {
                        "ID": int(max_id) + 1,
                        "Name": new_name,
                        "Price": new_price,
                        "Volume": new_vol,
                        "Weight_Full": new_weight,
                        "Τιμή/ml": new_price / new_vol if new_vol > 0 else 0,
                        "Αλκοόλ %": new_alc,
                        "Απόθεμα (ml)": 0.0
                    }
                    df_ing = pd.concat([df_ing, pd.DataFrame([new_row])], ignore_index=True)
                    df_ing = df_ing.sort_values(by="Name", key=lambda col: col.str.lower())
                    
                    # ΑΠΟΘΗΚΕΥΣΗ ΣΤΟ GOOGLE SHEETS
                    save_data(df_ing, "Ingredients")
                    st.success(f"✅ Το υλικό '{new_name}' προστέθηκε στο Cloud!")
                    st.rerun()

    # --- TAB 2: ΕΠΕΞΕΡΓΑΣΙΑ / ΔΙΑΓΡΑΦΗ ---
    with tab2:
        st.subheader("Διόρθωση ή Διαγραφή Υλικού")
        if not df_ing.empty:
            ing_to_edit = st.selectbox("Επιλέξτε υλικό:", options=df_ing["Name"].unique(), index=None)
            
            if ing_to_edit:
                curr_row = df_ing[df_ing["Name"] == ing_to_edit].iloc[0]
                with st.form("edit_ing_form"):
                    edit_name = st.text_input("Όνομα Υλικού", value=curr_row["Name"])
                    e1, e2, e3 = st.columns(3)
                    edit_price = e1.number_input("Τιμή (€)", value=float(curr_row["Price"]))
                    edit_vol = e2.number_input("ML Φιάλης", value=float(curr_row["Volume"]))
                    edit_alc = e3.number_input("Alc %", value=float(curr_row["Αλκοόλ %"]))
                    edit_weight = st.number_input("Βάρος Περιεχομένου (g)", value=float(curr_row["Weight_Full"]))
                    
                    col_btn1, col_btn2 = st.columns([1,1])
                    
                    if col_btn1.form_submit_button("Update ✅"):
                        # Ενημέρωση τοπικά στο DataFrame
                        idx = df_ing[df_ing["Name"] == ing_to_edit].index
                        df_ing.loc[idx, ["Name", "Price", "Volume", "Αλκοόλ %", "Weight_Full"]] = [edit_name, edit_price, edit_vol, edit_alc, edit_weight]
                        df_ing.loc[idx, "Τιμή/ml"] = edit_price / edit_vol
                        
                        # ΑΠΟΘΗΚΕΥΣΗ ΣΤΟ GOOGLE SHEETS
                        save_data(df_ing, "Ingredients")
                        st.success("✅ Η ενημέρωση ολοκληρώθηκε!")
                        st.rerun()

                    if col_btn2.form_submit_button("Διαγραφή 🗑️"):
                        df_ing = df_ing[df_ing["Name"] != ing_to_edit]
                        save_data(df_ing, "Ingredients")
                        st.warning(f"Το υλικό {ing_to_edit} διαγράφηκε.")
                        st.rerun()

    # --- TAB 3: ΠΡΟΒΟΛΗ ΠΙΝΑΚΑ ---
    with tab3:
        st.subheader("Συνολική Εικόνα Αποθήκης")
        st.dataframe(df_ing, use_container_width=True)


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

                combined_df = combined_df.sort_values(
                    by="Ονομα", 
                    key=lambda col: col.str.lower(), 
                    ascending=True
                )
                
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
        recipe_options = sorted(df_rec["Ονομα"].unique(), key=lambda x: str(x).lower())
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
                        
                        df_rec = df_rec.sort_values(by="Ονομα", key=lambda col: col.str.lower())
                        
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

# --- 4. ΑΝΑΛΥΣΗ (ΔΙΟΡΘΩΜΕΝΗ ΓΙΑ ΣΥΜΒΑΤΟΤΗΤΑ ΜΕ ID & ΟΝΟΜΑΤΑ) ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση & Κερδοφορία")
    df_ing, df_rec, df_orders, df_history = load_data() 
    recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

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

# --- 9. DASHBOARD ---



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

      # ==============================================================================
# 8. LOT ΠΑΡΑΓΩΓΗΣ (ΠΕΛΑΤΗΣ - ΗΜΕΡΟΜΗΝΙΑ ΩΣ LOT - ΙΧΝΗΛΑΣΙΜΟΤΗΤΑ)
# ==============================================================================
elif page == "📦 Lot Παραγωγής":
    st.header("📦 Αναλυτικό Δελτίο Παραγωγής & Ιχνηλασιμότητα")
    
    import glob
    from requests.auth import HTTPBasicAuth
    import requests
    import time

    # --- 1. ΚΕΝΤΡΙΚΟΣ ΟΡΙΣΜΟΣ ΗΜΕΡΟΜΗΝΙΑΣ & LOT ---
    col_date1, col_date2 = st.columns([1, 2])
    selected_date = col_date1.date_input("📅 Ημερομηνία Παραγωγής (LOT)", value=datetime.now(), format="DD/MM/YYYY")
    
    # Το LOT του cocktail βγαίνει αυτόματα από την ημερομηνία (π.χ. 040526)
    date_lot_label = selected_date.strftime('%d%m%y') 
    date_display = selected_date.strftime('%d/%m/%Y')
    current_time = datetime.now().strftime('%H:%M')

    if "auto_cocktails" not in st.session_state:
        st.session_state.auto_cocktails = []
    if "auto_counts" not in st.session_state:
        st.session_state.auto_counts = {}

    # --- 2. ΤΜΗΜΑ ΑΝΑΚΤΗΣΗΣ ΑΠΟ E-SHOP ---
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
                st.error("Αποτυχία σύνδεσης στο e-shop.")
        except Exception as e:
            st.error(f"Σφάλμα: {e}")

    st.divider()
    
    # --- 3. ΦΟΡΜΑ ΠΑΡΑΓΩΓΗΣ ---
    if not df_rec.empty:
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            selected_cocktails = st.multiselect("Επιλέξτε Προϊόντα:", options=df_rec["Ονομα"].unique(), default=st.session_state.auto_cocktails)
        with col_c2:
            customer_name = st.text_input("👤 Πελάτης / Παραγγελία:", value="CabClub E-shop")

        if selected_cocktails:
            st.subheader(f"⚖️ Οδηγίες Ζύγισης (LOT Προϊόντος: {date_lot_label})")
            counts = {}
            c_cols = st.columns(len(selected_cocktails))
            for i, name in enumerate(selected_cocktails):
                val = st.session_state.auto_counts.get(name, 1)
                counts[name] = c_cols[i].number_input(f"Τμχ: {name}", min_value=1, value=int(val), key=f"cnt_{name}")

            lot_entries = []
            with st.form("detailed_lot_form"):
                for cocktail_name in selected_cocktails:
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    bc = str(recipe_row.get("Barcode", ""))
                    st.markdown(f"#### 🏷️ {cocktail_name} | Shop ID: `{bc}`")
                    
                    h = st.columns([2, 1, 1, 1.2, 1.2, 1.2, 1.2])
                    labels = ["Υλικό", "ml", "Βάρος(g)", "Lot Ύλης 1", "Λήξη 1", "Lot Ύλης 2", "Λήξη 2"]
                    for col, label in zip(h, labels): col.caption(label)
                    
                    for i in range(1, 14):
                        ing_name = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        if ing_name in ["ΚΕΝΟ", "nan", "Νερό", ""]: continue
                        
                        ml_unit = recipe_row.get(f"ML{i}", 0.0)
                        total_ml = ml_unit * counts[cocktail_name]
                        target_g = total_ml
                        ing_data = df_ing[df_ing["Name"] == ing_name] if not df_ing.empty else pd.DataFrame()
                        if not ing_data.empty:
                            target_g = (total_ml / ing_data.iloc[0].get("Volume", 700)) * ing_data.iloc[0].get("Weight_Full", 0)

                        r = st.columns([2, 1, 1, 1.2, 1.2, 1.2, 1.2])
                        r[0].write(f"**{ing_name}**")
                        r[1].write(f"{total_ml:.0f}")
                        r[2].markdown(f"**{target_g:.1f}g**")
                        l1 = r[3].text_input("Lot 1", key=f"l1_{cocktail_name}_{i}", label_visibility="collapsed")
                        e1 = r[4].text_input("E1", key=f"e1_{cocktail_name}_{i}", label_visibility="collapsed")
                        l2 = r[5].text_input("Lot 2", key=f"l2_{cocktail_name}_{i}", label_visibility="collapsed")
                        e2 = r[6].text_input("E2", key=f"e2_{cocktail_name}_{i}", label_visibility="collapsed")

                        lot_entries.append({
                            "Ημερομηνία": date_display,
                            "Ώρα": current_time,
                            "Πελάτης": customer_name,
                            "Cocktail": cocktail_name,
                            "LOT_Cocktail": date_lot_label, # ΑΠΟΘΗΚΕΥΕΤΑΙ Η ΗΜΕΡΟΜΗΝΙΑ ΩΣ LOT
                            "Barcode": bc,
                            "Τεμάχια": counts[cocktail_name],
                            "Υλικό": ing_name,
                            "Σύνολο_ML": total_ml,
                            "Στόχος_Γραμμάρια": round(target_g, 1),
                            "Lot Number": l1 if not l2 else f"{l1} / {l2}",
                            "Ημ_Λήξης": e1 if not e2 else f"{e1} / {e2}"
                        })
                
                if st.form_submit_button("💾 Οριστικοποίηση & Αποθήκευση"):
                    if lot_entries:
                        try:
                            csv_file = f"Lot_Report_{selected_date.strftime('%d_%m_%Y')}.csv"
                            new_df = pd.DataFrame(lot_entries)
                            if os.path.exists(csv_file):
                                final_df = pd.concat([pd.read_csv(csv_file), new_df], ignore_index=True)
                            else:
                                final_df = new_df
                            final_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                            st.success(f"✅ Αποθηκεύτηκε! Το LOT του προϊόντος είναι: {date_lot_label}")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα κατά την αποθήκευση: {e}")

    # --- 4. ΙΣΤΟΡΙΚΟ & ΕΚΤΥΠΩΣΗ ---
    st.divider()
    st.subheader("📂 Ιστορικό Παραγωγής & Εκτυπώσεις")
    past_files = glob.glob("Lot_Report_*.csv")
    if past_files:
        all_dates_files = sorted([f.replace("Lot_Report_", "").replace(".csv", "").replace("_", "/") for f in past_files], reverse=True)
        sel_hist_date = st.selectbox("🔍 Επιλέξτε Ημερομηνία Παραγωγής:", all_dates_files)
        
        if sel_hist_date:
            file_path = f"Lot_Report_{sel_hist_date.replace('/', '_')}.csv"
            df_past = pd.read_csv(file_path)
            
            all_custs = ["ΟΛΟΙ"] + sorted(df_past["Πελάτης"].unique().tolist())
            sel_cust = st.selectbox("👤 Φίλτρο Πελάτη (για εκτύπωση):", all_custs)
            
            view_df = df_past if sel_cust == "ΟΛΟΙ" else df_past[df_past["Πελάτης"] == sel_cust]
            st.dataframe(view_df[["Πελάτης", "Cocktail", "LOT_Cocktail", "Ώρα", "Τεμάχια"]].drop_duplicates(), use_container_width=True)
            
            # --- ΕΠΑΓΓΕΛΜΑΤΙΚΟ HTML ΓΙΑ ΕΚΤΥΠΩΣΗ ---
            html = f"""
            <html>
            <head>
                <meta charset='UTF-8'>
                <style>
                    body {{ font-family: 'Helvetica', sans-serif; color: #333; line-height: 1.4; }}
                    .document-header {{ text-align: center; border-bottom: 2px solid #444; padding-bottom: 10px; margin-bottom: 20px; }}
                    .customer-section {{ background-color: #f2f2f2; padding: 10px; border: 1px solid #ccc; margin-top: 20px; border-radius: 5px; }}
                    .cocktail-title {{ color: #d32f2f; border-left: 5px solid #d32f2f; padding-left: 10px; margin: 15px 0 5px 0; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
                    th {{ background-color: #444; color: white; padding: 8px; text-align: left; }}
                    td {{ border: 1px solid #ddd; padding: 6px; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .footer-info {{ margin-top: 30px; font-size: 10px; color: #666; font-style: italic; }}
                    .signature-table {{ width: 100%; margin-top: 40px; border: none; }}
                    .signature-table td {{ border: none; padding: 20px; border-top: 1px solid #333; text-align: center; width: 50%; }}
                    @media print {{
                        .page-break {{ page-break-before: always; }}
                    }}
                </style>
            </head>
            <body>
                <div class='document-header'>
                    <h1>CABCLUB COCKTAILS</h1>
                    <h2>ΔΕΛΤΙΟ ΠΑΡΑΓΩΓΗΣ & ΙΧΝΗΛΑΣΙΜΟΤΗΤΑΣ</h2>
                    <p>Ημερομηνία: <b>{sel_hist_date}</b> | LOT Ημέρας: <b>{df_past['LOT_Cocktail'].iloc[0]}</b></p>
                </div>
            """

            for p in view_df["Πελάτης"].unique():
                p_df = view_df[view_df["Πελάτης"] == p]
                html += f"""
                <div class='customer-section'>
                    <strong>ΠΕΛΑΤΗΣ / ΠΑΡΑΓΓΕΛΙΑ:</strong> {p}
                </div>
                """
                for t in p_df["Ώρα"].unique():
                    t_df = p_df[p_df["Ώρα"] == t]
                    for c in t_df["Cocktail"].unique():
                        c_df = t_df[t_df["Cocktail"] == c]
                        html += f"""
                        <h3 class='cocktail-title'>{c} <small>(ID: {c_df['Barcode'].iloc[0]})</small></h3>
                        <p style='font-size:12px; margin:0;'>Ποσότητα: <b>{c_df['Τεμάχια'].iloc[0]} τμχ</b> | Ώρα Παραγωγής: {t}</p>
                        <table>
                            <thead>
                                <tr>
                                    <th>Πρώτη Ύλη</th>
                                    <th>Σύνολο ml</th>
                                    <th>Βάρος (g)</th>
                                    <th>Lot Number</th>
                                    <th>Ημ. Λήξης</th>
                                </tr>
                            </thead>
                            <tbody>
                        """
                        for _, r in c_df.iterrows():
                            html += f"""
                                <tr>
                                    <td><b>{r['Υλικό']}</b></td>
                                    <td>{r['Σύνολο_ML']}</td>
                                    <td>{r['Στόχος_Γραμμάρια']}g</td>
                                    <td>{r['Lot Number']}</td>
                                    <td>{r['Ημ_Λήξης']}</td>
                                </tr>
                            """
                        html += "</tbody></table>"
                
                # Προσθήκη υπογραφών στο τέλος κάθε σελίδας πελάτη
                html += """
                <table class='signature-table'>
                    <tr>
                        <td>Υπεύθυνος Παραγωγής<br><br>____________________</td>
                        <td>Ποιοτικός Έλεγχος<br><br>____________________</td>
                    </tr>
                </table>
                <div class='page-break'></div>
                """

            html += f"""
                <div class='footer-info'>
                    Εκτύπωση από DC CABCLUB System: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </div>
            </body>
            </html>
            """
            
            st.download_button("🖨️ Εκτύπωση Επαγγελματικού Δελτίου", data=html, file_name=f"Professional_Report_{sel_hist_date.replace('/','_')}.html", mime="text/html")

    # --- 5. ΣΥΝΘΕΤΗ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑ (ΑΝΑΖΗΤΗΣΗ ΣΕ ΟΛΑ) ---
    st.divider()
    st.subheader("🔍 Αναζήτηση Ιχνηλασιμότητας (Φίλτρα)")
    if past_files:
        df_all = pd.concat([pd.read_csv(f) for f in past_files], ignore_index=True)
        with st.expander("⚙️ Σύνθετα Φίλτρα (Πελάτης, Υλικά, Lot)"):
            f1, f2, f3 = st.columns(3)
            search_cust = f1.multiselect("Πελάτης:", sorted(df_all["Πελάτης"].unique()))
            search_cock = f2.multiselect("Cocktail:", sorted(df_all["Cocktail"].unique()))
            search_ing = f3.multiselect("Πρώτη Ύλη:", sorted(df_all["Υλικό"].unique()))
            search_lot = st.text_input("🔢 Αναζήτηση βάσει οποιουδήποτε LOT (Προϊόντος ή Ύλης):", placeholder="π.χ. 040526 ή L123...")

        # --- ΕΦΑΡΜΟΓΗ ΦΙΛΤΡΩΝ ---
        dff = df_all.copy()
        if search_cust: dff = dff[dff["Πελάτης"].isin(search_cust)]
        if search_cock: dff = dff[dff["Cocktail"].isin(search_cock)]
        if search_ing: dff = dff[dff["Υλικό"].isin(search_ing)]
        if search_lot:
            dff = dff[dff.apply(lambda x: search_lot.lower() in str(x).lower(), axis=1)]

        st.write(f"Αποτελέσματα: **{len(dff)}** εγγραφές")
        st.dataframe(dff, use_container_width=True)

        if not dff.empty:
            # --- ΔΗΜΙΟΥΡΓΙΑ ΕΠΑΓΓΕΛΜΑΤΙΚΗΣ ΑΝΑΦΟΡΑΣ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑΣ (HTML) ---
            trace_html = f"""
            <html>
            <head>
                <meta charset='UTF-8'>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; color: #2c3e50; }}
                    .report-header {{ border-bottom: 3px solid #2c3e50; padding-bottom: 10px; margin-bottom: 25px; }}
                    .report-title {{ font-size: 24px; font-weight: bold; color: #2c3e50; margin: 0; }}
                    .filters-used {{ background: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 4px solid #6c757d; margin-bottom: 20px; font-size: 13px; }}
                    table {{ width: 100%; border-collapse: collapse; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }}
                    th {{ background-color: #2c3e50; color: white; padding: 12px 8px; text-align: left; font-size: 13px; text-transform: uppercase; }}
                    td {{ border: 1px solid #dee2e6; padding: 10px 8px; font-size: 12px; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    tr:hover {{ background-color: #e9ecef; }}
                    .badge-lot {{ background: #d32f2f; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold; }}
                    .footer {{ margin-top: 40px; border-top: 1px solid #ccc; padding-top: 10px; font-size: 11px; color: #7f8c8d; }}
                </style>
            </head>
            <body>
                <div class='report-header'>
                    <div class='report-title'>📊 ΑΝΑΦΟΡΑ ΕΛΕΓΧΟΥ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑΣ</div>
                    <div style='font-size: 14px;'>CABCLUB COCKTAILS - Quality Assurance System</div>
                </div>

                <div class='filters-used'>
                    <strong>Κριτήρια Αναζήτησης:</strong><br>
                    Ημερομηνία Εξαγωγής: {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
                    Φίλτρο Lot: {search_lot if search_lot else 'Κανένα'}<br>
                    Πελάτες: {', '.join(search_cust) if search_cust else 'Όλοι'}
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Ημ/νία</th>
                            <th>Πελάτης</th>
                            <th>Cocktail</th>
                            <th>LOT Προϊόντος</th>
                            <th>Υλικό (Πρ. Ύλη)</th>
                            <th>Lot Ύλης</th>
                            <th>Τμχ</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for _, row in dff.iterrows():
                trace_html += f"""
                    <tr>
                        <td>{row['Ημερομηνία']}</td>
                        <td>{row['Πελάτης']}</td>
                        <td><b>{row['Cocktail']}</b></td>
                        <td><span class='badge-lot'>{row['LOT_Cocktail']}</span></td>
                        <td>{row['Υλικό']}</td>
                        <td>{row['Lot Number']}</td>
                        <td>{row['Τεμάχια']}</td>
                    </tr>
                """

            trace_html += """
                    </tbody>
                </table>
                <div class='footer'>
                    Η παρούσα αναφορά παράχθηκε αυτόματα από το σύστημα διαχείρισης παραγωγής της CABCLUB.
                </div>
            </body>
            </html>
            """

            # Δύο επιλογές εξαγωγής: Η παραδοσιακή (CSV) και η νέα (HTML)
            c1, c2 = st.columns(2)
            c1.download_button(
                label="📥 Εξαγωγή Επαγγελματικής Αναφοράς (HTML)",
                data=trace_html,
                file_name=f"Traceability_Report_{datetime.now().strftime('%d_%m_%y')}.html",
                mime="text/html"
            )
            c2.download_button(
                label="📊 Εξαγωγή Raw Data (CSV)",
                data=dff.to_csv(index=False, encoding="utf-8-sig"),
                file_name="Trace_Data.csv",
                mime="text/csv"
            )
            # --- 6. ΕΚΤΥΠΩΣΗ ΠΛΗΡΟΥΣ ΙΣΤΟΡΙΚΟΥ (ΧΩΡΙΣ ΦΙΛΤΡΑ) ---
        st.divider()
        st.subheader("📊 Γενικό Αρχείο Παραγωγής")
        st.info("Εδώ μπορείτε να εκτυπώσετε ολόκληρο το ιστορικό παραγωγής από την πρώτη μέρα λειτουργίας.")

        if st.button("📑 Προετοιμασία Πλήρους Ιστορικού για Εκτύπωση"):
            # Φορτώνουμε όλα τα αρχεία
            all_files = glob.glob("Lot_Report_*.csv")
            if all_files:
                # Ένωση όλων των CSV σε ένα DataFrame
                df_full_hist = pd.concat([pd.read_csv(f, dtype={"LOT_Cocktail": str}) for f in all_files], ignore_index=True)
                
                # Ταξινόμηση ανά ημερομηνία (νεότερα πάνω)
                df_full_hist['temp_date'] = pd.to_datetime(df_full_hist['Ημερομηνία'], format='%d/%m/%Y')
                df_full_hist = df_full_hist.sort_values(by='temp_date', ascending=False)

                # Δημιουργία HTML
                full_html = f"""
                <html>
                <head>
                    <meta charset='UTF-8'>
                    <style>
                        body {{ font-family: 'Helvetica', sans-serif; padding: 20px; }}
                        h1 {{ text-align: center; color: #2c3e50; border-bottom: 3px solid #2c3e50; }}
                        .summary {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #dee2e6; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                        th {{ background-color: #2c3e50; color: white; padding: 10px; font-size: 12px; text-transform: uppercase; }}
                        td {{ border: 1px solid #ddd; padding: 8px; font-size: 11px; }}
                        tr:nth-child(even) {{ background-color: #f2f2f2; }}
                        .badge-lot {{ background: #d32f2f; color: white; padding: 2px 5px; border-radius: 3px; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <h1>ΚΑΤΑΣΤΑΣΗ ΟΛΙΚΗΣ ΠΑΡΑΓΩΓΗΣ - CABCLUB</h1>
                    <div class='summary'>
                        Συνολικές Εγγραφές: <b>{len(df_full_hist)}</b><br>
                        Ημερομηνία Εξαγωγής: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Ημ/νία</th>
                                <th>Πελάτης</th>
                                <th>Cocktail</th>
                                <th>LOT</th>
                                <th>Υλικό</th>
                                <th>Lot Ύλης</th>
                                <th>Τμχ</th>
                            </tr>
                        </thead>
                        <tbody>
                """

                for _, row in df_full_hist.iterrows():
                    full_html += f"""
                        <tr>
                            <td>{row['Ημερομηνία']}</td>
                            <td>{row['Πελάτης']}</td>
                            <td><b>{row['Cocktail']}</b></td>
                            <td><span class='badge-lot'>{row['LOT_Cocktail']}</span></td>
                            <td>{row['Υλικό']}</td>
                            <td>{row['Lot Number']}</td>
                            <td>{row['Τεμάχια']}</td>
                        </tr>
                    """

                full_html += "</tbody></table></body></html>"

                # Εμφάνιση κουμπιού λήψης
                st.download_button(
                    label="📥 Λήψη Πλήρους Ιστορικού (HTML)",
                    data=full_html,
                    file_name=f"Full_Production_History_{datetime.now().strftime('%d_%m_%y')}.html",
                    mime="text/html"
                )
            else:
                st.warning("Δεν βρέθηκαν αρχεία παραγωγής.")


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

            # ==============================================================================
# 9. ΣΥΝΤΗΡΗΣΗ & HACCP
# ==============================================================================
elif page == "🧼 Συντήρηση & HACCP":
    st.header("🧼 Ημερολόγιο Συντήρησης & Καθαρισμού")
    
    tab1, tab2 = st.tabs(["🌡️ Θερμοκρασίες", "🧹 Checklist Καθαρισμού"])
    
    # --- TAB 1: ΘΕΡΜΟΚΡΑΣΙΕΣ ---
    with tab1:
        st.subheader("Καταγραφή Θερμοκρασίας Ψυγείων")
        with st.form("temp_form"):
            col_t1, col_t2 = st.columns(2)
            fridge_id = col_t1.selectbox("Ψυγείο:", ["Ψυγείο Α (Πρώτες Ύλες)", "Ψυγείο Β (Έτοιμα Product)"])
            temp_value = col_t2.number_input("Θερμοκρασία (°C):", min_value=-20.0, max_value=20.0, value=4.0, step=0.5)
            notes = st.text_input("Σημειώσεις (π.χ. Έλεγχος λάστιχων):")
            
            if st.form_submit_button("💾 Καταγραφή Θερμοκρασίας"):
                log_data = {
                    "Ημερομηνία": datetime.now().strftime("%d/%m/%Y"),
                    "Ώρα": datetime.now().strftime("%H:%M"),
                    "Χρήστης": current_user, # Χρησιμοποιεί το όνομα που επιλέξατε στο sidebar
                    "Τύπος": "Θερμοκρασία",
                    "Στοιχείο": fridge_id,
                    "Τιμή": f"{temp_value} °C",
                    "Σημειώσεις": notes
                }
                # Αποθήκευση σε CSV
                haccp_file = "HACCP_Log.csv"
                new_row = pd.DataFrame([log_data])
                if not os.path.exists(haccp_file):
                    new_row.to_csv(haccp_file, index=False, encoding='utf-8-sig')
                else:
                    new_row.to_csv(haccp_file, mode='a', header=False, index=False, encoding='utf-8-sig')
                st.success("✅ Η θερμοκρασία καταγράφηκε!")

    # --- TAB 2: ΚΑΘΑΡΙΣΜΟΣ ---
    with tab2:
        st.subheader("Ημερήσιο Checklist Καθαρισμού")
        with st.form("cleaning_form"):
            c1 = st.checkbox("Καθαρισμός & Απολύμανση Πάγκων")
            c2 = st.checkbox("Πλύσιμο Εργαλείων (Shakers, Μεζούρες)")
            c3 = st.checkbox("Καθαρισμός Δαπέδου")
            c4 = st.checkbox("Απομάκρυνση Απορριμμάτων")
            
            if st.form_submit_button("💾 Οριστικοποίηση Καθαρισμού"):
                if c1 and c2 and c3 and c4:
                    log_data = {
                        "Ημερομηνία": datetime.now().strftime("%d/%m/%Y"),
                        "Ώρα": datetime.now().strftime("%H:%M"),
                        "Χρήστης": current_user,
                        "Τύπος": "Καθαρισμός",
                        "Στοιχείο": "Γενικό Checklist",
                        "Τιμή": "ΟΛΟΚΛΗΡΩΘΗΚΕ",
                        "Σημειώσεις": "Όλες οι εργασίες εκτελέστηκαν"
                    }
                    pd.DataFrame([log_data]).to_csv("HACCP_Log.csv", mode='a', header=False, index=False, encoding='utf-8-sig')
                    st.success("✨ Ο καθαρισμός επιβεβαιώθηκε!")
                else:
                    st.warning("⚠️ Πρέπει να ολοκληρώσετε όλες τις εργασίες για να γίνει η καταγραφή.")

    # --- ΠΡΟΒΟΛΗ ΙΣΤΟΡΙΚΟΥ & ΕΠΑΓΓΕΛΜΑΤΙΚΗ ΕΞΑΓΩΓΗ ---
    st.divider()
    if os.path.exists("HACCP_Log.csv"):
        st.subheader("📂 Αρχείο Καταγραφών HACCP")
        df_haccp = pd.read_csv("HACCP_Log.csv")
        
        # Φίλτρο για να διαλέγεις τι θα εξάγεις
        log_view = st.dataframe(df_haccp.sort_values(by=["Ημερομηνία", "Ώρα"], ascending=False), use_container_width=True)
        
        # --- ΔΗΜΙΟΥΡΓΙΑ ΕΠΑΓΓΕΛΜΑΤΙΚΟΥ HTML REPORT ---
        report_date = datetime.now().strftime("%d/%m/%Y")
        
        html_style = """
        <style>
            body { font-family: 'Helvetica', sans-serif; color: #333; line-height: 1.6; }
            .header { text-align: center; border-bottom: 3px solid #1e1e1e; padding-bottom: 10px; margin-bottom: 20px; }
            .header h1 { margin: 0; color: #1e1e1e; letter-spacing: 2px; }
            .info-table { width: 100%; margin-bottom: 20px; font-size: 14px; }
            .data-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            .data-table th { background-color: #f2f2f2; border: 1px solid #ddd; padding: 12px; text-align: left; font-size: 13px; }
            .data-table td { border: 1px solid #ddd; padding: 10px; font-size: 12px; }
            .footer { margin-top: 50px; font-size: 10px; text-align: center; color: #777; border-top: 1px solid #ddd; padding-top: 10px; }
            .badge-temp { background-color: #e3f2fd; color: #0d47a1; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
            .badge-clean { background-color: #e8f5e9; color: #1b5e20; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
        </style>
        """
        
        html_content = f"""
        <html>
        <head><meta charset='UTF-8'>{html_style}</head>
        <body>
            <div class='header'>
                <h1>CABCLUB COCKTAILS</h1>
                <p>ΜΗΤΡΩΟ HACCP & ΥΓΙΕΙΝΗΣ</p>
            </div>
            
            <table class='info-table'>
                <tr>
                    <td><strong>Ημερομηνία Έκδοσης:</strong> {report_date}</td>
                    <td style='text-align:right;'><strong>Υπεύθυνος Μονάδας:</strong> CabClub Team</td>
                </tr>
            </table>

            <table class='data-table'>
                <thead>
                    <tr>
                        <th>Ημερομηνία</th>
                        <th>Ώρα</th>
                        <th>Χρήστης</th>
                        <th>Τύπος Ελέγχου</th>
                        <th>Στοιχείο / Χώρος</th>
                        <th>Αποτέλεσμα</th>
                        <th>Σημειώσεις</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Προσθήκη γραμμών από το DataFrame
        for _, row in df_haccp.iterrows():
            badge_class = "badge-temp" if row['Τύπος'] == "Θερμοκρασία" else "badge-clean"
            html_content += f"""
                <tr>
                    <td>{row['Ημερομηνία']}</td>
                    <td>{row['Ώρα']}</td>
                    <td>{row['Χρήστης']}</td>
                    <td><span class='{badge_class}'>{row['Τύπος']}</span></td>
                    <td>{row['Στοιχείο']}</td>
                    <td><strong>{row['Τιμή']}</strong></td>
                    <td>{row['Σημειώσεις'] if pd.notna(row['Σημειώσεις']) else '-'}</td>
                </tr>
            """
            
        html_content += """
                </tbody>
            </table>
            
            <div class='footer'>
                <p>Το παρόν έγγραφο αποτελεί επίσημο αρχείο της επιχείρησης CabClub Cocktails.<br>
                Εξήχθη αυτόματα μέσω του CabClub Production Management System.</p>
            </div>
        </body>
        </html>
        """
        
        # Κουμπί Λήψης
        st.download_button(
            label="📑 Λήψη Επίσημης Αναφοράς HACCP (HTML)",
            data=html_content,
            file_name=f"HACCP_Report_{datetime.now().strftime('%d_%m_%Y')}.html",
            mime="text/html"
        )
