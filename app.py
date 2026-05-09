import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime
import plotly.express as px
import imaplib
import email
import time

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

# --- 1. ΑΠΟΘΗΚΗ (ΦΟΡΜΑ ΑΝΤΙ ΓΙΑ ΠΙΝΑΚΑ) ---
if page == "📦 Αποθήκη":
    st.header("📦 Διαχείριση Υλικών")
    
    # Εξασφάλιση στηλών
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
            
            new_weight = st.number_input("Βάρος Περιεχομένου σε Γραμμάρια (g)", min_value=0.0, help="Το βάρος μόνο του υγρού")
            
            if st.form_submit_button("💾 Αποθήκευση Νέου Υλικού"):
                if new_name:
                    max_id = df_ing["ID"].max() if not df_ing.empty else 1000
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
                    df_ing.to_csv(DB_INGREDIENTS, index=False, encoding='utf-8-sig')
                    st.success(f"✅ Το υλικό '{new_name}' προστέθηκε!")
                    st.rerun()
                else:
                    st.error("Παρακαλώ δώστε όνομα στο υλικό.")

    # --- TAB 2: ΕΠΕΞΕΡΓΑΣΙΑ / ΔΙΑΓΡΑΦΗ ---
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
                    
                    # --- ΕΔΩ ΜΠΑΙΝΕΙ Ο ΝΕΟΣ ΚΩΔΙΚΑΣ UPDATE ---
                    if col_btn1.form_submit_button("Update ✅"):
                        # 1. Φόρτωση των αρχείων απευθείας από το δίσκο
                        temp_ing = pd.read_csv(DB_INGREDIENTS)
                        temp_rec = pd.read_csv(DB_RECIPES)
                        
                        old_name = ing_to_edit 
                        
                        # 2. Ενημέρωση στην Αποθήκη
                        idx_ing = temp_ing[temp_ing["Name"] == old_name].index
                        temp_ing.loc[idx_ing, "Name"] = edit_name
                        temp_ing.loc[idx_ing, "Price"] = edit_price
                        temp_ing.loc[idx_ing, "Volume"] = edit_vol
                        temp_ing.loc[idx_ing, "Αλκοόλ %"] = edit_alc
                        temp_ing.loc[idx_ing, "Weight_Full"] = edit_weight
                        temp_ing.loc[idx_ing, "Τιμή/ml"] = edit_price / edit_vol
                        
                        # Σώσιμο Αποθήκης
                        temp_ing.to_csv(DB_INGREDIENTS, index=False, encoding='utf-8-sig')

                        # 3. Ενημέρωση στις Συνταγές (Αν άλλαξε το όνομα)
                        if old_name != edit_name:
                            changes_made = 0
                            for i in range(1, 14):
                                col = f"ΣΥΣΤΑΤΙΚΟ{i}"
                                if col in temp_rec.columns:
                                    # Καθαρισμός κενών για σωστή σύγκριση
                                    temp_rec[col] = temp_rec[col].astype(str).str.strip()
                                    mask = temp_rec[col] == old_name.strip()
                                    if mask.any():
                                        temp_rec.loc[mask, col] = edit_name
                                        changes_made += 1
                            
                            if changes_made > 0:
                                temp_rec.to_csv(DB_RECIPES, index=False, encoding='utf-8-sig')
                                st.info(f"⚙️ Έγινε αυτόματη ενημέρωση σε {changes_made} πεδία συνταγών.")

                        st.success(f"✅ Το υλικό '{edit_name}' ενημερώθηκε!")
                        st.rerun()
                    
                    # --- ΤΕΛΟΣ ΝΕΟΥ ΚΩΔΙΚΑ UPDATE ---

                    if col_btn2.form_submit_button("Διαγραφή 🗑️"):
                        df_ing = df_ing[df_ing["Name"] != ing_to_edit]
                        df_ing.to_csv(DB_INGREDIENTS, index=False, encoding='utf-8-sig')
                        st.warning(f"Το υλικό {ing_to_edit} διαγράφηκε.")
                        st.rerun()

    # --- TAB 3: ΠΡΟΒΟΛΗ ΠΙΝΑΚΑ ---
    with tab3:
        st.subheader("Συνολική Εικόνα Αποθήκης")
        st.dataframe(df_ing[["ID", "Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Weight_Full"]], use_container_width=True)
        
        st.divider()
        
        # --- ΚΑΤΑΣΚΕΥΗ HTML ΓΙΑ ΛΙΣΤΑ ΠΡΩΤΩΝ ΥΛΩΝ ---
        import base64
        from datetime import datetime

        def get_base64_image(image_path):
            try:
                with open(image_path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
            except: return ""

        logo_base64 = get_base64_image("logo.png")

        # 1. CSS & Layout
        html_ing = f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <style>
                body {{ font-family: 'Helvetica', sans-serif; padding: 30px; color: #333; background-color: #f4f4f4; }}
                .container {{ background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; border-bottom: 4px solid #ffcc00; padding-bottom: 20px; margin-bottom: 30px; }}
                .logo-img {{ max-width: 120px; margin-bottom: 10px; }}
                h1 {{ margin: 0; color: #1a1a1a; text-transform: uppercase; letter-spacing: 2px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }}
                th {{ background-color: #ffcc00; color: #1a1a1a; padding: 12px; text-align: left; border: 1px solid #ddd; }}
                td {{ padding: 10px; border: 1px solid #eee; font-size: 14px; }}
                tr:nth-child(even) {{ background-color: #fff9e6; }}
                tr:hover {{ background-color: #f2f2f2; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #ddd; padding-top: 10px; }}
                .price-tag {{ font-weight: bold; color: #d32f2f; }}
            </style>
        </head>
        <body>
            <div class='container'>
                <div class='header'>
                    {f'<img src="data:image/png;base64,{logo_base64}" class="logo-img"><br>' if logo_base64 else ''}
                    <h1>CABCLUB | LISTA ΠΡΩΤΩΝ ΥΛΩΝ</h1>
                    <p>Ημερομηνία Εξαγωγής: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Όνομα Υλικού</th>
                            <th>Τιμή (€)</th>
                            <th>ML Φιάλης</th>
                            <th>Τιμή/ml</th>
                            <th>Alc %</th>
                            <th>Βάρος (g)</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        # 2. Προσθήκη Δεδομένων
        for _, row in df_ing.iterrows():
            html_ing += f"""
                <tr>
                    <td><b>{row['ID']}</b></td>
                    <td>{row['Name']}</td>
                    <td class='price-tag'>{row['Price']:.2f} €</td>
                    <td>{row['Volume']:.0f} ml</td>
                    <td>{row['Τιμή/ml']:.4f} €</td>
                    <td>{row['Αλκοόλ %']:.1f}%</td>
                    <td>{row['Weight_Full']:.1f} g</td>
                </tr>
            """

        html_ing += """
                    </tbody>
                </table>
                <div class='footer'>
                    © CabClub Cocktails Management System - Warehouse Report
                </div>
            </div>
        </body>
        </html>
        """

        # 3. Κουμπί Λήψης
        st.download_button(
            label="📄 Λήψη Λίστας Αποθήκης (HTML)",
            data=html_ing,
            file_name=f"CabClub_Warehouse_{datetime.now().strftime('%d_%m_%Y')}.html",
            mime="text/html",
            use_container_width=True
        )


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

# --- 🖨️ ΕΚΤΥΠΩΣΗ ΠΛΗΡΟΥΣ ΒΙΒΛΙΟΥ ΣΥΝΤΑΓΩΝ (Yellow Theme + Logo) ---
    st.divider()
    st.subheader("🖨️ Εκτύπωση Βιβλίου Συνταγών")

    import base64

    # Συνάρτηση για τη μετατροπή του logo σε Base64
    def get_base64_image(image_path):
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except:
            return ""

    # Εδώ βάλε τη διαδρομή του logo σου (π.χ. "logo.png")
    logo_base64 = get_base64_image("logo.png") 

    if not df_rec.empty:
        # 1. Κατασκευή του HTML εγγράφου
        html_book = f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <style>
                body {{ font-family: 'Helvetica', sans-serif; padding: 40px; color: #333; background-color: #f9f9f9; }}
                .main-title {{ text-align: center; border-bottom: 5px solid #ffcc00; padding-bottom: 10px; margin-bottom: 50px; }}
                .logo-img {{ max-width: 150px; margin-bottom: 10px; }}
                .recipe-card {{ 
                    background-color: white; 
                    border: 1px solid #ddd; 
                    border-radius: 12px; 
                    padding: 25px; 
                    margin-bottom: 40px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                    page-break-inside: avoid;
                }}
                .recipe-header {{ 
                    background-color: #ffcc00; /* Κίτρινο Χρώμα */
                    color: #1a1a1a; /* Σκούρα γράμματα για αντίθεση */
                    padding: 15px; 
                    border-radius: 8px 8px 0 0; 
                    margin: -25px -25px 20px -25px; 
                }}
                .recipe-name {{ margin: 0; font-size: 26px; text-transform: uppercase; }}
                .barcode-label {{ font-size: 14px; opacity: 0.8; font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th {{ background-color: #fff9e6; text-align: left; padding: 12px; border-bottom: 2px solid #ffcc00; color: #444; }}
                td {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 15px; }}
                .ing-name {{ font-weight: bold; color: #2c3e50; }}
                .footer {{ text-align: center; font-size: 12px; color: #7f8c8d; margin-top: 60px; border-top: 1px solid #ccc; padding-top: 10px; }}
                .analysis-box {{ 
                    margin-top:20px; 
                    padding:12px; 
                    background:#fffdf2; 
                    border-top:3px solid #ffcc00; 
                    border-radius: 0 0 8px 8px; 
                }}
            </style>
        </head>
        <body>
            <div class='main-title'>
                {f'<img src="data:image/png;base64,{logo_base64}" class="logo-img"><br>' if logo_base64 else ''}
                <h1>CABCLUB COCKTAILS</h1>
                <h2>ΟΛΟΚΛΗΡΩΜΕΝΟ ΒΙΒΛΙΟ ΣΥΝΤΑΓΩΝ</h2>
                <p>Σύνολο Συνταγών: {len(df_rec)}</p>
            </div>
        """

        for _, recipe in df_rec.iterrows():
            name = recipe.get("Ονομα", "Χωρίς Όνομα")
            bc = recipe.get("Barcode", "-")
            
            html_book += f"""
            <div class='recipe-card'>
                <div class='recipe-header'>
                    <h2 class='recipe-name'>{name}</h2>
                    <span class='barcode-label'>Shop ID: {bc}</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Συστατικό Συνταγής</th>
                            <th>Ποσότητα (ml)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            total_ml_cocktail = 0
            total_alcohol_ml = 0
            total_cost = 0
            found_ingredients = 0
            
            for i in range(1, 14):
                raw_ing = str(recipe.get(f"ΣΥΣΤΑΤΙΚΟ{i}", ""))
                try:
                    ml = float(recipe.get(f"ML{i}", 0))
                except:
                    ml = 0
                
                ing_clean = raw_ing.strip()
                ing_check = ing_clean.upper()
                
                if ing_clean and ing_check not in ["NAN", "ΚΕΝΟ", "ΚΕΝΟ.", "-", "NONE", "0", "NULL"] and ml > 0:
                    html_book += f"<tr><td class='ing-name'>{ing_clean}</td><td>{ml:.0f} ml</td></tr>"
                    found_ingredients += 1
                    
                    if not df_ing.empty and ing_clean in df_ing["Name"].values:
                        ing_row = df_ing[df_ing["Name"] == ing_clean].iloc[0]
                        abv = float(ing_row.get("ABV", 0))
                        price = float(ing_row.get("Price", 0))
                        vol = float(ing_row.get("Volume", 700))
                        cost_per_ml = price / vol if vol > 0 else 0
                        total_ml_cocktail += ml
                        total_alcohol_ml += ml * (abv / 100)
                        total_cost += ml * cost_per_ml
            
            if found_ingredients == 0:
                html_book += "<tr><td colspan='2'><i>Δεν έχουν καταχωρηθεί συστατικά.</i></td></tr>"

            final_abv = (total_alcohol_ml / total_ml_cocktail * 100) if total_ml_cocktail > 0 else 0
            suggested_price = total_cost / 0.25 # Food Cost 25%

            html_book += f"""
                    </tbody>
                </table>
                <div class='analysis-box'>
                    <span style='font-size:16px;'>Αλκοόλ (ABV): <b>{final_abv:.1f}%</b></span>
                    <span style='float:right; font-size:18px; color:#b38f00;'>Προτεινόμενη Λιανική: <b>{suggested_price:.2f} €</b></span>
                </div>
            </div>
            """

        html_book += f"""
            <div class='footer'>
                Αυτόματη εξαγωγή από το σύστημα διαχείρισης CABCLUB: {datetime.now().strftime('%d/%m/%Y %H:%M')}
            </div>
        </body>
        </html>
        """

        st.download_button(
            label="📑 Λήψη Κίτρινου Βιβλίου Συνταγών (με Logo)",
            data=html_book,
            file_name=f"Recipe_Book_Yellow_{datetime.now().strftime('%d_%m_%Y')}.html",
            mime="text/html",
            use_container_width=True
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

      # ==============================================================================
# 8. LOT ΠΑΡΑΓΩΓΗΣ (ΠΕΛΑΤΗΣ - ΗΜΕΡΟΜΗΝΙΑ ΩΣ LOT - ΙΧΝΗΛΑΣΙΜΟΤΗΤΑ)
# ==============================================================================
elif page == "📦 Lot Παραγωγής":
    st.header("📦 Αναλυτικό Δελτίο Παραγωγής & Ιχνηλασιμότητα")
    
    import glob
    from requests.auth import HTTPBasicAuth
    import requests
    import time

    # --- 1. ΚΕΝΤΡΙΚΟΣ ΟΡΙΣΜΟΣ ΗΜΕΡΟΜΗΝΙΑΣ & LOT (ΕΝΗΜΕΡΩΜΕΝΟ) ---
    col_date1, col_date2 = st.columns([2, 1])
    
    with col_date1:
        selected_date = st.date_input("📅 Ημερομηνία LOT", value=datetime.now(), format="DD/MM/YYYY")
    
    with col_date2:
        prod_day = st.text_input("Ημερομηνία Παραγωγής", value=datetime.now().strftime('%d'), max_chars=2)

    # ΝΕΟΣ ΟΡΙΣΜΟΣ LOT: Συνδυασμός Ημερομηνίας LOT και Ημέρας Παραγωγής
    # Μετατρέπουμε την ημερομηνία σε μορφή DD/MM/YYYY και προσθέτουμε την παύλα και το prod_day
    formatted_date = selected_date.strftime('%d/%m/%Y')
    date_lot_label = f"{formatted_date}-{prod_day}" 
    
    # Λοιπές μεταβλητές προβολής
    date_display = formatted_date
    current_time = datetime.now().strftime('%H:%M')

    # Αρχικοποίηση session state
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
    
    import glob
    import os
    import time
    import base64

    def get_base64_image(image_path):
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except: return ""

    logo_base_64 = get_base64_image("logo.png") 

    past_files = glob.glob("Lot_Report_*.csv")
    if past_files:
        all_dates_files = sorted([f.replace("Lot_Report_", "").replace(".csv", "").replace("_", "/") for f in past_files], reverse=True)
        sel_hist_date = st.selectbox("🔍 Επιλέξτε Ημερομηνία Παραγωγής:", all_dates_files)
        
        if sel_hist_date:
            file_path = f"Lot_Report_{sel_hist_date.replace('/', '_')}.csv"
            
            if os.path.exists(file_path):
                df_past = pd.read_csv(file_path)
                
                # --- 🛠️ ΔΙΑΧΕΙΡΙΣΗ & ΕΠΕΞΕΡΓΑΣΙΑ ---
                st.markdown("#### 🛠️ Διαχείριση Παραγωγής")
                
                cocktail_options = df_rec["Ονομα"].dropna().unique().tolist() if not df_rec.empty else []
                ingredient_options = df_ing["Name"].dropna().unique().tolist() if not df_ing.empty else []

                batches = df_past.groupby(['Ώρα', 'Πελάτης', 'Cocktail', 'LOT_Cocktail']).groups
                options = ["-- Επιλέξτε Παραγωγή --"]
                batch_mapping = {}
                for (time_val, cust, cock, lot_c), indices in batches.items():
                    label = f"🍹 {cock} | 👤 {cust} | 🕒 {time_val} | LOT: {lot_c}"
                    options.append(label)
                    batch_mapping[label] = list(indices)

                selected_batch = st.selectbox("🔍 Αναζήτηση Παραγωγής:", options)

                if selected_batch != "-- Επιλέξτε Παραγωγή --":
                    row_indices = batch_mapping[selected_batch]
                    first_idx = row_indices[0]
                    base_data = df_past.loc[first_idx]
                    
                    try: old_pieces = int(base_data.get("Τεμάχια", 1))
                    except: old_pieces = 1

                    # --- ΒΑΣΙΚΑ ΣΤΟΙΧΕΙΑ (ΕΞΩ ΑΠΟ ΤΗ ΦΟΡΜΑ ΓΙΑ ΑΜΕΣΗ ΑΝΤΙΔΡΑΣΗ) ---
                    st.info("💡 Αλλάξτε το Cocktail ή τα Τεμάχια και δείτε τα υλικά να αλλάζουν αμέσως!")
                    c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1.5])
                    
                    new_customer = c1.text_input("Πελάτης", value=str(base_data.get("Πελάτης", "")), key=f"edit_cust_{first_idx}")
                    
                    current_cocktail_name = str(base_data.get("Cocktail", ""))
                    try: c_idx = cocktail_options.index(current_cocktail_name)
                    except: c_idx = 0
                    
                    new_cocktail = c2.selectbox("Νέο Cocktail", options=cocktail_options, index=c_idx, key=f"edit_cock_{first_idx}")
                    new_pieces = c3.number_input("Τεμάχια", value=old_pieces, min_value=1, key=f"edit_pcs_{first_idx}")
                    new_lot_cocktail = c4.text_input("LOT Προϊόντος", value=str(base_data.get("LOT_Cocktail", "")), key=f"edit_lotc_{first_idx}")

                    # --- ΛΟΓΙΚΗ ΖΩΝΤΑΝΟΥ ΥΠΟΛΟΓΙΣΜΟΥ ---
                    cocktail_changed = (new_cocktail != current_cocktail_name)
                    multiplier = new_pieces / old_pieces if not cocktail_changed else new_pieces
                    
                    # Προετοιμασία λίστας υλικών για εμφάνιση
                    display_ingredients = []
                    
                    if cocktail_changed:
                        # Αν άλλαξε το cocktail, τραβάμε τη νέα συνταγή
                        new_rec = df_rec[df_rec["Ονομα"] == new_cocktail].iloc[0]
                        for i in range(1, 14):
                            ing = str(new_rec.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "")).strip()
                            ml_b = new_rec.get(f"ML{i}", 0)
                            if ing and ing.upper() not in ["NAN", "ΚΕΝΟ", "", "-"]:
                                display_ingredients.append({
                                    "Υλικό": ing,
                                    "ML": float(ml_b) * new_pieces,
                                    "G": 0.0, # Μπορείτε να βάλετε εδώ τον υπολογισμό βάρους αν θέλετε
                                    "Lot": "", "Exp": ""
                                })
                    else:
                        # Αν είναι το ίδιο cocktail, παίρνουμε τα υλικά από το df_past (με τα LOT τους)
                        for idx in row_indices:
                            r_data = df_past.loc[idx]
                            display_ingredients.append({
                                "Υλικό": str(r_data.get("Υλικό", "")),
                                "ML": float(r_data.get("Σύνολο_ML", 0.0)) * (new_pieces / old_pieces),
                                "G": float(r_data.get("Στόχος_Γραμμάρια", 0.0)) * (new_pieces / old_pieces),
                                "Lot": str(r_data.get("Lot Number", "")),
                                "Exp": str(r_data.get("Ημ_Λήξης", ""))
                            })

                    # --- ΕΜΦΑΝΙΣΗ ΥΛΙΚΩΝ ΚΑΙ ΑΠΟΘΗΚΕΥΣΗ ---
                    with st.form("save_edit_form"):
                        st.markdown("#### 📋 Στοιχεία Υλικών")
                        h = st.columns([2, 1, 1, 1.5, 1.5])
                        labels = ["Υλικό", "ML", "G", "Lot Ύλης", "Ημ. Λήξης"]
                        for col, lab in zip(h, labels): col.caption(lab)
                        
                        final_updated_data = []
                        for i, item in enumerate(display_ingredients):
                            r = st.columns([2, 1, 1, 1.5, 1.5])
                            r[0].write(f"**{item['Υλικό']}**")
                            r[1].write(f"{item['ML']:.0f}")
                            r[2].write(f"{item['G']:.1f}")
                            
                            u_lot = r[3].text_input("Lot", value=item['Lot'], key=f"u_lot_{i}_{first_idx}", label_visibility="collapsed")
                            u_exp = r[4].text_input("Exp", value=item['Exp'], key=f"u_exp_{i}_{first_idx}", label_visibility="collapsed")
                            
                            final_updated_data.append({
                                "Υλικό": item['Υλικό'], "ML": item['ML'], "G": item['G'],
                                "Lot": u_lot, "Exp": u_exp
                            })

                        st.markdown("<br>", unsafe_allow_html=True)
                        b_save, b_del = st.columns(2)
                        
                        if b_save.form_submit_button("💾 Οριστικοποίηση Αλλαγών", type="primary", use_container_width=True):
                            # Καθαρισμός παλιών γραμμών και προσθήκη νέων
                            df_past = df_past.drop(row_indices)
                            
                            new_entries = []
                            for entry in final_updated_data:
                                new_entries.append({
                                    "Ημερομηνία": base_data['Ημερομηνία'],
                                    "Ώρα": base_data['Ώρα'],
                                    "Πελάτης": new_customer,
                                    "Cocktail": new_cocktail,
                                    "Τεμάχια": int(new_pieces),
                                    "Υλικό": entry['Υλικό'],
                                    "Σύνολο_ML": entry['ML'],
                                    "Στόχος_Γραμμάρια": round(entry['G'], 1),
                                    "LOT_Cocktail": new_lot_cocktail,
                                    "Lot Number": entry['Lot'],
                                    "Ημ_Λήξης": entry['Exp']
                                })
                            
                            df_updated = pd.concat([df_past, pd.DataFrame(new_entries)], ignore_index=True)
                            df_updated.to_csv(file_path, index=False, encoding='utf-8-sig')
                            st.success("✅ Η παραγωγή ενημερώθηκε!")
                            time.sleep(1)
                            st.rerun()

                        if b_del.form_submit_button("🗑️ Διαγραφή Παραγωγής", use_container_width=True):
                            df_past = df_past.drop(row_indices)
                            if df_past.empty: os.remove(file_path)
                            else: df_past.to_csv(file_path, index=False, encoding='utf-8-sig')
                            st.warning("🗑️ Διαγράφηκε!")
                            time.sleep(1)
                            st.rerun()

                st.divider()
                
                # --- ΠΡΟΒΟΛΗ & ΕΚΤΥΠΩΣΕΙΣ ---
                all_custs = ["ΟΛΟΙ"] + sorted(df_past["Πελάτης"].unique().tolist())
                sel_cust = st.selectbox("👤 Φίλτρο Πελάτη (για προβολή):", all_custs)
                view_df = df_past if sel_cust == "ΟΛΟΙ" else df_past[df_past["Πελάτης"] == sel_cust]
                st.dataframe(view_df, use_container_width=True)
                
                # --- ΕΚΤΥΠΩΣΕΙΣ & ΦΙΛΤΡΑ ---
                if not df_past.empty:
                    all_custs = ["ΟΛΟΙ"] + sorted(df_past["Πελάτης"].unique().tolist())
                    sel_cust = st.selectbox("👤 Φίλτρο Πελάτη (για εκτύπωση):", all_custs)
                    
                    view_df = df_past if sel_cust == "ΟΛΟΙ" else df_past[df_past["Πελάτης"] == sel_cust]
                    
                    if view_df.empty:
                        st.warning("⚠️ Δεν υπάρχουν διαθέσιμα δεδομένα με τα τρέχοντα φίλτρα.")
                    else:
                        st.markdown("##### 📋 Προεπισκόπηση Δεδομένων")
                        st.dataframe(view_df, use_container_width=True)
                        
                        # --- 1. ΕΠΑΓΓΕΛΜΑΤΙΚΟ HTML (ΙΧΝΗΛΑΣΙΜΟΤΗΤΑ) ---
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
                                <p>Ημερομηνία: <b>{sel_hist_date}</b> | LOT Ημέρας: <b>{view_df['LOT_Cocktail'].iloc[0] if not view_df.empty else '-'}</b></p>
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
                                    <h3 class='cocktail-title'>{c}</h3>
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

                        # --- 2. ΗΜΕΡΗΣΙΟ ΦΥΛΛΟ ΠΑΡΑΓΩΓΗΣ (ΣΥΝΟΛΑ COCKTAILS) ---
                        df_daily = view_df.drop_duplicates(subset=["Πελάτης", "Cocktail", "LOT_Cocktail"])
                        df_grouped = df_daily.groupby(['Cocktail', 'Πελάτης', 'LOT_Cocktail'])['Τεμάχια'].sum().reset_index()

                        html_daily = f"""
                        <html>
                        <head>
                            <meta charset='UTF-8'>
                            <style>
                                body {{ font-family: 'Helvetica', sans-serif; padding: 20px; color: #333; }}
                                .header {{ text-align: center; border-bottom: 3px solid #d32f2f; padding-bottom: 10px; margin-bottom: 30px; }}
                                .cocktail-section {{ margin-bottom: 40px; }}
                                .cocktail-header {{ background-color: #d32f2f; color: white; padding: 10px; margin-bottom: 0; border-radius: 5px 5px 0 0; }}
                                table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                                th {{ background-color: #444; color: white; padding: 10px; border: 1px solid #ddd; text-align: left; }}
                                td {{ padding: 10px; border: 1px solid #ddd; }}
                                .subtotal-row {{ background-color: #f2f2f2; font-weight: bold; }}
                                .grand-total {{ text-align: center; font-size: 20px; font-weight: bold; border-top: 2px solid #333; padding-top: 20px; margin-top: 30px; }}
                            </style>
                        </head>
                        <body>
                            <div class='header'>
                                <h1>📋 ΗΜΕΡΗΣΙΟ ΦΥΛΛΟ ΠΑΡΑΓΩΓΗΣ</h1>
                                <p>Ημερομηνία: <b>{sel_hist_date}</b></p>
                            </div>
                        """

                        for cocktail in df_grouped['Cocktail'].unique():
                            c_data = df_grouped[df_grouped['Cocktail'] == cocktail]
                            cocktail_total = c_data['Τεμάχια'].sum()
                            
                            html_daily += f"""
                            <div class='cocktail-section'>
                                <h2 class='cocktail-header'>{cocktail}</h2>
                                <table>
                                    <thead>
                                        <tr>
                                            <th>LOT Number</th>
                                            <th>Πελάτης</th>
                                            <th>Ποσότητα (τμχ)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                            """
                            
                            for _, row in c_data.iterrows():
                                html_daily += f"""
                                    <tr>
                                        <td>{row['LOT_Cocktail']}</td>
                                        <td>{row['Πελάτης']}</td>
                                        <td>{row['Τεμάχια']}</td>
                                    </tr>
                                """
                            
                            html_daily += f"""
                                    <tr class='subtotal-row'>
                                        <td colspan='2' style='text-align: right;'>ΣΥΝΟΛΟ {cocktail}:</td>
                                        <td>{cocktail_total} τμχ</td>
                                    </tr>
                                </tbody>
                                </table>
                            </div>
                            """

                        grand_total = df_grouped['Τεμάχια'].sum()
                        html_daily += f"""
                            <div class='grand-total'>
                                ΓΕΝΙΚΟ ΣΥΝΟΛΟ ΠΑΡΑΓΩΓΗΣ ΗΜΕΡΑΣ: {grand_total} τμχ
                            </div>
                        </body>
                        </html>
                        """            
                        
                        # --- 3. ΣΥΓΚΕΝΤΡΩΤΙΚΗ ΛΙΣΤΑ ΠΡΩΤΩΝ ΥΛΩΝ (ΓΙΑ ΠΡΟΕΤΟΙΜΑΣΙΑ) ---
                        df_ingredients_total = view_df.groupby("Υλικό").agg({
                            "Σύνολο_ML": "sum",
                            "Στόχος_Γραμμάρια": "sum"
                        }).reset_index()

                        html_ing_list = f"""
                        <html>
                        <head>
                            <meta charset='UTF-8'>
                            <style>
                                body {{ font-family: 'Helvetica', sans-serif; padding: 30px; color: #2c3e50; }}
                                .header {{ text-align: center; border-bottom: 4px solid #2980b9; padding-bottom: 10px; margin-bottom: 30px; }}
                                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                                th {{ background-color: #2980b9; color: white; padding: 12px; text-align: left; }}
                                td {{ border: 1px solid #bdc3c7; padding: 10px; font-size: 14px; }}
                                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                                .total-row {{ font-weight: bold; background-color: #ecf0f1; }}
                                .unit {{ color: #7f8c8d; font-size: 12px; }}
                            </style>
                        </head>
                        <body>
                            <div class='header'>
                                <h1>📋 ΛΙΣΤΑ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ΠΡΩΤΩΝ ΥΛΩΝ</h1>
                                <p>Ημερομηνία Παραγωγής: <b>{sel_hist_date}</b></p>
                            </div>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Πρώτη Ύλη</th>
                                        <th>Συνολική Ποσότητα (ml)</th>
                                        <th>Συνολικό Βάρος (g)</th>
                                        <th>Συνολικό Βάρος (kg)</th>
                                    </tr>
                                </thead>
                                <tbody>
                        """

                        for _, row in df_ingredients_total.iterrows():
                            kg_val = row['Στόχος_Γραμμάρια'] / 1000
                            html_ing_list += f"""
                                <tr>
                                    <td><b>{row['Υλικό']}</b></td>
                                    <td>{row['Σύνολο_ML']:.0f} <span class='unit'>ml</span></td>
                                    <td>{row['Στόχος_Γραμμάρια']:.1f} <span class='unit'>g</span></td>
                                    <td><b>{kg_val:.3f}</b> <span class='unit'>kg</span></td>
                                </tr>
                            """

                        html_ing_list += """
                                </tbody>
                            </table>
                            <div style='margin-top: 40px; font-size: 12px; font-style: italic;'>
                                * Οι υπολογισμοί βάρους βασίζονται στην πυκνότητα κάθε υλικού όπως έχει οριστεί στις Πρώτες Ύλες.
                            </div>
                        </body>
                        </html>
                        """

                        # --- ΕΜΦΑΝΙΣΗ ΚΟΥΜΠΙΩΝ ΔΙΠΛΑ-ΔΙΠΛΑ (ΠΛΕΟΝ 3 ΚΟΥΜΠΙΑ) ---
                        st.divider()
                        col_p1, col_p2, col_p3 = st.columns(3)
                        with col_p1:
                            st.download_button("🖨️ Εκτύπωση Επαγγελματικού Δελτίου", data=html, file_name=f"Professional_Report_{sel_hist_date.replace('/','_')}.html", mime="text/html", use_container_width=True)
                        with col_p2:
                            st.download_button("📋 Εκτύπωση Ημερήσιας Παραγωγής", data=html_daily, file_name=f"Daily_Production_{sel_hist_date.replace('/','_')}.html", mime="text/html", use_container_width=True)
                        with col_p3:
                            st.download_button("🧪 Λίστα Πρώτων Υλών", data=html_ing_list, file_name=f"Ingredients_Needed_{sel_hist_date.replace('/','_')}.html", mime="text/html", use_container_width=True)
    else:
        st.info("Δεν βρέθηκαν αρχεία ιστορικού παραγωγής.")

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
import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- ΕΝΟΤΗΤΑ: ΣΥΝΤΗΡΗΣΗ & HACCP ---
# Υποθέτουμε ότι η σελίδα 'page' έχει επιλεγεί από το πλευρικό μενού
if page == "🧼 Συντήρηση & HACCP":
    st.header("🧼 Ημερολόγιο Συντήρησης & Καθαρισμού")

    # --- ΚΕΝΤΡΙΚΑ ΠΕΔΙΑ ΕΙΣΑΓΩΓΗΣ ---
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        # ΝΕΟ ΠΕΔΙΟ: Πληκτρολόγηση ονόματος υπευθύνου
        staff_name = st.text_input("👤 Ονοματεπώνυμο Υπευθύνου:", placeholder="π.χ. Νίκος Παπαδόπουλος")
    with col_u2:
        # ΕΠΙΛΟΓΗ ΗΜΕΡΟΜΗΝΙΑΣ (ηη/μμ/εε)
        selected_date = st.date_input("📅 Ημερομηνία Καταγραφής:", value=datetime.now())
        date_str = selected_date.strftime("%d/%m/%y")
    
    tab1, tab2, tab3 = st.tabs(["🌡️ Θερμοκρασίες", "🧹 Checklist Καθαρισμού", "📄 Εκτυπώσεις & Ιστορικό"])
    
    # --- TAB 1: ΘΕΡΜΟΚΡΑΣΙΕΣ ---
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
                    st.success(f"✅ Η μέτρηση για το {device} αποθηκεύτηκε!")

    # --- TAB 2: CHECKLIST ΚΑΘΑΡΙΣΜΟΥ (Ανά εργασία) ---
    with tab2:
        tasks_data = {
            "Ημερήσιο Checklist": ["Σκεύη & Εργαλεία", "Εξοπλισμός", "Επιφάνειες επαφής", "Δάπεδα παραγωγής", "Τουαλέτες", "Απορρίμματα"],
            "Εβδομαδιαίο Checklist": ["Δάπεδα αποθηκών", "Ψυγεία", "Τοίχοι", "Κάδοι", "Τζαμαρία", "Ράφια"],
            "Μηνιαίο Checklist": ["Παράθυρα", "Οροφές", "Φώτα", "Εξαερισμός"]
        }

        category = st.radio("Επιλέξτε τύπο εργασιών:", list(tasks_data.keys()), horizontal=True)
        current_tasks = tasks_data[category]
        responses = {}

        with st.form(f"form_{category}"):
            st.subheader(f"Καταγραφή: {category}")
            for task in current_tasks:
                c1, c2 = st.columns([0.4, 0.6])
                with c1:
                    done = st.checkbox(task, key=f"ch_{task}")
                with c2:
                    cleaner = st.text_input("Καθαριστικό:", key=f"cl_{task}", placeholder="π.χ. Χλωρίνη")
                responses[task] = {"done": done, "cleaner": cleaner}
            
            if st.form_submit_button("💾 Οριστικοποίηση"):
                if not staff_name.strip():
                    st.error("⚠️ Συμπληρώστε το όνομα υπευθύνου!")
                elif all(res["done"] for res in responses.values()) and all(res["cleaner"].strip() != "" for res in responses.values()):
                    summary_cleaners = " | ".join([f"{t}: {res['cleaner']}" for t, res in responses.items()])
                    log_data = {
                        "Ημερομηνία": date_str, "Ώρα": datetime.now().strftime("%H:%M"),
                        "Χρήστης": staff_name, "Τύπος": "Καθαρισμός",
                        "Στοιχείο": category, "Τιμή": "ΟΛΟΚΛΗΡΩΘΗΚΕ",
                        "Καθαριστικό": summary_cleaners, "Σημειώσεις": "-"
                    }
                    pd.DataFrame([log_data]).to_csv("HACCP_Log.csv", mode='a', header=not os.path.exists("HACCP_Log.csv"), index=False, encoding='utf-8-sig')
                    st.success("✨ Το checklist αποθηκεύτηκε με επιτυχία!")
                else:
                    st.error("⚠️ Πρέπει να ολοκληρώσετε όλες τις εργασίες και να γράψετε τα καθαριστικά!")

    # --- TAB 3: ΙΣΤΟΡΙΚΟ & ΕΚΤΥΠΩΣΕΙΣ ---
    with tab3:
        if os.path.exists("HACCP_Log.csv"):
            try:
                # Ορισμός στηλών για αποφυγή ParserError
                cols = ["Ημερομηνία", "Ώρα", "Χρήστης", "Τύπος", "Στοιχείο", "Τιμή", "Καθαριστικό", "Σημειώσεις"]
                df_haccp = pd.read_csv("HACCP_Log.csv", names=cols, header=0, on_bad_lines='skip', encoding='utf-8-sig').fillna("-")

                # ΣΥΝΑΡΤΗΣΗ ΕΚΤΥΠΩΣΗΣ (Με σωστές εσοχές)
                def generate_report(filter_type, title):
                    report_df = df_haccp[df_haccp["Στοιχείο"].astype(str).str.strip() == filter_type]
                    if report_df.empty:
                        return f"<html><body><h3>Δεν υπάρχουν δεδομένα για: {title}</h3></body></html>"
                    
                    html = f"""
                    <html><head><meta charset='UTF-8'><style>
                        table {{ width: 100%; border-collapse: collapse; }}
                        th, td {{ border: 1px solid black; padding: 8px; text-align: left; font-size: 12px; }}
                        th {{ background-color: #f2f2f2; }}
                    </style></head><body>
                    <h2 style='text-align:center;'>CABCLUB COCKTAILS</h2>
                    <h3 style='text-align:center;'>{title}</h3>
                    <p>Ημερομηνία Εκτύπωσης: {date_str}</p>
                    <table><tr><th>Ημερομηνία</th><th>Χρήστης</th><th>Κατάσταση</th><th>Καθαριστικά</th></tr>
                    """
                    for _, r in report_df.iterrows():
                        cleaners_fmt = str(r['Καθαριστικό']).replace(" | ", "<br>")
                        html += f"<tr><td>{r['Ημερομηνία']}</td><td>{r['Χρήστης']}</td><td>{r['Τιμή']}</td><td>{cleaners_fmt}</td></tr>"
                    html += "</table></body></html>"
                    return html

                # Κουμπιά Λήψης
                c_btn1, c_btn2, c_btn3 = st.columns(3)
                c_btn1.download_button("📄 Ημερήσια", generate_report("Ημερήσιο Checklist", "ΗΜΕΡΗΣΙΟ ΜΗΤΡΩΟ"), f"Daily_{date_str}.html", "text/html")
                c_btn2.download_button("📄 Εβδομαδιαία", generate_report("Εβδομαδιαίο Checklist", "ΕΒΔΟΜΑΔΙΑΙΟ ΜΗΤΡΩΟ"), f"Weekly_{date_str}.html", "text/html")
                c_btn3.download_button("📄 Μηνιαία", generate_report("Μηνιαίο Checklist", "ΜΗΝΙΑΙΟ ΜΗΤΡΩΟ"), f"Monthly_{date_str}.html", "text/html")

                st.divider()
                st.dataframe(df_haccp.sort_values(by="Ημερομηνία", ascending=False), use_container_width=True)
            except Exception as e:
                st.error(f"Σφάλμα ανάγνωσης αρχείου: {e}")
        else:
            st.info("ℹ️ Δεν υπάρχουν ακόμη καταγραφές.")
