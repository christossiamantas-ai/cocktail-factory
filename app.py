import streamlit as st
import pandas as pd
import os
import math
import time
from datetime import datetime
import plotly.express as px
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. ΡΥΘΜΙΣΕΙΣ & ΣΥΝΔΕΣΗ DRIVE
# ==========================================
FOLDER_ID = "1KSpn-eyT_B-7lTdjAerWHyxrl5zeBtar" 
SERVICE_ACCOUNT_FILE = 'service_account.json'

def get_gdrive_service():
    """Σύνδεση με το Google Drive API"""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        st.error(f"Το αρχείο {SERVICE_ACCOUNT_FILE} λείπει!")
        return None
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def sync_to_drive(file_path):
    """Ανεβάζει το τοπικό CSV στο Drive"""
    try:
        service = get_gdrive_service()
        if not service: return False
        file_name = os.path.basename(file_path)
        query = f"name = '{file_name}' and '{FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        media = MediaFileUpload(file_path, mimetype='text/csv')
        if files:
            service.files().update(fileId=files[0]['id'], media_body=media).execute()
        else:
            meta = {'name': file_name, 'parents': [FOLDER_ID]}
            service.files().create(body=meta, media_body=media).execute()
        st.toast(f"✅ Συγχρονίστηκε: {file_name}")
        return True
    except Exception as e:
        st.warning(f"⚠️ Σφάλμα Sync: {e}")
        return False

def download_from_drive(file_path):
    """Κατεβάζει το CSV από το Drive στο Streamlit"""
    try:
        service = get_gdrive_service()
        if not service: return False
        file_name = os.path.basename(file_path)
        query = f"name = '{file_name}' and '{FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        if files:
            request = service.files().get_media(fileId=files[0]['id'])
            with open(file_path, "wb") as f:
                f.write(request.execute())
            return True
        return False
    except Exception:
        return False

# ==========================================
# 2. ΡΥΘΜΙΣΕΙΣ ΣΕΛΙΔΑΣ & PATHS
# ==========================================
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DB_INGREDIENTS = os.path.join(BASE_PATH, "db_ingredients.csv")
DB_RECIPES = os.path.join(BASE_PATH, "db_recipes.csv")
DB_ORDERS = os.path.join(BASE_PATH, "db_orders.csv")
DB_HISTORY = os.path.join(BASE_PATH, "db_history.csv")

# ΑΥΤΟΜΑΤΟ ΚΑΤΕΒΑΣΜΑ ΜΕ ΤΟ ΠΟΥ ΑΝΟΙΓΕΙ Η ΕΦΑΡΜΟΓΗ
if 'init_done' not in st.session_state:
    with st.spinner("🔄 Φόρτωση δεδομένων από το Cloud..."):
        download_from_drive(DB_INGREDIENTS)
        download_from_drive(DB_RECIPES)
        download_from_drive(DB_ORDERS)
        download_from_drive(DB_HISTORY)
        download_from_drive("HACCP_Log.csv")
        st.session_state['init_done'] = True
        st.rerun()

# ==========================================
# 3. ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ (LOAD)
# ==========================================
def load_data():
    ing = pd.read_csv(DB_INGREDIENTS) if os.path.exists(DB_INGREDIENTS) else pd.DataFrame(columns=["ID", "Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Απόθεμα (ml)", "Weight_Full"])
    rec = pd.read_csv(DB_RECIPES) if os.path.exists(DB_RECIPES) else pd.DataFrame(columns=["Barcode", "Ονομα", "Τιμή Καταλόγου"])
    orders = pd.read_csv(DB_ORDERS) if os.path.exists(DB_ORDERS) else pd.DataFrame(columns=["Πελάτης", "Cocktail", "Τεμάχια"])
    return ing, rec, orders

df_ing, df_rec, df_orders = load_data()

# --- ΣΥΣΤΗΜΑ LIVE STATUS ---
def update_live_status(user_name):
    with open("app_status.txt", "w", encoding="utf-8") as f:
        f.write(f"{user_name}|{time.time()}")

def get_who_is_online():
    if os.path.exists("app_status.txt"):
        with open("app_status.txt", "r", encoding="utf-8") as f:
            data = f.read().split("|")
            if len(data) == 2:
                user, last_time = data[0], float(data[1])
                if time.time() - last_time < 60:
                    return user
    return None

current_user = st.sidebar.selectbox("👤 Είσαι ο:", ["Χρήστης Α", "Χρήστης Β"])
update_live_status(current_user)
online_user = get_who_is_online()

