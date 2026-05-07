import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime
import plotly.express as px
import imaplib
import email
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SIDEBAR & REFRESH LOGIC ---
with st.sidebar:
    st.header("⚙️ Διαχείριση")
    if st.button("🔄 Ανανέωση Δεδομένων"):
        st.cache_data.clear()
        st.rerun()
    
    st.info("Πατήστε ανανέωση αν ο συνεργάτης σας έκανε αλλαγές στο Excel.")
    st.divider()

now = datetime.now().strftime("%H:%M:%S")
st.write(f"Τελευταίος έλεγχος: {now}")

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

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

def check_password():
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
    .stApp { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc; }
    div[data-testid="stMetric"] { background-color: #1e2129; border: 1px solid #333; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #3e4451; color: white; border: none; }
    .stButton>button:hover { border: 1px solid #00ffcc; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

TOTAL_FIXED = 0.22  
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

# ==========================================
# GOOGLE SHEETS INTEGRATION
# ==========================================
@st.cache_resource
def init_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("client_secret.json", scope)
    client = gspread.authorize(creds)
    return client.open("CabClub_DB")

try:
    spreadsheet = init_google_sheets()
except Exception as e:
    st.error(f"Σφάλμα σύνδεσης με Google Sheets. Βεβαιωθείτε ότι το client_secret.json υπάρχει και το αρχείο CabClub_DB είναι shared στο Service Account. Λεπτομέρειες: {e}")
    st.stop()

def load_sheet_data(worksheet_name, columns):
    """Φορτώνει δεδομένα από ένα Tab του Google Sheet. Αν δεν υπάρχει ή είναι κενό, επιστρέφει DataFrame με τις δοσμένες στήλες."""
    try:
        sheet = spreadsheet.worksheet(worksheet_name)
        data = sheet.get_all_records()
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame(columns=columns)
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"Το φύλλο '{worksheet_name}' δεν βρέθηκε στο Google Sheet. Θα δημιουργηθεί κατά την πρώτη αποθήκευση.")
        return pd.DataFrame(columns=columns)
    except Exception as e:
        st.error(f"Σφάλμα ανάγνωσης του {worksheet_name}: {e}")
        return pd.DataFrame(columns=columns)

def save_to_sheet(df, worksheet_name):
    """Καθαρίζει το Tab και αποθηκεύει το DataFrame."""
    try:
        df_to_save = df.copy()
        df_to_save = df_to_save.fillna("")
        df_to_save = df_to_save.astype(str)
        df_to_save = df_to_save.replace({"nan": "", "None": "", "<NA>": ""})
        
        try:
            sheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
            
        sheet.clear()
        data = [df_to_save.columns.values.tolist()] + df_to_save.values.tolist()
        # Fallback for updated gspread versions
        try:
            sheet.update(data)
        except TypeError:
            sheet.update(values=data, range_name="A1")
            
    except Exception as e:
        st.error(f"Αποτυχία αποθήκευσης στο '{worksheet_name}': {e}")

# ==========================================
# ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ ΑΠΟ CLOUD
# ==========================================
def load_data():
    ing = load_sheet_data("Ingredients", ["ID", "Name", "Price", "Volume", "Weight_Full", "Τιμή/ml", "Αλκοόλ %", "Απόθεμα (ml)"])
    for col in ["Name", "Price", "Volume", "Weight_Full", "Τιμή/ml", "Αλκοόλ %", "Απόθεμα (ml)"]:
        if col not in ing.columns:
            ing[col] = 0.0 if col != "Name" else "Νέο Υλικό"
            
    cols_rec = ["Barcode", "Ονομα", "Τιμή Καταλόγου"] + [f"ΣΥΣΤΑΤΙΚΟ{i}" for i in range(1,14)] + [f"ML{i}" for i in range(1,14)]
    rec = load_sheet_data("Recipes", cols_rec)
        
    orders = load_sheet_data("Orders", ["Πελάτης", "Cocktail", "Τεμάχια"])
    orders["Πελάτης"] = orders["Πελάτης"].astype(str).replace("nan", "")

    history = load_sheet_data("History", ["Ημερομηνία", "Πελάτης", "Cocktail", "Τεμάχια"])
        
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
            new_weight = st.number_input("Βάρος Περιεχομένου σε Γραμμάρια (g)", min_value=0.0, help="Το βάρος μόνο του υγρού")
            
            if st.form_submit_button("💾 Αποθήκευση Νέου Υλικού"):
                if new_name:
                    max_id = pd.to_numeric(df_ing["ID"], errors="coerce").max() if not df_ing.empty else 1000
                    if pd.isna(max_id): max_id = 1000
                    new_row = {
                        "ID": int(max_id) + 1,
                        "Name": new_name,
                        "Price": new_price,
                        "Volume": new_vol,
                        "Weight_Full": new_weight,
                        "Τιμή/ml": new_price / new_vol,
                        "Αλκοόλ %": new_alc,
                        "Απόθεμα (ml)": 0.0
                    }
                    df_ing = pd.concat([df_ing, pd.DataFrame([new_row])], ignore_index=True)
                    df_ing = df_ing.sort_values(by="Name", key=lambda col: col.str.lower())
                    
                    # Cloud Save
                    save_to_sheet(df_ing, "Ingredients")
                    
                    st.success(f"✅ Το υλικό '{new_name}' προστέθηκε!")
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
                    edit_weight = st.number_input("Βάρος Περιεχομένου (g)", value=float(curr_row.get("Weight_Full", 0)))
                    
                    col_btn1, col_btn2 = st.columns([1,1])
                    
                    if col_btn1.form_submit_button("Update ✅"):
                        temp_ing, temp_rec, _, _ = load_data() # Load fresh from cloud
                        old_name = ing_to_edit 
                        
                        idx_ing = temp_ing[temp_ing["Name"] == old_name].index
                        temp_ing.loc[idx_ing, "Name"] = edit_name
                        temp_ing.loc[idx_ing, "Price"] = edit_price
                        temp_ing.loc[idx_ing, "Volume"] = edit_vol
                        temp_ing.loc[idx_ing, "Αλκοόλ %"] = edit_alc
                        temp_ing.loc[idx_ing, "Weight_Full"] = edit_weight
                        temp_ing.loc[idx_ing, "Τιμή/ml"] = edit_price / edit_vol
                        
                        save_to_sheet(temp_ing, "Ingredients")

                        if old_name != edit_name:
                            changes_made = 0
                            for i in range(1, 14):
                                col = f"ΣΥΣΤΑΤΙΚΟ{i}"
                                if col in temp_rec.columns:
                                    temp_rec[col] = temp_rec[col].astype(str).str.strip()
                                    mask = temp_rec[col] == old_name.strip()
                                    if mask.any():
                                        temp_rec.loc[mask, col] = edit_name
                                        changes_made += 1
                            
                            if changes_made > 0:
                                save_to_sheet(temp_rec, "Recipes")
                                st.info(f"⚙️ Έγινε αυτόματη ενημέρωση σε {changes_made} πεδία συνταγών.")

                        st.success(f"✅ Το υλικό '{edit_name}' ενημερώθηκε!")
                        st.rerun()

                    if col_btn2.form_submit_button("Διαγραφή 🗑️"):
                        df_ing = df_ing[df_ing["Name"] != ing_to_edit]
                        save_to_sheet(df_ing, "Ingredients")
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
        with c_top1: barcode = st.text_input("Barcode (SKU Site)")
        with c_top2: name = st.text_input("Όνομα Cocktail")
            
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
                new_row = {"Barcode": str(barcode).strip(), "Ονομα": name, "Τιμή Καταλόγου": cat_price, **recipe_data}
                new_df = pd.DataFrame([new_row])
                
                cols_order = ["Barcode", "Ονομα", "Τιμή Καταλόγου"]
                for i in range(1, 14):
                    cols_order.append(f"ΣΥΣΤΑΤΙΚΟ{i}")
                    cols_order.append(f"ML{i}")

                # Φόρτωση από Cloud
                _, old_df, _, _ = load_data()
                
                for col in cols_order:
                    if col not in old_df.columns:
                        old_df[col] = "ΚΕΝΟ" if "ΣΥΣΤΑΤΙΚΟ" in col else 0.0
                
                old_df["Barcode"] = old_df["Barcode"].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
                combined_df = pd.concat([old_df, new_df], ignore_index=True)

                combined_df = combined_df.reindex(columns=cols_order)
                combined_df = combined_df.drop_duplicates(subset=["Barcode", "Ονομα"], keep="last")
                combined_df = combined_df.sort_values(by="Ονομα", key=lambda col: col.str.lower(), ascending=True)
                
                # Cloud Save
                save_to_sheet(combined_df, "Recipes")
                
                st.success(f"✅ Το Cocktail '{name}' αποθηκεύτηκε επιτυχώς!")
                st.rerun()
            else:
                st.error("❌ Παρακαλώ εισάγετε το όνομα του Cocktail.")

# --- 5. ΔΙΑΧΕΙΡΙΣΗ ΣΥΝΤΑΓΩΝ ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία & Διαγραφή Συνταγών")
    
    if not df_rec.empty:
        if "Barcode" not in df_rec.columns: df_rec.insert(0, "Barcode", "")
        df_rec["Barcode"] = df_rec["Barcode"].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
        
        recipe_options = sorted(df_rec["Ονομα"].unique(), key=lambda x: str(x).lower())
        recipe_to_edit = st.selectbox("Αναζήτηση Cocktail:", options=df_rec["Ονομα"].unique(), index=None, placeholder="Επιλέξτε ένα Cocktail...")
        
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
                            
                            try: current_idx = clean_options.index(val_from_db)
                            except ValueError: current_idx = 0
                            
                            sub_c1, sub_c2 = st.columns([2, 1])
                            new_recipe_data[f"ΣΥΣΤΑΤΙΚΟ{i}"] = sub_c1.selectbox(f"Υλικό {i}", options=ing_options, index=current_idx, key=f"s_{i}_{recipe_to_edit}")
                            new_recipe_data[f"ML{i}"] = sub_c2.number_input(f"ML {i}", value=ml_from_db, key=f"m_{i}_{recipe_to_edit}")

                    if st.form_submit_button("💾 Αποθήκευση Αλλαγών"):
                        idx_to_update = df_rec[df_rec["Ονομα"] == recipe_to_edit].index
                        df_rec.loc[idx_to_update, "Ονομα"] = edit_name
                        df_rec.loc[idx_to_update, "Barcode"] = edit_barcode
                        df_rec.loc[idx_to_update, "Τιμή Καταλόγου"] = edit_price
                        for k, v in new_recipe_data.items(): df_rec.loc[idx_to_update, k] = v
                        df_rec = df_rec.sort_values(by="Ονομα", key=lambda col: col.str.lower())
                        
                        save_to_sheet(df_rec, "Recipes")
                        st.success(f"✅ Η συνταγή '{edit_name}' ενημερώθηκε!")
                        st.rerun()

            with tab_del:
                st.warning(f"⚠️ Είστε σίγουροι ότι θέλετε να διαγράψετε το **{recipe_to_edit}**; Αυτή η ενέργεια δεν αναιρείται.")
                if st.button(f"🗑️ Οριστική Διαγραφή {recipe_to_edit}", key=f"del_{recipe_to_edit}"):
                    df_rec = df_rec[df_rec["Ονομα"] != recipe_to_edit]
                    save_to_sheet(df_rec, "Recipes")
                    st.error(f"❌ Η συνταγή '{recipe_to_edit}' διαγράφηκε.")
                    st.rerun()

        st.write("---")
        with st.expander("📋 Προεπισκόπηση Όλων των Συνταγών (Πίνακας)"):
            st.dataframe(df_rec, use_container_width=True)
    else:
        st.info("Δεν βρέθηκαν αποθηκευμένες συνταγές. Πηγαίνετε στη 'Νέα Συνταγή' για να ξεκινήσετε.")

# --- 4. ΑΝΑΛΥΣΗ ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση & Κερδοφορία")

    if not df_rec.empty:
        st.sidebar.subheader("Ρυθμίσεις Ανάλυσης")
        discount = st.sidebar.slider("Έκπτωση Προσφοράς %", 0, 100, 0)
        
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]
        
        p_retail = float(r.get("Τιμή Καταλόγου", 0))
        p_agent = p_retail * 0.74
        p_custom = p_retail * (1 - discount/100)
        
        raw_cost, pure_alc_ml, total_ml_cocktail = 0.0, 0.0, 0.0
        breakdown = []
        missing_ingredients = [] 
        
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
            ml = float(r.get(f"ML{i}", 0))
            
            if ing_n != "ΚΕΝΟ" and ml > 0:
                total_ml_cocktail += ml
                if ing_n == "Νερό":
                    breakdown.append({"Υλικό": "Νερό", "ML": ml, "Κόστος": 0.0, "Alc %": 0.0})
                elif ing_n not in ["nan", ""]:
                    match = df_ing[df_ing["Name"] == ing_n]
                    if not match.empty:
                        ing_row = match.iloc[0]
                        alc_val = float(ing_row.get("Αλκοόλ %", 0))
                        actual_alc_pct = alc_val if alc_val <= 1 else alc_val / 100
                        pure_alc_ml += (ml * actual_alc_pct)
                        price_ml = float(ing_row.get("Τιμή/ml", 0))
                        item_cost = ml * price_ml
                        raw_cost += item_cost
                        breakdown.append({"Υλικό": ing_n, "ML": ml, "Κόστος": item_cost, "Alc %": actual_alc_pct * 100})
                    else:
                        missing_ingredients.append(ing_n)
                        breakdown.append({"Υλικό": f"⚠️ {ing_n} (Μη διαθέσιμο)", "ML": ml, "Κόστος": 0.0, "Alc %": 0.0})

        if missing_ingredients:
            st.error(f"⚠️ Τα παρακάτω υλικά της συνταγής δεν βρέθηκαν στην Αποθήκη: {', '.join(missing_ingredients)}")

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
                if col in df_render.columns: df_render[col] = df_render[col].apply(lambda x: f"{x:.2f}".replace('.', ','))
            st.table(df_render[["Υλικό", "ML", "Alc %", "Κόστος"]])

        st.markdown("### 📜 Εξαγωγή Επαγγελματικού Report")
        def clean_val(val, decimals=3):
            try: return f"{float(val):.{decimals}f}".replace('.', ',')
            except: return str(val).replace('.', ',')

        try:
            current_barcode = df_rec[df_rec['Ονομα'] == choice]['Barcode'].values[0]
            if not current_barcode or str(current_barcode).lower() == 'nan': current_barcode = "Δεν ορίστηκε"
        except: current_barcode = "Δεν βρέθηκε"

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
            report_data.append([f"Υλικό: {item['Υλικό']}", f"{clean_val(item['ML'], 1)} ml | {clean_val(val_alc, 1)}% Alc | {clean_val(item['Κόστος'])} €"])

        df_export = pd.DataFrame(report_data, columns=["ΠΕΡΙΓΡΑΦΗ", "ΤΙΜΗ / ΠΟΣΟΤΗΤΑ"])
        csv_final = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig')
        
        st.download_button(label=f"📥 Λήψη Πλήρους Report: {choice}", data=csv_final, file_name=f"Report_{choice.replace(' ', '_')}.csv", mime="text/csv", key="download_report_btn")

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
            save_to_sheet(ed_orders, "Orders")
            st.rerun()

        if st.button("✅ ΟΛΟΚΛΗΡΩΣΗ & ΑΡΧΕΙΟΘΕΤΗΣΗ"):
            if not ed_orders.empty:
                new_h = ed_orders.copy()
                new_h["Ημερομηνία"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                df_history = pd.concat([df_history, new_h], ignore_index=True)
                save_to_sheet(df_history, "History")
                save_to_sheet(pd.DataFrame(columns=["Πελάτης", "Cocktail", "Τεμάχια"]), "Orders")
                st.success("Η παραγγελία μεταφέρθηκε στο ιστορικό (Cloud)!")
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

# --- 6. ΕΜΠΟΡΙΚΗ ΠΟΛΙΤΙΚΗ ---
elif page == "📊 Εμπορική Πολιτική":
    st.header("📊 Εμπορική Πολιτική & Σύγκριση Σεναρίων")
    st.write("Συγκρίνετε τη στρατηγική Δώρων έναντι της Έκπτωσης % και δείτε την ανάλυση κερδοφορίας.")

    if not df_rec.empty:
        choice = st.selectbox("Επιλέξτε Cocktail:", df_rec["Ονομα"].unique())
        r = df_rec[df_rec["Ονομα"] == choice].iloc[0]

        raw_cost = 0.0
        for i in range(1, 14):
            ing_n = str(r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
            ml = float(r.get(f"ML{i}", 0))
            if ing_n not in ["ΚΕΝΟ", "nan", "Νερό", ""] and ml > 0:
                match = df_ing[df_ing["Name"] == ing_n]
                if not match.empty: raw_cost += ml * float(match.iloc[0]["Τιμή/ml"])
        
        unit_cost = raw_cost + TOTAL_FIXED
        p_retail = float(r["Τιμή Καταλόγου"])
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
                    <tr><td style="padding: 10px; border: 1px solid #444;">Κανονική Τιμή Αντιπρ.</td><td style="text-align:center; color: #4caf50; border: 1px solid #444;">{0:.2f} €</td><td style="text-align:center; color: #2196f3; border: 1px solid #444;">{0:.2f} €</td></tr>
                    <tr><td style="padding: 10px; border: 1px solid #444;">Effective Τιμή/Τμχ</td><td style="text-align:center; color: #4caf50; border: 1px solid #444;">{1:.2f} €</td><td style="text-align:center; color: #2196f3; border: 1px solid #444;">{2:.2f} €</td></tr>
                    <tr><td style="padding: 10px; border: 1px solid #444;">Συνολικά Έσοδα</td><td style="text-align:center; color: #4caf50; border: 1px solid #444;">{3:.2f} €</td><td style="text-align:center; color: #2196f3; border: 1px solid #444;">{4:.2f} €</td></tr>
                    <tr><td style="padding: 10px; border: 1px solid #444;">Συνολικό Κόστος</td><td style="text-align:center; color: #4caf50; border: 1px solid #444;">{5:.2f} €</td><td style="text-align:center; color: #2196f3; border: 1px solid #444;">{6:.2f} €</td></tr>
                    <tr style="font-weight: bold; background-color: #222;"><td style="padding: 10px; border: 1px solid #444;">ΚΑΘΑΡΟ ΚΕΡΔΟΣ</td><td style="text-align:center; color: #4caf50; font-size: 1.2em; border: 1px solid #444;">{7:.2f} €</td><td style="text-align:center; color: #2196f3; font-size: 1.2em; border: 1px solid #444;">{8:.2f} €</td></tr>
                    <tr style="background-color: #333; font-weight: bold;"><td colspan="3" style="padding: 10px; border: 1px solid #444;">ΔΕΙΚΤΕΣ</td></tr>
                    <tr><td style="padding: 10px; border: 1px solid #444;">Margin %</td><td style="text-align:center; color: #4caf50; border: 1px solid #444;">{9:.1f}%</td><td style="text-align:center; color: #2196f3; border: 1px solid #444;">{10:.1f}%</td></tr>
                    <tr><td style="padding: 10px; border: 1px solid #444;">Markup %</td><td style="text-align:center; color: #4caf50; border: 1px solid #444;">{11:.1f}%</td><td style="text-align:center; color: #2196f3; border: 1px solid #444;">{12:.1f}%</td></tr>
                </table>
                <div style="margin-top: 20px; padding: 15px; background-color: #1b5e20; border-radius: 8px; text-align: center; color: white;">
                    <h2 style="margin:0;">🏆 ΝΙΚΗΤΗΣ: {13}</h2><p style="margin:5px 0 0 0;">Επιπλέον κέρδος: <b>{14:.2f} €</b></p>
                </div>
            </div>
            """.format(p_agent_base, sA_effective, sB_effective, sA_revenue, sB_revenue, sA_cost, sB_cost, sA_profit, sB_profit, sA_margin, sB_margin, sA_markup, sB_markup, winner_text, diff_val)
            
            st.markdown(html_table, unsafe_allow_html=True)

            with st.expander("ℹ️ Ερμηνεία Οικονομικών Όρων & Δεικτών"):
                st.info("* **Effective Τιμή:** Η πραγματική τιμή που εισπράττει η εταιρεία ανά μονάδα προϊόντος...\n* **Margin:** (Κέρδος / Έσοδα) * 100\n* **Markup:** (Κέρδος / Κόστος) * 100\n* **Κόστος Εμπορικής Ενέργειας:** Διαφυγόν κέρδος.")
            st.divider()
            
            if st.button("💾 Λήψη Πλήρους Φακέλου Ανάλυσης"):
                now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                sA_indirect_disc = ((1 - sA_effective/p_agent_base)*100) if p_agent_base > 0 else 0
                full_audit_data = [
                    {"ΚΑΤΗΓΟΡΙΑ": "1. ΤΑΥΤΟΤΗΤΑ", "ΣΤΟΙΧΕΙΟ": "Cocktail", "ΣΕΝΑΡΙΟ Α": choice, "ΣΕΝΑΡΙΟ Β": choice},
                    {"ΚΑΤΗΓΟΡΙΑ": "1. ΤΑΥΤΟΤΗΤΑ", "ΣΤΟΙΧΕΙΟ": "Ημερομηνία", "ΣΕΝΑΡΙΟ Α": now_str, "ΣΕΝΑΡΙΟ Β": ""},
                    {"ΚΑΤΗΓΟΡΙΑ": "2. ΤΙΜΟΛΟΓΙΑΚΗ ΒΑΣΗ", "ΣΤΟΙΧΕΙΟ": "Κανονική Τιμή", "ΣΕΝΑΡΙΟ Α": f"{p_agent_base:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{p_agent_base:.2f} €"},
                    {"ΚΑΤΗΓΟΡΙΑ": "3. ΟΓΚΟΙ", "ΣΤΟΙΧΕΙΟ": "Συνολικά Τεμάχια", "ΣΕΝΑΡΙΟ Α": f"{sA_total_units} τμχ", "ΣΕΝΑΡΙΟ Β": f"{sB_total_units} τμχ"},
                    {"ΚΑΤΗΓΟΡΙΑ": "4. P&L", "ΣΤΟΙΧΕΙΟ": "Μικτό Κέρδος", "ΣΕΝΑΡΙΟ Α": f"{sA_profit:.2f} €", "ΣΕΝΑΡΙΟ Β": f"{sB_profit:.2f} €"}
                ]
                df_rep = pd.DataFrame(full_audit_data)
                st.download_button(label="📥 Λήψη (CSV)", data=df_rep.to_csv(index=False, sep=';', encoding='utf-8-sig'), file_name=f"Audit_{choice}.csv", mime="text/csv")

# --- 7. DASHBOARD ---
elif page == "📈 Dashboard":
    st.header("📈 Στατιστικά Πωλήσεων & Ιστορικό")
    if not df_history.empty:
        fig = px.bar(df_history.groupby("Cocktail")["Τεμάχια"].sum().reset_index(), x="Cocktail", y="Τεμάχια", title="Συνολικές Πωλήσεις ανά Cocktail", color="Cocktail")
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("Πλήρες Ιστορικό")
        st.dataframe(df_history.sort_values("Ημερομηνία", ascending=False), use_container_width=True)
        st.divider()
        st.subheader("⚠️ Διαχείριση Δεδομένων")
        if "delete_confirm" not in st.session_state: st.session_state.delete_confirm = False
        if not st.session_state.delete_confirm:
            if st.button("🗑️ Καθαρισμός Ιστορικού"):
                st.session_state.delete_confirm = True
                st.rerun()
        else:
            st.warning("Είστε σίγουροι ότι θέλετε να διαγράψετε όλο το ιστορικό;")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Ναι, Διαγραφή"):
                    save_to_sheet(pd.DataFrame(columns=["Ημερομηνία", "Πελάτης", "Cocktail", "Τεμάχια"]), "History")
                    st.session_state.delete_confirm = False
                    st.success("Διαγράφηκε στο Cloud!")
                    st.rerun()
            with c2:
                if st.button("❌ Άκυρο"):
                    st.session_state.delete_confirm = False
                    st.rerun()
    else: st.info("Δεν υπάρχουν ακόμα δεδομένα στο ιστορικό.")

# --- 7. SHOP SYNC ---
elif page == "🌐 Shop Sync":
    st.header("🌐 Συγχρονισμός & Ανάλυση Ημέρας (WooCommerce API)")
    recipes_path = r"/Users/christossiamantas/Documents/recipes.xlsx"
    WC_URL = "https://your-site-url.gr"
    if 'sync_results' not in st.session_state: st.session_state['sync_results'] = []
    tab1, tab2 = st.tabs(["📥 Λήψη από WooCommerce", "📊 Ανάλυση Υλικών"])
    with tab1:
        st.subheader("Σύνδεση με το Κατάστημα")
        c1, c2 = st.columns(2)
        ck = c1.text_input("Consumer Key", type="password")
        cs = c2.text_input("Consumer Secret", type="password")
        g_date = st.date_input("Επιλέξτε Ημερομηνία:", value=datetime.now().date())
        if st.button("🚀 Λήψη Παραγγελιών"):
            if not ck or not cs: st.warning("Παρακαλώ εισάγετε τα API Keys.")
            else:
                import requests
                from requests.auth import HTTPBasicAuth
                date_start, date_end = f"{g_date}T00:00:00", f"{g_date}T23:59:59"
                endpoint = f"{WC_URL}/wp-json/wc/v3/orders"
                try:
                    with st.spinner("Επικοινωνία με WooCommerce..."):
                        response = requests.get(endpoint, auth=HTTPBasicAuth(ck, cs), params={"after": date_start, "before": date_end, "per_page": 100})
                        if response.status_code == 200:
                            orders = response.json()
                            results = []
                            for order in orders:
                                customer = order.get("billing", {}).get("company", "") or f"{order.get('billing', {}).get('first_name')} {order.get('billing', {}).get('last_name')}"
                                for item in order.get("line_items", []):
                                    results.append({"Ημερομηνία": g_date.strftime("%d/%m/%Y"), "Πελάτης": customer.upper(), "Cocktail": item.get("name"), "Τεμάχια": int(item.get("quantity", 0)) * 24})
                            st.session_state['sync_results'] = results
                            if results:
                                st.success(f"✅ Βρέθηκαν {len(results)} εγγραφές!")
                                st.dataframe(pd.DataFrame(results), use_container_width=True)
                            else: st.warning("Δεν βρέθηκαν παραγγελίες.")
                        else: st.error("Σφάλμα API.")
                except Exception as e: st.error(f"Σφάλμα: {e}")
    with tab2:
        st.subheader("📊 Συνολικά Υλικά προς Προετοιμασία")
        if st.session_state['sync_results']:
            if os.path.exists(recipes_path):
                df_orders = pd.DataFrame(st.session_state['sync_results'])
                df_recipes = pd.read_excel(recipes_path)
                analysis = []
                for _, order in df_orders.iterrows():
                    recipe = df_recipes[df_recipes['Cocktail'].apply(lambda x: str(x).lower() in order['Cocktail'].lower())]
                    if recipe.empty: recipe = df_recipes[df_recipes['Cocktail'].apply(lambda x: order['Cocktail'].lower() in str(x).lower())]
                    for _, ing in recipe.iterrows():
                        analysis.append({"Συστατικό": ing['Συστατικό'], "Ποσότητα": (ing['Ποσότητα'] / 5) * order['Τεμάχια']})
                if analysis:
                    final_sum = pd.DataFrame(analysis).groupby("Συστατικό")["Ποσότητα"].sum().reset_index()
                    st.dataframe(final_sum.style.format({"Ποσότητα": "{:.0f} ml/gr"}), use_container_width=True)
                else: st.error("Δεν βρέθηκαν αντιστοιχίες.")
            else: st.error("Δεν βρέθηκε το αρχείο συνταγών.")
        else: st.info("Κάντε πρώτα λήψη.")

# --- 8. LOT ΠΑΡΑΓΩΓΗΣ (ΜΕΤΑΤΡΟΠΗ ΣΕ SINGLE CLOUD SHEET) ---
elif page == "📦 Lot Παραγωγής":
    st.header("📦 Αναλυτικό Δελτίο Παραγωγής & Ιχνηλασιμότητα")
    import requests
    from requests.auth import HTTPBasicAuth

    # Φόρτωση όλων των Lots από το Cloud μία φορά!
    LOT_COLS = ["Ημερομηνία", "Ώρα", "Πελάτης", "Cocktail", "LOT_Cocktail", "Barcode", "Τεμάχια", "Υλικό", "Σύνολο_ML", "Στόχος_Γραμμάρια", "Lot Number", "Ημ_Λήξης"]
    df_cloud_lots = load_sheet_data("Lot_Reports", LOT_COLS)

    col_date1, col_date2 = st.columns([2, 1])
    with col_date1: selected_date = st.date_input("📅 Ημερομηνία LOT", value=datetime.now(), format="DD/MM/YYYY")
    with col_date2: prod_day = st.text_input("Ημερομηνία Παραγωγής", value=datetime.now().strftime('%d'), max_chars=2)

    formatted_date = selected_date.strftime('%d/%m/%Y')
    date_lot_label = f"{formatted_date}-{prod_day}" 
    date_display = formatted_date
    current_time = datetime.now().strftime('%H:%M')

    if "auto_cocktails" not in st.session_state: st.session_state.auto_cocktails = []
    if "auto_counts" not in st.session_state: st.session_state.auto_counts = {}

    st.subheader("🌐 Αυτόματη Ανάκτηση από E-shop")
    col_api1, col_api2, col_api3 = st.columns([1, 1, 1])
    ck_input = col_api1.text_input("Consumer Key", type="password", key="lot_ck_ui")
    cs_input = col_api2.text_input("Consumer Secret", type="password", key="lot_cs_ui")
    if col_api3.button("📥 Φόρτωση"):
        try:
            url = "https://cabclub.gr/wp-json/wc/v3/orders?status=processing&per_page=100"
            res = requests.get(url, auth=HTTPBasicAuth(ck_input, cs_input))
            if res.status_code == 200:
                found_names, temp_counts = [], {}
                for order in res.json():
                    for item in order.get('line_items', []):
                        match = df_rec[df_rec["Barcode"].astype(str) == str(item.get('sku')).strip()]
                        if not match.empty:
                            c_name = match.iloc[0]["Ονομα"]
                            found_names.append(c_name)
                            temp_counts[c_name] = temp_counts.get(c_name, 0) + int(item.get('quantity', 0))
                st.session_state.auto_cocktails, st.session_state.auto_counts = list(set(found_names)), temp_counts
                st.success("Φορτώθηκαν!")
                st.rerun()
        except: st.error("Σφάλμα σύνδεσης.")

    st.divider()
    if not df_rec.empty:
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1: selected_cocktails = st.multiselect("Επιλέξτε Προϊόντα:", options=df_rec["Ονομα"].unique(), default=st.session_state.auto_cocktails)
        with col_c2: customer_name = st.text_input("👤 Πελάτης / Παραγγελία:", value="CabClub E-shop")

        if selected_cocktails:
            st.subheader(f"⚖️ Οδηγίες Ζύγισης (LOT: {date_lot_label})")
            counts = {}
            c_cols = st.columns(len(selected_cocktails))
            for i, name in enumerate(selected_cocktails):
                counts[name] = c_cols[i].number_input(f"Τμχ: {name}", min_value=1, value=int(st.session_state.auto_counts.get(name, 1)), key=f"cnt_{name}")

            lot_entries = []
            with st.form("detailed_lot_form"):
                for cocktail_name in selected_cocktails:
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    bc = str(recipe_row.get("Barcode", ""))
                    st.markdown(f"#### 🏷️ {cocktail_name} | Shop ID: `{bc}`")
                    for col, label in zip(st.columns([2, 1, 1, 1.2, 1.2, 1.2, 1.2]), ["Υλικό", "ml", "Βάρος(g)", "Lot Ύλης 1", "Λήξη 1", "Lot Ύλης 2", "Λήξη 2"]): col.caption(label)
                    
                    for i in range(1, 14):
                        ing_name = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        if ing_name in ["ΚΕΝΟ", "nan", "Νερό", ""]: continue
                        total_ml = recipe_row.get(f"ML{i}", 0.0) * counts[cocktail_name]
                        target_g = total_ml
                        ing_data = df_ing[df_ing["Name"] == ing_name] if not df_ing.empty else pd.DataFrame()
                        if not ing_data.empty: target_g = (total_ml / ing_data.iloc[0].get("Volume", 700)) * ing_data.iloc[0].get("Weight_Full", 0)

                        r = st.columns([2, 1, 1, 1.2, 1.2, 1.2, 1.2])
                        r[0].write(f"**{ing_name}**"); r[1].write(f"{total_ml:.0f}"); r[2].markdown(f"**{target_g:.1f}g**")
                        l1 = r[3].text_input("Lot 1", key=f"l1_{cocktail_name}_{i}", label_visibility="collapsed")
                        e1 = r[4].text_input("E1", key=f"e1_{cocktail_name}_{i}", label_visibility="collapsed")
                        l2 = r[5].text_input("Lot 2", key=f"l2_{cocktail_name}_{i}", label_visibility="collapsed")
                        e2 = r[6].text_input("E2", key=f"e2_{cocktail_name}_{i}", label_visibility="collapsed")

                        lot_entries.append({"Ημερομηνία": date_display, "Ώρα": current_time, "Πελάτης": customer_name, "Cocktail": cocktail_name, "LOT_Cocktail": date_lot_label, "Barcode": bc, "Τεμάχια": counts[cocktail_name], "Υλικό": ing_name, "Σύνολο_ML": total_ml, "Στόχος_Γραμμάρια": round(target_g, 1), "Lot Number": l1 if not l2 else f"{l1} / {l2}", "Ημ_Λήξης": e1 if not e2 else f"{e1} / {e2}"})
                
                if st.form_submit_button("💾 Οριστικοποίηση & Αποθήκευση στο Cloud"):
                    if lot_entries:
                        final_df = pd.concat([df_cloud_lots, pd.DataFrame(lot_entries)], ignore_index=True)
                        save_to_sheet(final_df, "Lot_Reports")
                        st.success(f"✅ Αποθηκεύτηκε στο Google Sheets! LOT: {date_lot_label}")
                        time.sleep(1)
                        st.rerun()

    st.divider()
    st.subheader("📂 Ιστορικό Παραγωγής & Εκτυπώσεις")
    if not df_cloud_lots.empty:
        all_dates = sorted(df_cloud_lots["Ημερομηνία"].unique().tolist(), reverse=True)
        sel_hist_date = st.selectbox("🔍 Επιλέξτε Ημερομηνία Παραγωγής:", all_dates)
        
        if sel_hist_date:
            view_df = df_cloud_lots[df_cloud_lots["Ημερομηνία"] == sel_hist_date]
            sel_cust = st.selectbox("👤 Φίλτρο Πελάτη:", ["ΟΛΟΙ"] + sorted(view_df["Πελάτης"].unique().tolist()))
            if sel_cust != "ΟΛΟΙ": view_df = view_df[view_df["Πελάτης"] == sel_cust]
            
            st.dataframe(view_df[["Πελάτης", "Cocktail", "LOT_Cocktail", "Ώρα", "Τεμάχια"]].drop_duplicates(), use_container_width=True)
            
            html = f"<h2>ΔΕΛΤΙΟ ΠΑΡΑΓΩΓΗΣ</h2><p>Ημερομηνία: <b>{sel_hist_date}</b></p>"
            for _, r in view_df.iterrows():
                html += f"<p>{r['Cocktail']} - {r['Υλικό']} - {r['Στόχος_Γραμμάρια']}g - Lot: {r['Lot Number']}</p>"
            
            c1, c2 = st.columns(2)
            c1.download_button("🖨️ Εκτύπωση Δελτίου", data=html.encode('utf-8'), file_name=f"Report_{sel_hist_date.replace('/','_')}.html", mime="text/html", use_container_width=True)

    st.divider()
    st.subheader("🔍 Αναζήτηση Ιχνηλασιμότητας (Cloud Data)")
    if not df_cloud_lots.empty:
        with st.expander("⚙️ Σύνθετα Φίλτρα"):
            f1, f2, f3 = st.columns(3)
            search_cust = f1.multiselect("Πελάτης:", sorted(df_cloud_lots["Πελάτης"].unique()))
            search_cock = f2.multiselect("Cocktail:", sorted(df_cloud_lots["Cocktail"].unique()))
            search_ing = f3.multiselect("Πρώτη Ύλη:", sorted(df_cloud_lots["Υλικό"].unique()))
            search_lot = st.text_input("🔢 Αναζήτηση βάσει LOT:")

        dff = df_cloud_lots.copy()
        if search_cust: dff = dff[dff["Πελάτης"].isin(search_cust)]
        if search_cock: dff = dff[dff["Cocktail"].isin(search_cock)]
        if search_ing: dff = dff[dff["Υλικό"].isin(search_ing)]
        if search_lot: dff = dff[dff.apply(lambda x: search_lot.lower() in str(x).lower(), axis=1)]

        st.write(f"Αποτελέσματα: **{len(dff)}** εγγραφές")
        st.dataframe(dff, use_container_width=True)
        if not dff.empty:
            c1, c2 = st.columns(2)
            c1.download_button("📊 Εξαγωγή (CSV)", data=dff.to_csv(index=False, encoding="utf-8-sig"), file_name="Trace_Data.csv", mime="text/csv")

# --- 9. ΑΝΤΙΚΑΤΑΣΤΑΣΗ ΥΛΙΚΟΥ ---
elif page == "🔄 Αντικατάσταση":
    st.header("🔄 Μαζική Αντικατάσταση Πρώτης Ύλης")
    if not df_rec.empty:
        used_ingredients = []
        for i in range(1, 14):
            if f"ΣΥΣΤΑΤΙΚΟ{i}" in df_rec.columns: used_ingredients.extend(df_rec[f"ΣΥΣΤΑΤΙΚΟ{i}"].astype(str).unique())
        unique_used = sorted(list(set([ing for ing in used_ingredients if ing not in ["ΚΕΝΟ", "nan", "None", ""]])))
        
        col_src, col_dst = st.columns(2)
        with col_src: target_ing = st.selectbox("1. Υλικό προς αντικατάσταση:", options=unique_used)
        
        found_recipes = [row["Ονομα"] for _, row in df_rec.iterrows() if any(str(row.get(f"ΣΥΣΤΑΤΙΚΟ{i}")) == target_ing for i in range(1, 14))]
        if found_recipes:
            st.warning(f"🔎 Βρέθηκε σε **{len(found_recipes)}** συνταγές: {', '.join(found_recipes)}")
            with col_dst: new_ing = st.selectbox("2. Αντικατάσταση με:", options=df_ing["Name"].unique())
            
            if st.button("🚀 Εκτέλεση ΠΑΝΤΟΥ στο Cloud"):
                temp_recipes = df_rec.copy()
                total_changes = 0
                for i in range(1, 14):
                    mask = temp_recipes[f"ΣΥΣΤΑΤΙΚΟ{i}"].astype(str) == target_ing
                    total_changes += mask.sum()
                    temp_recipes.loc[mask, f"ΣΥΣΤΑΤΙΚΟ{i}"] = new_ing
                save_to_sheet(temp_recipes, "Recipes")
                st.success(f"✅ Επιτυχία σε {total_changes} σημεία.")
                st.rerun()

# --- 10. HACCP LOG ---
elif page == "🧼 Συντήρηση & HACCP":
    st.header("🧼 Ημερολόγιο Συντήρησης & Καθαρισμού")
    
    HACCP_COLS = ["Ημερομηνία", "Ώρα", "Χρήστης", "Τύπος", "Στοιχείο", "Τιμή", "Καθαριστικό", "Σημειώσεις"]
    df_haccp = load_sheet_data("HACCP_Log", HACCP_COLS)

    col_u1, col_u2 = st.columns(2)
    with col_u1: staff_name = st.text_input("👤 Ονοματεπώνυμο Υπευθύνου:", placeholder="π.χ. Νίκος Παπαδόπουλος")
    with col_u2:
        selected_date = st.date_input("📅 Ημερομηνία Καταγραφής:", value=datetime.now())
        date_str = selected_date.strftime("%d/%m/%y")
    
    tab1, tab2, tab3 = st.tabs(["🌡️ Θερμοκρασίες", "🧹 Checklist", "📄 Ιστορικό"])
    with tab1:
        with st.form("temp_form"):
            device = st.selectbox("Συσκευή:", ["Ψυγείο 1", "Ψυγείο 2", "Ψυγείο 3", "Κατάψυξη 1", "Κατάψυξη 2"])
            is_freezer = "Κατάψυξη" in device
            temp = st.number_input("Θερμοκρασία (°C):", value=-18.0 if is_freezer else 4.0, step=0.5)
            notes = st.text_input("Σημειώσεις:")
            if st.form_submit_button("💾 Καταγραφή Cloud"):
                if not staff_name.strip(): st.error("⚠️ Συμπληρώστε όνομα!")
                else:
                    log_data = {"Ημερομηνία": date_str, "Ώρα": datetime.now().strftime("%H:%M"), "Χρήστης": staff_name, "Τύπος": "Θερμοκρασία", "Στοιχείο": device, "Τιμή": f"{temp} °C", "Καθαριστικό": "-", "Σημειώσεις": notes}
                    final_haccp = pd.concat([df_haccp, pd.DataFrame([log_data])], ignore_index=True)
                    save_to_sheet(final_haccp, "HACCP_Log")
                    st.success(f"✅ Η μέτρηση αποθηκεύτηκε στο Google Sheets!")
                    st.rerun()

    with tab2:
        tasks_data = {"Ημερήσιο Checklist": ["Σκεύη & Εργαλεία", "Εξοπλισμός", "Δάπεδα"], "Εβδομαδιαίο Checklist": ["Ψυγεία", "Τοίχοι"]}
        category = st.radio("Τύπος:", list(tasks_data.keys()), horizontal=True)
        responses = {}
        with st.form(f"form_{category}"):
            for task in tasks_data[category]:
                c1, c2 = st.columns([0.4, 0.6])
                with c1: done = st.checkbox(task, key=f"ch_{task}")
                with c2: cleaner = st.text_input("Καθαριστικό:", key=f"cl_{task}")
                responses[task] = {"done": done, "cleaner": cleaner}
            if st.form_submit_button("💾 Οριστικοποίηση Cloud"):
                if not staff_name.strip(): st.error("⚠️ Συμπληρώστε όνομα!")
                elif all(res["done"] for res in responses.values()):
                    summary_cleaners = " | ".join([f"{t}: {res['cleaner']}" for t, res in responses.items()])
                    log_data = {"Ημερομηνία": date_str, "Ώρα": datetime.now().strftime("%H:%M"), "Χρήστης": staff_name, "Τύπος": "Καθαρισμός", "Στοιχείο": category, "Τιμή": "ΟΛΟΚΛΗΡΩΘΗΚΕ", "Καθαριστικό": summary_cleaners, "Σημειώσεις": "-"}
                    final_haccp = pd.concat([df_haccp, pd.DataFrame([log_data])], ignore_index=True)
                    save_to_sheet(final_haccp, "HACCP_Log")
                    st.success("✨ Το checklist αποθηκεύτηκε!")
                    st.rerun()

    with tab3:
        if not df_haccp.empty:
            st.dataframe(df_haccp.sort_values(by="Ημερομηνία", ascending=False), use_container_width=True)
        else:
            st.info("ℹ️ Δεν υπάρχουν ακόμη καταγραφές στο Cloud.")