if online_user and online_user != current_user:
    st.sidebar.success(f"🟢 Ο {online_user} είναι online!")
else:
    st.sidebar.info("⚪️ Μόνος στην εφαρμογή")

st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

def check_password():
    """Επιστρέφει True αν ο χρήστης έδωσε σωστό κωδικό."""
    def password_entered():
        if st.session_state["password"] == "panatha1908":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Εισάγετε τον Κωδικό Πρόσβασης", type="password", on_change=password_entered, key="password")
        st.error("❌ Λάθος κωδικός. Προσπαθήστε ξανά.")
        return False
    else:
        return True

if not check_password():
    st.stop()

st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00ffcc;
    }
    div[data-testid="stMetric"] {
        background-color: #1e2129;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }
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

st.sidebar.image("https://cabclub.gr/wp-content/uploads/2021/12/logo.png", use_container_width=True)
st.sidebar.title("DC CABCLUB 2026 🏆")
page = st.sidebar.radio("Μενού:", ["📦 Αποθήκη", "🔄 Αντικατάσταση","📝 Νέα Συνταγή", "📊 Διαχείριση", "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "🛒 Παραγγελίες", "📈 Dashboard", "🌐 Shop Sync", "📦 Lot Παραγωγής", "🧼 Συντήρηση & HACCP"])
country = st.sidebar.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()))
tax_factor = TAX_RATES[country]

# --- 1. ΑΠΟΘΗΚΗ ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών")
    
    if "ID" not in df_ing.columns:
        df_ing.insert(0, "ID", range(1001, 1001 + len(df_ing)))
    for col in ["Weight_Full", "Αλκοόλ %", "Price", "Volume"]:
        if col not in df_ing.columns: df_ing[col] = 0.0

    tab1, tab2, tab3 = st.tabs(["➕ Νέο Υλικό", "📝 Επεξεργασία / Διόρθωση", "📋 Προβολή Όλων"])

    with tab1:
        st.subheader("Προσθήκη Νέας Πρώτης ύλης")
        with st.form("add_ing_form", clear_on_submit=True):
            new_name = st.text_input("Όνομα Υλικού (π.χ. Gin Mare)")
            c1, c2, c3 = st.columns(3)
            new_price = c1.number_input("Τιμή Αγοράς (€)", min_value=0.0, step=0.1)
            new_vol = c2.number_input("ML Φιάλης", min_value=1.0, value=700.0)
            new_alc = c3.number_input("Alc %", min_value=0.0, max_value=100.0, step=0.1)
            new_weight = st.number_input("Βάρος Περιεχομένου σε Γραμμάρια (g)", min_value=0.0)
            
            if st.form_submit_button("💾 Αποθήκευση Νέου Υλικού"):
                if new_name:
                    max_id = df_ing["ID"].max() if not df_ing.empty else 1000
                    new_row = {
                        "ID": int(max_id) + 1, "Name": new_name, "Price": new_price,
                        "Volume": new_vol, "Weight_Full": new_weight,
                        "Τιμή/ml": new_price / new_vol, "Αλκοόλ %": new_alc, "Απόθεμα (ml)": 0.0
                    }
                    df_ing = pd.concat([df_ing, pd.DataFrame([new_row])], ignore_index=True)
                    df_ing = df_ing.sort_values(by="Name", key=lambda col: col.str.lower())
                    
                    df_ing.to_csv(DB_INGREDIENTS, index=False, encoding='utf-8-sig')
                    
                    if sync_to_drive(DB_INGREDIENTS):
                        st.success(f"✅ Το υλικό '{new_name}' αποθηκεύτηκε και συγχρονίστηκε!")
                    st.rerun()
                else:
                    st.error("Παρακαλώ δώστε όνομα στο υλικό.")

    with tab2:
        st.subheader("Διόρθωση ή Διαγραφή Υλικού")
        if not df_ing.empty:
            ing_to_edit = st.selectbox("Επιλέξτε υλικό για επεξεργασία:", options=df_ing["Name"].unique(), index=None)
            
            if ing_to_edit:
                curr_row = df_ing[df_ing["Name"] == ing_to_edit].iloc[0]
                with st.form("edit_ing_form"):
                    edit_name = st.text_input("Όνομα Υλικού", value=curr_row["Name"])
                    e1, e2, e3 = st.columns(3)
                    edit_price = e1.number_input("Τιμή (€)", value=float(curr_row["Price"]), step=0.1)
                    edit_vol = e2.number_input("ML Φιάλης", value=float(curr_row["Volume"]), min_value=1.0)
                    edit_alc = e3.number_input("Alc %", value=float(curr_row["Αλκοόλ %"]), step=0.1)
                    edit_weight = st.number_input("Βάρος Περιεχομένου (g)", value=float(curr_row["Weight_Full"]))
                    
                    col_btn1, col_btn2 = st.columns([1,1])
                    
                    if col_btn1.form_submit_button("Update ✅"):
                        temp_ing = pd.read_csv(DB_INGREDIENTS)
                        temp_rec = pd.read_csv(DB_RECIPES)
                        old_name = ing_to_edit 
                        
                        idx_ing = temp_ing[temp_ing["Name"] == old_name].index
                        temp_ing.loc[idx_ing, ["Name", "Price", "Volume", "Αλκοόλ %", "Weight_Full"]] = [edit_name, edit_price, edit_vol, edit_alc, edit_weight]
                        temp_ing.loc[idx_ing, "Τιμή/ml"] = edit_price / edit_vol
                        temp_ing.to_csv(DB_INGREDIENTS, index=False, encoding='utf-8-sig')
                        
                        sync_to_drive(DB_INGREDIENTS)

                        if old_name != edit_name:
                            for i in range(1, 14):
                                col = f"ΣΥΣΤΑΤΙΚΟ{i}"
                                if col in temp_rec.columns:
                                    temp_rec[col] = temp_rec[col].astype(str).str.strip()
                                    temp_rec.loc[temp_rec[col] == old_name.strip(), col] = edit_name
                            temp_rec.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                            sync_to_drive(DB_RECIPES)
                            st.info("⚙️ Ενημερώθηκαν αυτόματα και οι συνταγές στο Drive.")

                        st.success(f"✅ Η ενημέρωση ολοκληρώθηκε!")
                        st.rerun()

                    if col_btn2.form_submit_button("Διαγραφή 🗑️"):
                        df_ing = df_ing[df_ing["Name"] != ing_to_edit]
                        df_ing.to_csv(DB_INGREDIENTS, index=False, encoding='utf-8-sig')
                        sync_to_drive(DB_INGREDIENTS)
                        st.warning(f"Το υλικό {ing_to_edit} διαγράφηκε.")
                        st.rerun()

    with tab3:
        st.subheader("Συνολική Εικόνα Αποθήκης")
        st.dataframe(df_ing[["ID", "Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Weight_Full"]], use_container_width=True)

# --- 2. ΝΕΑ ΣΥΝΤΑΓΗ ---
elif page == "📝 Νέα Συνταγή":
    st.header("📝 Καταχώρηση Νέας Συνταγής")
    
    with st.form("new_recipe_form"):
        c_top1, c_top2 = st.columns([1, 2])
        with c_top1: 
            barcode = st.text_input("Barcode (SKU Site)")
        with c_top2: 
            name = st.text_input("Όνομα Cocktail")
            
        cat_price = st.number_input("Τιμή Καταλόγου (€)", min_value=0.0, step=0.10)
        
        st.markdown("---")
        st.subheader("Συστατικά Συνταγής")
        
        recipe_data = {}
        for i in range(1, 14):
            c1, c2 = st.columns([3, 1])
            with c1: 
                val_ing = st.selectbox(f"Συστατικό {i}", ing_options, key=f"n_s_{i}")
                recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = val_ing if val_ing else "ΚΕΝΟ"
            with c2: 
                recipe_data[f"ML{i}"] = st.number_input(f"ML {i}", min_value=0.0, key=f"n_m_{i}")
        
        if st.form_submit_button("💾 Αποθήκευση Συνταγής"):
            if name:
                new_row = {
                    "Barcode": str(barcode).strip(),
                    "Ονομα": name, 
                    "Τιμή Καταλόγου": cat_price, 
                    **recipe_data
                }
                new_df = pd.DataFrame([new_row])
                
                cols_order = ["Barcode", "Ονομα", "Τιμή Καταλόγου"]
                for i in range(1, 14):
                    cols_order.extend([f"ΣΥΣΤΑΤΙΚΟ{i}", f"ML{i}"])

                if os.path.exists(DB_RECIPES):
                    old_df = pd.read_csv(DB_RECIPES)
                    for col in cols_order:
                        if col not in old_df.columns:
                            old_df[col] = "ΚΕΝΟ" if "ΣΥΣΤΑΤΙΚΟ" in col else 0.0
                    combined_df = pd.concat([old_df, new_df], ignore_index=True)
                else:
                    combined_df = new_df

                combined_df = combined_df.reindex(columns=cols_order)
                combined_df = combined_df.drop_duplicates(subset=["Barcode", "Ονομα"], keep="last")
                combined_df = combined_df.sort_values(by="Ονομα", key=lambda col: col.str.lower())
                
                combined_df.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                
                with st.spinner("⏳ Συγχρονισμός με Google Drive..."):
                    if sync_to_drive(DB_RECIPES):
                        st.success(f"✅ Το Cocktail '{name}' αποθηκεύτηκε στο Drive!")
                    else:
                        st.warning("⚠️ Σώθηκε τοπικά, αλλά απέτυχε ο συγχρονισμός cloud.")
                
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Παρακαλώ εισάγετε το όνομα του Cocktail.")

# --- 3. ΔΙΑΧΕΙΡΙΣΗ ΣΥΝΤΑΓΩΝ ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία & Διαγραφή Συνταγών")
    
    if os.path.exists(DB_RECIPES):
        df_rec = pd.read_csv(DB_RECIPES)
    
    if not df_rec.empty:
        if "Barcode" not in df_rec.columns:
            df_rec.insert(0, "Barcode", "")
        df_rec["Barcode"] = df_rec["Barcode"].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
        
        recipe_to_edit = st.selectbox(
            "Αναζήτηση Cocktail:", 
            options=df_rec["Ονομα"].unique(),
            index=None,
            placeholder="Επιλέξτε ένα Cocktail..."
        )
        
        if recipe_to_edit:
            row = df_rec[df_rec["Ονομα"] == recipe_to_edit].iloc[0]
            tab_edit, tab_del = st.tabs(["📝 Επεξεργασία Στοιχείων", "🗑️ Διαγραφή Συνταγής"])
            
            with tab_edit:
                with st.form(f"form_{recipe_to_edit}"):
                    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                    edit_name = col_h1.text_input("Όνομα Cocktail", value=str(row["Ονομα"]))
                    edit_barcode = col_h2.text_input("Barcode Shop", value=str(row["Barcode"]))
                    current_price = float(row["Τιμή Καταλόγου"]) if "Τιμή Καταλόγου" in row else 0.0
                    edit_price = col_h3.number_input("Τιμή (€)", value=current_price, step=0.10)
                    
                    st.write("---")
                    new_recipe_data = {}
                    c1, c2 = st.columns(2)
                    clean_options = [str(opt).strip() for opt in ing_options]
                    
                    for i in range(1, 14):
                        target_col = c1 if i <= 7 else c2
                        with target_col:
                            val_from_db = str(row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                            ml_from_db = float(row.get(f"ML{i}", 0.0))
                            try:
                                current_idx = clean_options.index(val_from_db)
                            except ValueError:
                                current_idx = 0
                            
                            sub_c1, sub_c2 = st.columns([2, 1])
                            new_recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = sub_c1.selectbox(
                                f"Υλικό {i}", options=ing_options, index=current_idx, key=f"s_{i}_{recipe_to_edit}"
                            )
                            new_recipe_data[f"ML{i}"] = sub_c2.number_input(
                                f"ML {i}", value=ml_from_db, key=f"m_{i}_{recipe_to_edit}"
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
                        
                        with st.spinner("⏳ Ενημέρωση στο Google Drive..."):
                            sync_to_drive(DB_RECIPES)
                        
                        st.success(f"✅ Η συνταγή '{edit_name}' ενημερώθηκε!")
                        time.sleep(1)
                        st.rerun()

            with tab_del:
                st.warning(f"⚠️ Διαγραφή του **{recipe_to_edit}**;")
                if st.button(f"🗑️ Οριστική Διαγραφή", key=f"del_{recipe_to_edit}"):
                    df_rec = df_rec[df_rec["Ονομα"] != recipe_to_edit]
                    
                    df_rec.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                    
                    with st.spinner("🗑️ Ενημέρωση Cloud..."):
                        sync_to_drive(DB_RECIPES)
                        
                    st.error(f"❌ Η συνταγή '{recipe_to_edit}' διαγράφηκε.")
                    time.sleep(1)
                    st.rerun()

        st.write("---")
        with st.expander("📋 Προεπισκόπηση"):
            st.dataframe(df_rec, use_container_width=True)
    else:
        st.info("Δεν βρέθηκαν αποθηκευμένες συνταγές.")

# --- 4. ΑΝΑΛΥΣΗ ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση & Κερδοφορία")
    df_ing, df_rec, df_orders, df_history = load_data() 
    recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

    if not df_rec.empty:
        st.sidebar.subheader("Ρυθμίσεις Ανάλυσης")
        discount = st.sidebar.slider("Έκπτωση Προσφοράς %", 0, 100, 0)
        
        choice = st.selectbox("Επιλέξτε Cocktail:", recipe_options)
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        p_retail = float(pd.to_numeric(r.get("Τιμή Καταλόγου", 0), errors='coerce') or 0.0)
        p_agent = p_retail * 0.74
        p_custom = p_retail * (1 - discount/100)
        
        raw_cost, pure_alc_ml, total_ml_cocktail = 0.0, 0.0, 0.0
        breakdown = []
        missing_ingredients = [] 
        
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
            ml = float(pd.to_numeric(r.get(f"ML{i}", 0), errors='coerce') or 0.0)
            
            if ing_n != "ΚΕΝΟ" and ml > 0:
                total_ml_cocktail += ml
                if ing_n == "Νερό":
                    breakdown.append({"Υλικό": "Νερό", "ML": ml, "Κόστος": 0.0, "Alc %": 0.0})
                elif ing_n not in ["nan", ""]:
                    match = df_ing[df_ing["Name"] == ing_n]
                    
                    if not match.empty:
                        ing_row = match.iloc[0]
                        alc_val = float(pd.to_numeric(ing_row.get("Αλκοόλ %", 0), errors='coerce') or 0.0)
                        actual_alc_pct = alc_val if alc_val <= 1 else alc_val / 100
                        pure_alc_ml += (ml * actual_alc_pct)
                        
                        price_ml = float(pd.to_numeric(ing_row.get("Τιμή/ml", 0), errors='coerce') or 0.0)
                        item_cost = ml * price_ml
                        raw_cost += item_cost
                        
                        breakdown.append({
                            "Υλικό": ing_n, 
                            "ML": ml, 
                            "Κόστος": item_cost, 
                            "Alc %": actual_alc_pct * 100
                        })
                    else:
                        missing_ingredients.append(ing_n)
                        breakdown.append({
                            "Υλικό": f"⚠️ {ing_n}", 
                            "ML": ml, 
                            "Κόστος": 0.0, 
                            "Alc %": 0.0
                        })

        if missing_ingredients:
            st.error(f"⚠️ Τα παρακάτω υλικά δεν βρέθηκαν στην Αποθήκη: {', '.join(missing_ingredients)}")

        final_abv = (pure_alc_ml / total_ml_cocktail * 100) if total_ml_cocktail > 0 else 0
        efk_informational = pure_alc_ml * tax_factor
        total_production = raw_cost + TOTAL_FIXED 
        
        profit_retail = p_retail - total_production
        profit_agent = p_agent - total_production
        profit_custom = p_custom - total_production
        margin_retail = (profit_retail / p_retail * 100) if p_retail > 0 else 0

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

        st.markdown("---")
        st.write("### 🍹 Σύνθεση Υλικών")
        df_screen = pd.DataFrame(breakdown)
        if not df_screen.empty:
            df_render = df_screen.copy()
            for col in ["ML", "Alc %", "Κόστος"]:
                if col in df_render.columns:
                    df_render[col] = df_render[col].apply(lambda x: f"{x:.2f}".replace('.', ','))
            st.table(df_render[["Υλικό", "ML", "Alc %", "Κόστος"]])

# --- 5. ΠΑΡΑΓΓΕΛΙΕΣ (ΜΕ ΕΝΣΩΜΑΤΩΣΗ GOOGLE DRIVE SYNC) ---
elif page == "🛒 Παραγγελίες":
    st.header("🛒 Παραγγελίες & Ανάγκες")
    
    df_ing, df_rec, df_orders, df_history = load_data()
    
    col_a, col_b = st.columns([1, 1.3])
    
    with col_a:
        order_config = {
            "Πελάτης": st.column_config.TextColumn("Πελάτης"),
            "Cocktail": st.column_config.SelectboxColumn("Cocktail", options=recipe_options),
            "Τεμάχια": st.column_config.NumberColumn("Τεμάχια", min_value=1)
        }
        
        ed_orders = st.data_editor(df_orders, column_config=order_config, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Αποθήκευση Παραγγελιών"):
            # ✅ ΔΙΟΡΘΩΜΕΝΟ: Προσθήκη sync_to_drive
            ed_orders.to_csv(DB_ORDERS, index=False, encoding='utf-8-sig')
            with st.spinner("⏳ Συγχρονισμός παραγγελιών..."):
                sync_to_drive(DB_ORDERS)
            st.success("✅ Αποθηκεύτηκαν!")
            time.sleep(1)
            st.rerun()

        if st.button("✅ ΟΛΟΚΛΗΡΩΣΗ & ΑΡΧΕΙΟΘΕΤΗΣΗ"):
            if not ed_orders.empty:
                with st.spinner("⏳ Ενημέρωση Cloud..."):
                    new_h = ed_orders.copy()
                    new_h["Ημερομηνία"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                    df_history = pd.concat([df_history, new_h], ignore_index=True)
                    
                    # ✅ Συγχρονισμός Ιστορικού
                    df_history.to_csv(DB_HISTORY, index=False, encoding='utf-8-sig')
                    sync_to_drive(DB_HISTORY)
                    
                    # ✅ Καθαρισμός τρεχουσών
                    empty_orders = pd.DataFrame(columns=["Πελάτης", "Cocktail", "Τεμάχια"])
                    empty_orders.to_csv(DB_ORDERS, index=False, encoding='utf-8-sig')
                    sync_to_drive(DB_ORDERS)
                    
                st.success("✅ Η παραγγελία αρχειοθετήθηκε!")
                time.sleep(1)
                st.rerun()

    with col_b:
        st.subheader("📊 Υπολογισμός Αναγκών")
        if not ed_orders.empty:
            needs = {}
            for _, o in ed_orders.iterrows():
                r_m = df_rec[df_rec["Ονομα"] == o["Cocktail"]]
                if not r_m.empty:
                    for i in range(1, 14):
                        ing = str(r_m.iloc[0].get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        ml_val = r_m.iloc[0].get(f"ML{i}", 0)
                        try:
                            ml = float(ml_val)
                        except:
                            ml = 0.0
                        if ing not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml > 0:
                            needs[ing] = needs.get(ing, 0) + (ml * o["Τεμάχια"])
            
            if needs:
                calc_data = []
                for ing, total_ml in needs.items():
                    ing_info = df_ing[df_ing["Name"] == ing]
                    vol = float(ing_info.iloc[0]["Volume"]) if not ing_info.empty else 700.0
                    calc_data.append({"Υλικό": ing, "Ανάγκη (ml)": total_ml, "Απόθεμα στο Ράφι (ml)": 0.0, "_vol": vol})
                
                df_c = pd.DataFrame(calc_data)
                ed_c = st.data_editor(df_c, column_config={"Ανάγκη (ml)": st.column_config.NumberColumn(disabled=True), "Απόθεμα στο Ράφι (ml)": st.column_config.NumberColumn()}, num_rows="fixed", use_container_width=True)
                
                ed_c["Προς Αγορά (Φιάλες)"] = ed_c.apply(lambda x: math.ceil(max(0, x["Ανάγκη (ml)"] - x["Απόθεμα στο Ράφι (ml)"]) / x["_vol"]) if x["_vol"] > 0 else 0, axis=1)
                st.subheader("📋 Λίστα Αγορών")
                shopping_list = ed_c[ed_c["Προς Αγορά (Φιάλες)"] > 0][["Υλικό", "Προς Αγορά (Φιάλες)"]]
                st.dataframe(shopping_list, use_container_width=True)

# --- 6. ΕΜΠΟΡΙΚΗ ΠΟΛΙΤΙΚΗ ---
elif page == "📊 Εμπορική Πολιτική":
    st.header("📊 Εμπορική Πολιτική & Σύγκριση Σεναρίων")
    st.write("Συγκρίνετε τη στρατηγική Δώρων έναντι της Έκπτωσης % και δείτε την ανάλυση κερδοφορίας.")

    if not df_rec.empty:
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]

        raw_cost = 0.0
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
            ml_val = r.get(f"ML{i}", 0)
            try:
                ml = float(ml_val)
            except:
                ml = 0.0
                
            if ing_n not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml > 0:
                match = df_ing[df_ing["Name"] == ing_n]
                if not match.empty:
                    raw_cost += ml * float(match.iloc[0].get("Τιμή/ml", 0))
        
        unit_cost = raw_cost + TOTAL_FIXED
        p_retail = float(r.get("Τιμή Καταλόγου", 0))
        p_agent_base = p_retail * 0.74  
        normal_profit_per_unit = p_agent_base - unit_cost

        st.divider()

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

        if sA_total_units > 0 or sB_total_units > 0:
            st.divider()
            winner_text = "ΣΕΝΑΡΙΟ Α" if sA_profit > sB_profit else "ΣΕΝΑΡΙΟ Β"
            diff_val = abs(sA_profit - sB_profit)

            html_table = f"""
            <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #444;">
                <table style="width: 100%; border-collapse: collapse; color: white; font-family: sans-serif;">
                    <tr style="background-color: #1a3a5f;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #444;">ΠΕΡΙΓΡΑΦΗ ΑΝΑΛΥΣΗΣ</th>
                        <th style="padding: 12px; text-align: center; border: 1px solid #444;">ΣΕΝΑΡΙΟ Α</th>
                        <th style="padding: 12px; text-align: center; border: 1px solid #444;">ΣΕΝΑΡΙΟ Β</th>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Effective Τιμή/Τμχ</td>
                        <td style="text-align:center; color: #4caf50; border: 1px solid #444;">{sA_effective:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; border: 1px solid #444;">{sB_effective:.2f} €</td>
                    </tr>
                    <tr style="font-weight: bold; background-color: #222;">
                        <td style="padding: 10px; border: 1px solid #444;">ΚΑΘΑΡΟ ΚΕΡΔΟΣ</td>
                        <td style="text-align:center; color: #4caf50; font-size: 1.2em; border: 1px solid #444;">{sA_profit:.2f} €</td>
                        <td style="text-align:center; color: #2196f3; font-size: 1.2em; border: 1px solid #444;">{sB_profit:.2f} €</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #444;">Margin %</td>
                        <td style="text-align:center; border: 1px solid #444;">{sA_margin:.1f}%</td>
                        <td style="text-align:center; border: 1px solid #444;">{sB_margin:.1f}%</td>
                    </tr>
                </table>
                <div style="margin-top: 20px; padding: 15px; background-color: #1b5e20; border-radius: 8px; text-align: center; color: white;">
                    <h2 style="margin:0;">🏆 ΝΙΚΗΤΗΣ: {winner_text}</h2>
                    <p style="margin:5px 0 0 0;">Επιπλέον κέρδος: <b>{diff_val:.2f} €</b></p>
                </div>
            </div>
            """
            st.markdown(html_table, unsafe_allow_html=True)

# --- 7. DASHBOARD ---
elif page == "📈 Dashboard":
    st.header("📈 Στατιστικά Πωλήσεων & Ιστορικό")
    
    df_ing, df_rec, df_orders, df_history = load_data()
    
    if not df_history.empty:
        plot_data = df_history.groupby("Cocktail")["Τεμάχια"].sum().reset_index()
        
        fig = px.bar(
            plot_data, 
            x="Cocktail", 
            y="Τεμάχια",
            title="Συνολικές Πωλήσεις ανά Cocktail", 
            color="Cocktail",
            labels={"Τεμάχια": "Συνολικά Τεμάχια"}
        )
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
            st.warning("⚠️ Προσοχή: Είστε σίγουροι ότι θέλετε να διαγράψετε οριστικά όλο το ιστορικό;")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Ναι, Οριστική Διαγραφή"):
                    with st.spinner("⏳ Ενημέρωση Cloud..."):
                        new_df = pd.DataFrame(columns=["Ημερομηνία", "Πελάτης", "Cocktail", "Τεμάχια"])
                        new_df.to_csv(DB_HISTORY, index=False, encoding='utf-8-sig')
                        sync_to_drive(DB_HISTORY)
                        
                        st.session_state.delete_confirm = False
                        st.success("Το ιστορικό καθαρίστηκε!")
                        st.rerun()
            with c2:
                if st.button("❌ Άκυρο"):
                    st.session_state.delete_confirm = False
                    st.rerun()
    else:
        st.info("Δεν υπάρχουν ακόμα δεδομένα στο ιστορικό.")

# --- 8. SHOP SYNC ---
elif page == "🌐 Shop Sync":
    st.header("🌐 Συγχρονισμός & Ανάλυση Ημέρας (WooCommerce API)")
    st.info("Ενότητα για σύνδεση με WooCommerce - Έρχεται σύντομα!")

# --- 9. LOT ΠΑΡΑΓΩΓΗΣ ---
elif page == "📦 Lot Παραγωγής":
    st.header("📦 Αναλυτικό Δελτίο Παραγωγής & Ιχνηλασιμότητα")
    st.info("Ενότητα για LOT Παραγωγής - Έρχεται σύντομα!")

# --- 10. ΑΝΤΙΚΑΤΑΣΤΑΣΗ ΥΛΙΚΟΥ ---
elif page == "🔄 Αντικατάσταση":
    st.header("🔄 Μαζική Αντικατάσταση Πρώτης Ύλης")
    st.info("Βρείτε σε ποιες συνταγές υπάρχει ένα υλικό και αντικαταστήστε το παντού με ένα νέο.")

    if not df_rec.empty:
        used_ingredients = []
        for i in range(1, 14):
            col_name = f"ΣΥΣΤΑΤΙΚΟ{i}"
            if col_name in df_rec.columns:
                used_ingredients.extend(df_rec[col_name].astype(str).unique())
        
        unique_used = sorted(list(set([ing for ing in used_ingredients if ing not in ["ΚΕΝΟ", "nan", "None", ""]])))
        
        col_src, col_dst = st.columns(2)
        
        with col_src:
            target_ing = st.selectbox("1. Επιλέξτε υλικό προς αντικατάσταση:", options=unique_used)
        
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
                new_ing = st.selectbox("2. Αντικατάσταση με:", options=df_ing["Name"].unique())
            
            st.markdown("---")
            if st.button("🚀 Εκτέλεση Αντικατάστασης ΠΑΝΤΟΥ"):
                temp_recipes = df_rec.copy()
                total_changes = 0
                
                for i in range(1, 14):
                    col = f"ΣΥΣΤΑΤΙΚΟ{i}"
                    mask = temp_recipes[col].astype(str) == target_ing
                    total_changes += mask.sum()
                    temp_recipes.loc[mask, col] = new_ing
                
                temp_recipes.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                
                with st.spinner("⏳ Ενημέρωση Cloud..."):
                    sync_to_drive(DB_RECIPES)
                    
                st.success(f"✅ Επιτυχία! Το '{target_ing}' αντικαταστάθηκε από το '{new_ing}' σε {total_changes} σημεία.")
                st.balloons()
                st.rerun()
        else:
            st.info("Δεν βρέθηκαν συνταγές που να περιέχουν αυτό το υλικό.")

# --- 11. ΣΥΝΤΗΡΗΣΗ & HACCP ---
elif page == "🧼 Συντήρηση & HACCP":
    st.header("🧼 Ημερολόγιο Συντήρησης & Καθαρισμού")

    col_u1, col_u2 = st.columns(2)
    with col_u1:
        staff_name = st.text_input("👤 Ονοματεπώνυμο Υπευθύνου:", placeholder="π.χ. Νίκος Παπαδόπουλος")
    with col_u2:
        selected_date = st.date_input("📅 Ημερομηνία Καταγραφής:", value=datetime.now())
        date_str = selected_date.strftime("%d/%m/%y")
    
    tab1, tab2, tab3 = st.tabs(["🌡️ Θερμοκρασίες", "🧹 Checklist Καθαρισμού", "📄 Εκτυπώσεις & Ιστορικό"])
    
    with tab1:
        st.subheader(f"🌡️ Καταγραφή Θερμοκρασίας ({date_str})")
        with st.form("temp_form"):
            device = st.selectbox("Συσκευή:", ["Ψυγείο 1", "Ψυγείο 2", "Ψυγείο 3", "Κατάψυξη 1", "Κατάψυξη 2"])
            is_freezer = "Κατάψυξη" in device
            temp = st.number_input("Θερμοκρασία (°C):", 
                                   min_value=-25.0 if is_freezer else 0.0, 
                                   max_value=-10.0 if is_freezer else 10.0, 
                                   value=-18.0 if is_freezer else 4.0, step=0.5)
            notes = st.text_input("Σημειώσεις:")
            
            if st.form_submit_button("💾 Καταγραφή"):
                if not staff_name.strip():
                    st.error("⚠️ Παρακαλώ συμπληρώστε το όνομα υπευθύνου!")
                else:
                    log_data = {
                        "Ημερομηνία": date_str, "Ώρα": datetime.now().strftime("%H:%M"),
                        "Χρήστης": staff_name, "Τύπος": "Θερμοκρασία",
                        "Στοιχείο": device, "Τιμή": f"{temp} °C",
                        "Καθαριστικό": "-", "Σημειώσεις": notes
                    }
                    pd.DataFrame([log_data]).to_csv("HACCP_Log.csv", mode='a', header=not os.path.exists("HACCP_Log.csv"), index=False, encoding='utf-8-sig')
                    sync_to_drive("HACCP_Log.csv")
                    st.success(f"✅ Η μέτρηση για το {device} αποθηκεύτηκε!")

    with tab2:
        st.subheader("🧹 Checklist Καθαρισμού")
        st.info("Ενότητα Checklist - Έρχεται σύντομα!")

    with tab3:
        st.subheader("📄 Εκτυπώσεις & Ιστορικό")
        st.info("Ενότητα Εκτυπώσεων - Έρχεται σύντομα!")
