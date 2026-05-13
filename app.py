import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime, timedelta
import plotly.express as px
import imaplib
import email
import time
from supabase import create_client, Client
import zipfile
import io

# --- Ρυθμίσεις Σελίδας ---
st.set_page_config(page_title="DC CABCLUB 2026", layout="wide", page_icon="🍸")

# --- ΣΥΝΔΕΣΗ ΜΕ SUPABASE ---
url: str = st.secrets["supabase"]["url"]
key: str = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

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

# --- Σύστημα Password ---
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

# Προσθήκη CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc; }
    div[data-testid="stMetric"] { background-color: #1e2129; border: 1px solid #333; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #3e4451; color: white; border: none; }
    .stButton>button:hover { border: 1px solid #00ffcc; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# Σταθερές
TOTAL_FIXED = 0.22  
TAX_RATES = {"Ελλάδα": 0.0245, "Γερμανία": 0.0130, "Κύπρος": 0.0096, "Ιταλία": 0.0104, "Bulgaria": 0.0056}

def format_greek(value):
    if isinstance(value, (int, float)):
        return "{:.3f}".format(value).replace('.', ',')
    return value

# --- ΣΥΝΑΡΤΗΣΕΙΣ ΦΟΡΤΩΣΗΣ ΔΕΔΟΜΕΝΩΝ (SUPABASE) ---
@st.cache_data(ttl=600) 
def load_all_ingredients():
    res = supabase.table("ingredients").select("*").order("name").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df = df.rename(columns={
            "id": "ID", "name": "Name", "price": "Price", "volume": "Volume", 
            "abv": "Αλκοόλ %", "weight_full": "Weight_Full"
        })
        df["Τιμή/ml"] = df["Price"] / df["Volume"]
        df["Απόθεμα (ml)"] = 0.0
        return df
    else:
        return pd.DataFrame(columns=["ID", "Name", "Price", "Volume", "Τιμή/ml", "Αλκοόλ %", "Weight_Full", "Απόθεμα (ml)"])

@st.cache_data(ttl=600)
def load_all_recipes():
    res_rec = supabase.table("recipes").select("*").order("name").execute()
    res_items = supabase.table("recipe_items").select("*").execute()
    
    if res_rec.data:
        df_rec = pd.DataFrame(res_rec.data)
        df_items = pd.DataFrame(res_items.data) if res_items.data else pd.DataFrame(columns=["recipe_id", "ingredient_name", "ml_per_unit"])
        
        reconstructed = []
        for _, row in df_rec.iterrows():
            rec_dict = {
                "Ονομα": row["name"],
                "Barcode": row["barcode"],
                "Τιμή Καταλόγου": row.get("catalog_price", 0.0)
            }
            items = df_items[df_items["recipe_id"] == row["id"]]
            for i, (_, item) in enumerate(items.iterrows(), start=1):
                rec_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = item["ingredient_name"]
                rec_dict[f"ML{i}"] = item["ml_per_unit"]
            reconstructed.append(rec_dict)
            
        return pd.DataFrame(reconstructed)
    else:
        cols_rec = ["Ονομα", "Barcode", "Τιμή Καταλόγου"] + [f"ΣΥΣΤΑΤΙΚΟ{i}" for i in range(1,14)] + [f"ML{i}" for i in range(1,14)]
        return pd.DataFrame(columns=cols_rec)

df_ing = load_all_ingredients()
df_rec = load_all_recipes()

ing_options = ["ΚΕΝΟ", "Νερό"] + sorted(df_ing["Name"].unique().tolist()) if not df_ing.empty else ["ΚΕΝΟ", "Νερό"]
recipe_options = sorted(df_rec["Ονομα"].unique().tolist()) if not df_rec.empty else []

# Υπολογισμός ώρας Ελλάδος (UTC + 3)
now_athens = datetime.utcnow() + timedelta(hours=3)

# ==========================================
# --- SIDEBAR (ΑΡΙΣΤΕΡΗ ΜΠΑΡΑ) ---
# ==========================================
with st.sidebar:
    # 1. Λογότυπο και Τίτλος
    st.image("https://cabclub.gr/wp-content/uploads/2021/12/logo.png", use_container_width=True)
    st.title("DC CABCLUB 2026 🏆")
    
    st.divider()

    # --- Live Status User Selection ---
    current_user = st.selectbox("👤 Είσαι ο:", ["Χρήστης Α", "Χρήστης Β"], key="user_select")
    update_live_status(current_user)
    online_user = get_who_is_online()

    if online_user and online_user != current_user:
        st.success(f"🟢 Ο {online_user} είναι online!")
    else:
        st.info("⚪️ Μόνος στην εφαρμογή")

    st.divider()

    # 2. Κεντρικό Μενού (Το key="main_page" το βοηθάει να μην "ξεχνάει" τη σελίδα στο refresh)
    page = st.radio(
        "Μενού:", 
        [
            "📦 Αποθήκη", "🔄 Αντικατάσταση", "📝 Νέα Συνταγή", "📊 Διαχείριση", 
            "🔍 Ανάλυση", "📊 Εμπορική Πολιτική", "📦 Παραγγελίες B2B", 
            "📦 Lot Παραγωγής", "📈 Dashboard", "👥 Πελατολόγιο", "🧼 Συντήρηση & HACCP"
        ],
        key="main_page"
    )

    st.divider()

    # 3. Επιλογή Χώρας για ΕΦΚ (Με key για να μην χάνει την επιλογή)
    country = st.selectbox("Χώρα για ΕΦΚ:", list(TAX_RATES.keys()), key="selected_country")
    tax_factor = TAX_RATES[country]

    st.divider()

    # 4. Εργαλεία Διαχείρισης (Refresh & Backup)
    st.subheader("⚙️ Διαχείριση")
    
    if st.button("🔄 Ανανέωση Δεδομένων", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- Πλήρες Backup ZIP ---
    try:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            tables = {
                "Production_LOT": "production_log",
                "B2B_Orders": "b2b_orders",
                "Inventory": "ingredients",
                "HACCP_Log": "haccp_log", 
                "Recipes": "recipes"
            }
            for file_label, table_name in tables.items():
                try:
                    res = supabase.table(table_name).select("*").execute()
                    df_temp = pd.DataFrame(res.data) if res.data else pd.DataFrame()
                    csv_data = df_temp.to_csv(index=False).encode('utf-8-sig')
                    zf.writestr(f"{file_label}_{now_athens.strftime('%d_%m_%Y')}.csv", csv_data)
                except:
                    continue # Αν ένας πίνακας έχει πρόβλημα, πάμε στον επόμενο
        
        st.download_button(
            label="📥 Λήψη Όλων των Δεδομένων (.zip)",
            data=buf.getvalue(),
            file_name=f"FULL_BACKUP_CABCLUB_{now_athens.strftime('%d_%m_%Y')}.zip",
            mime="application/zip",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Σφάλμα Backup: {e}")

    st.divider()
    st.write(f"🕒 Ώρα Ελλάδος: {now_athens.strftime('%H:%M:%S')}")
    st.write(f"📅 Ημερομηνία: {now_athens.strftime('%d/%m/%Y')}")

# ==========================================
# ΑΠΟ ΕΔΩ ΚΑΙ ΚΑΤΩ ΞΕΚΙΝΑΕΙ ΤΟ ΜΕΝΟΥ (Αποθήκη κ.λπ.)
# (Δηλαδή το αμέσως επόμενο είναι: if page == "📦 Αποθήκη":)
# ==========================================
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
                    try:
                        # Το ID μπαίνει αυτόματα από τη Supabase (SERIAL)
                        supabase.table("ingredients").insert({
                            "name": new_name,
                            "price": new_price,
                            "volume": new_vol,
                            "abv": new_alc,
                            "weight_full": new_weight
                        }).execute()
                        
                        st.success(f"✅ Το υλικό '{new_name}' προστέθηκε στη βάση!")
                        st.cache_data.clear() # Καθαρίζουμε τη μνήμη για να φέρει τα νέα δεδομένα
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Σφάλμα κατά την αποθήκευση (Ίσως υπάρχει ήδη;): {e}")
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
                    
                    # --- Ο ΝΕΟΣ ΚΩΔΙΚΑΣ UPDATE ---
                    if col_btn1.form_submit_button("Update ✅"):
                        try:
                            # 1. Ενημέρωση στην Αποθήκη (Supabase)
                            supabase.table("ingredients").update({
                                "name": edit_name,
                                "price": edit_price,
                                "volume": edit_vol,
                                "abv": edit_alc,
                                "weight_full": edit_weight
                            }).eq("id", int(curr_row["ID"])).execute()

                            # 2. Ενημέρωση στις Συνταγές (Αν άλλαξε το όνομα)
                            if ing_to_edit != edit_name:
                                # Η Supabase βρίσκει και ενημερώνει όλα τα υλικά με αυτό το όνομα με 1 εντολή!
                                supabase.table("recipe_items").update({
                                    "ingredient_name": edit_name
                                }).eq("ingredient_name", ing_to_edit).execute()
                                st.info("⚙️ Το νέο όνομα ενημερώθηκε αυτόματα και στις συνταγές!")

                            st.success(f"✅ Το υλικό '{edit_name}' ενημερώθηκε!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα κατά την ενημέρωση: {e}")

                    # --- Ο ΝΕΟΣ ΚΩΔΙΚΑΣ ΔΙΑΓΡΑΦΗΣ ---
                    if col_btn2.form_submit_button("Διαγραφή 🗑️"):
                        try:
                            supabase.table("ingredients").delete().eq("id", int(curr_row["ID"])).execute()
                            st.warning(f"Το υλικό {ing_to_edit} διαγράφηκε.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα κατά τη διαγραφή: {e}")

    # --- TAB 3: ΠΡΟΒΟΛΗ ΠΙΝΑΚΑ & HTML ---
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


# --- 2. ΝΕΑ ΣΥΝΤΑΓΗ (SUPABASE EDITION) ---
elif page == "📝 Νέα Συνταγή":
    st.header("📝 Προσθήκη Νέας Συνταγής (Cocktail)")

    with st.form("new_recipe_form", clear_on_submit=True):
        st.subheader("Βασικά Στοιχεία")
        col1, col2 = st.columns(2)
        new_rec_name = col1.text_input("Όνομα Cocktail", placeholder="π.χ. CabClub Margarita")
        new_barcode = col2.text_input("Barcode / Κωδικός", placeholder="Προαιρετικό")
        
        st.divider()
        st.subheader("🧪 Υλικά & Ποσότητες")
        
        # Δημιουργούμε πεδία για 13 υλικά (για να ταιριάζει με το παλιό σου σύστημα)
        ingredients_data = []
        cols_ing = st.columns(2)
        
        for i in range(1, 14):
            with cols_ing[i % 2]:  # Μοιράζουμε τα πεδία σε 2 στήλες για οικονομία χώρου
                c_ing, c_ml = st.columns([2, 1])
                # Το ing_options φορτώνεται στην αρχή του app.py από την Supabase!
                ing_val = c_ing.selectbox(f"Συστατικό {i}", options=ing_options, key=f"ing_{i}")
                ml_val = c_ml.number_input(f"ML {i}", min_value=0.0, step=0.5, key=f"ml_{i}")
                
                # Αν έχει επιλεγεί υλικό και έχει μπει ποσότητα, το κρατάμε στη λίστα
                if ing_val and ing_val != "ΚΕΝΟ" and ml_val > 0:
                    ingredients_data.append({"name": ing_val, "ml": ml_val})

        st.divider()
        submitted = st.form_submit_button("💾 Αποθήκευση Συνταγής", type="primary")

        if submitted:
            if not new_rec_name:
                st.error("❌ Πρέπει να δώσετε όνομα στο Cocktail!")
            elif not ingredients_data:
                st.error("❌ Πρέπει να προσθέσετε τουλάχιστον 1 υλικό με ποσότητα μεγαλύτερη από 0.")
            else:
                try:
                    # ΒΗΜΑ 1: Δημιουργία της Συνταγής (Title) στον πίνακα 'recipes'
                    res = supabase.table("recipes").insert({
                        "name": new_rec_name.strip(),
                        "barcode": new_barcode.strip() if new_barcode else ""
                    }).execute()
                    
                    # Παίρνουμε το ID που της έδωσε αυτόματα η βάση (π.χ. ID 5)
                    new_recipe_id = res.data[0]["id"]
                    
                    # ΒΗΜΑ 2: Αποθήκευση των Υλικών στον πίνακα 'recipe_items'
                    items_to_insert = []
                    for item in ingredients_data:
                        items_to_insert.append({
                            "recipe_id": new_recipe_id,
                            "ingredient_name": item["name"],
                            "ml_per_unit": float(item["ml"])
                        })
                    
                    # Τα στέλνουμε όλα μαζί στη βάση με μια κίνηση!
                    supabase.table("recipe_items").insert(items_to_insert).execute()
                    
                    st.success(f"✅ Η συνταγή '{new_rec_name}' αποθηκεύτηκε επιτυχώς με {len(items_to_insert)} υλικά!")
                    st.balloons()
                    st.cache_data.clear() # Καθαρίζουμε τη μνήμη για να τη δει αμέσως στα άλλα μενού
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    # Το πιο πιθανό σφάλμα εδώ είναι να υπάρχει ήδη συνταγή με το ίδιο όνομα (UNIQUE constraint)
                    st.error(f"⚠️ Σφάλμα αποθήκευσης. Ίσως υπάρχει ήδη συνταγή με αυτό το όνομα! Λεπτομέρειες: {e}")

# --- 5. ΔΙΑΧΕΙΡΙΣΗ ΣΥΝΤΑΓΩΝ (SUPABASE EDITION) ---
elif page == "📊 Διαχείριση":
    st.header("📊 Επεξεργασία & Διαγραφή Συνταγών")

    # --- ΜΑΓΙΚΟ ΚΟΥΜΠΙ ΓΙΑ ΜΕΤΑΦΟΡΑ ΠΑΛΙΩΝ ΣΥΝΤΑΓΩΝ (ΠΡΟΣΩΡΙΝΟ) ---
    with st.expander("🚀 Εισαγωγή παλιών συνταγών από CSV"):
        st.info("Ανέβασε το αρχείο με τις συνταγές σου για να περαστούν μαζικά στη Supabase.")
        uploaded_rec = st.file_uploader("Ανέβασε το DB_RECIPES.csv", type="csv")
        if uploaded_rec and st.button("Μεταφορά Συνταγών Τώρα!", type="primary"):
            try:
                temp_df = pd.read_csv(uploaded_rec)
                for _, row in temp_df.iterrows():
                    name = str(row.get("Ονομα", "")).strip()
                    barcode = str(row.get("Barcode", "")).replace(".0", "").replace("nan", "")
                    price = float(row.get("Τιμή Καταλόγου", 0.0)) if pd.notna(row.get("Τιμή Καταλόγου")) else 0.0
                    
                    if name:
                        # 1. Φτιάχνουμε τη συνταγή
                        res = supabase.table("recipes").insert({"name": name, "barcode": barcode, "catalog_price": price}).execute()
                        rec_id = res.data[0]["id"]
                        
                        # 2. Περνάμε τα υλικά της
                        items_to_insert = []
                        for i in range(1, 14):
                            ing = str(row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ")).strip()
                            ml = float(row.get(f"ML{i}", 0.0)) if pd.notna(row.get(f"ML{i}")) else 0.0
                            if ing and ing != "ΚΕΝΟ" and ing != "nan" and ml > 0:
                                items_to_insert.append({
                                    "recipe_id": rec_id,
                                    "ingredient_name": ing,
                                    "ml_per_unit": ml
                                })
                        if items_to_insert:
                            supabase.table("recipe_items").insert(items_to_insert).execute()
                st.success("🎉 Όλες οι συνταγές μεταφέρθηκαν!")
                st.balloons()
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Σφάλμα: {e}")

    # Ζητάμε τα βασικά στοιχεία όλων των συνταγών από τη Supabase
    res_rec = supabase.table("recipes").select("*").order("name").execute()
    
    if not res_rec.data:
        st.info("Δεν βρέθηκαν αποθηκευμένες συνταγές. Πηγαίνετε στη 'Νέα Συνταγή' ή κάντε Εισαγωγή από πάνω.")
    else:
        df_recipes_base = pd.DataFrame(res_rec.data)
        
        # 1. Επιλογή Cocktail
        recipe_to_edit = st.selectbox(
            "Αναζήτηση Cocktail:", 
            options=df_recipes_base["name"].tolist(),
            index=None,
            placeholder="Επιλέξτε ένα Cocktail..."
        )
        
        if recipe_to_edit:
            # Βρίσκουμε τη γραμμή της επιλεγμένης συνταγής
            rec_row = df_recipes_base[df_recipes_base["name"] == recipe_to_edit].iloc[0]
            rec_id = int(rec_row["id"])
            
            # Βρίσκουμε τα υλικά
            res_items = supabase.table("recipe_items").select("*").eq("recipe_id", rec_id).execute()
            items_data = res_items.data if res_items.data else []
            
            tab_edit, tab_del = st.tabs(["📝 Επεξεργασία Στοιχείων", "🗑️ Διαγραφή Συνταγής"])
            
            with tab_edit:
                with st.form(f"form_{rec_id}"): 
                    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                    edit_name = col_h1.text_input("Όνομα Cocktail", value=str(rec_row["name"]))
                    
                    current_barcode = str(rec_row.get("barcode", ""))
                    if current_barcode == "None" or current_barcode == "nan": current_barcode = ""
                    edit_barcode = col_h2.text_input("Barcode Shop", value=current_barcode)
                    
                    current_price = float(rec_row.get("catalog_price", 0.0)) if rec_row.get("catalog_price") else 0.0
                    edit_price = col_h3.number_input("Τιμή Καταλόγου (€)", value=current_price, step=0.10)
                    
                    st.write("---")
                    c1, c2 = st.columns(2)
                    
                    new_ingredients_list = []
                    
                    # Καθαρισμός επιλογών για να μην σκάσει με κενά (όπως το είχες)
                    clean_options = [str(opt).strip() for opt in ing_options]
                    
                    for i in range(1, 14):
                        target_col = c1 if i <= 7 else c2
                        with target_col:
                            val_from_db = "ΚΕΝΟ"
                            ml_from_db = 0.0
                            if i - 1 < len(items_data):
                                val_from_db = items_data[i-1]["ingredient_name"].strip()
                                ml_from_db = float(items_data[i-1]["ml_per_unit"])
                            
                            try:
                                current_idx = clean_options.index(val_from_db)
                            except ValueError:
                                current_idx = 0
                            
                            sub_c1, sub_c2 = st.columns([2, 1])
                            
                            ing_val = sub_c1.selectbox(
                                f"Υλικό {i}", 
                                options=ing_options, 
                                index=current_idx, 
                                key=f"s_{i}_{rec_id}"
                            )
                            ml_val = sub_c2.number_input(
                                f"ML {i}", 
                                value=ml_from_db,
                                min_value=0.0,
                                step=0.5,
                                key=f"m_{i}_{rec_id}"
                            )
                            new_ingredients_list.append({"name": ing_val, "ml": ml_val})

                    if st.form_submit_button("💾 Αποθήκευση Αλλαγών"):
                        try:
                            supabase.table("recipes").update({
                                "name": edit_name.strip(),
                                "barcode": edit_barcode.strip(),
                                "catalog_price": edit_price
                            }).eq("id", rec_id).execute()
                            
                            supabase.table("recipe_items").delete().eq("recipe_id", rec_id).execute()
                            
                            items_to_insert = []
                            for item in new_ingredients_list:
                                if item["name"] and item["name"] != "ΚΕΝΟ" and item["ml"] > 0:
                                    items_to_insert.append({
                                        "recipe_id": rec_id,
                                        "ingredient_name": item["name"],
                                        "ml_per_unit": float(item["ml"])
                                    })
                            
                            if items_to_insert:
                                supabase.table("recipe_items").insert(items_to_insert).execute()
                            
                            st.success(f"✅ Η συνταγή '{edit_name}' ενημερώθηκε!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Σφάλμα: {e}")

            with tab_del:
                st.warning(f"⚠️ Είστε σίγουροι ότι θέλετε να διαγράψετε το **{recipe_to_edit}**;")
                if st.button(f"🗑️ Οριστική Διαγραφή", key=f"del_{rec_id}", type="primary"):
                    supabase.table("recipes").delete().eq("id", rec_id).execute()
                    st.error(f"❌ Η συνταγή διαγράφηκε.")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()

        st.write("---")
        with st.expander("📋 Προεπισκόπηση Όλων των Συνταγών (Πίνακας)"):
            # --- ΜΑΓΕΙΑ: Φτιάχνουμε το df_rec δυναμικά από τη Supabase! ---
            all_items = supabase.table("recipe_items").select("*").execute().data
            df_rec_list = []
            for _, r in df_recipes_base.iterrows():
                row_dict = {
                    "Ονομα": r["name"],
                    "Barcode": str(r.get("barcode", "")).replace(".0", "").replace("nan", ""),
                    "Τιμή Καταλόγου": r.get("catalog_price", 0.0)
                }
                r_items = [item for item in all_items if item["recipe_id"] == r["id"]]
                for i in range(1, 14):
                    if i - 1 < len(r_items):
                        row_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = r_items[i-1]["ingredient_name"]
                        row_dict[f"ML{i}"] = r_items[i-1]["ml_per_unit"]
                    else:
                        row_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = "ΚΕΝΟ"
                        row_dict[f"ML{i}"] = 0.0
                df_rec_list.append(row_dict)
            
            df_rec = pd.DataFrame(df_rec_list)
            st.dataframe(df_rec, use_container_width=True)

# --- 4. ΑΝΑΛΥΣΗ (ΔΙΟΡΘΩΜΕΝΗ ΓΙΑ ΣΥΜΒΑΤΟΤΗΤΑ ΜΕ SUPABASE) ---
elif page == "🔍 Ανάλυση":
    st.header("🔍 Οικονομική Ανάλυση & Κερδοφορία")
    
    # --- ΜΑΓΕΙΑ SUPABASE: Φτιάχνουμε τα df_ing & df_rec όπως ακριβώς τα περιμένει ο κώδικάς σου! ---
    # 1. Φόρτωση Αποθήκης
    res_ing = supabase.table("ingredients").select("*").execute()
    ing_data = res_ing.data if res_ing.data else []
    df_ing_list = []
    for item in ing_data:
        df_ing_list.append({
            "Name": item["name"],
            "Price": item["price"],
            "Volume": item["volume"],
            "Αλκοόλ %": item["abv"],
            "ABV": item["abv"], # Το χρειάζεται το HTML book πιο κάτω
            "Τιμή/ml": item["price"] / item["volume"] if item["volume"] > 0 else 0
        })
    df_ing = pd.DataFrame(df_ing_list)

    # 2. Φόρτωση & Μετατροπή Συνταγών (σε οριζόντια μορφή με 13 υλικά)
    res_rec_base = supabase.table("recipes").select("*").order("name").execute()
    rec_data = res_rec_base.data if res_rec_base.data else []
    all_items = supabase.table("recipe_items").select("*").execute().data if rec_data else []
    
    df_rec_list = []
    for r in rec_data:
        row_dict = {
            "Ονομα": r["name"],
            "Barcode": str(r.get("barcode", "")).replace(".0", "").replace("nan", ""),
            "Τιμή Καταλόγου": r.get("catalog_price", 0.0)
        }
        r_items = [item for item in all_items if item["recipe_id"] == r["id"]]
        for i in range(1, 14):
            if i - 1 < len(r_items):
                row_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = r_items[i-1]["ingredient_name"]
                row_dict[f"ML{i}"] = r_items[i-1]["ml_per_unit"]
            else:
                row_dict[f"ΣΥΣΤΑΤΙΚΟ{i}"] = "ΚΕΝΟ"
                row_dict[f"ML{i}"] = 0.0
        df_rec_list.append(row_dict)
    df_rec = pd.DataFrame(df_rec_list)
    # --- ΤΕΛΟΣ ΦΟΡΤΩΣΗΣ SUPABASE ---

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
                    # Αναζήτηση στην Αποθήκη
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
        
        # Πρόβλεψη αν το tax_factor δεν έχει οριστεί
        try: efk_informational = pure_alc_ml * tax_factor
        except NameError: efk_informational = pure_alc_ml * 0.0255
        
        try: fixed_cost = TOTAL_FIXED
        except NameError: fixed_cost = 0.50
        
        total_production = raw_cost + fixed_cost 
        
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
        k3.metric("Σταθερά Έξοδα", f"{fixed_cost:.2f} €".replace('.', ','))
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

        # --- 📜 ΕΝΟΤΗΤΑ ΕΞΑΓΩΓΗΣ ΕΠΑΓΓΕΛΜΑΤΙΚΟΥ REPORT (HTML) ---
        st.divider()
        st.subheader("📜 Εξαγωγή Τεχνικού Φακέλου")

        # 1. Εύρεση του Barcode
        try:
            current_barcode = df_rec[df_rec['Ονομα'] == choice]['Barcode'].values[0]
            if not current_barcode or str(current_barcode).lower() == 'nan':
                current_barcode = "Δεν ορίστηκε"
        except:
            current_barcode = "Δεν βρέθηκε"

        # 2. Υπολογισμός τιμών αντιπροσώπου (βάσει του -26% που είπαμε)
        p_agent = p_retail * 0.74
        profit_agent = p_agent - total_production

        # 3. Δημιουργία των γραμμών του πίνακα συστατικών για το HTML
        ingredients_rows = ""
        for item in breakdown:
            ingredients_rows += f"""
            <tr>
                <td>{item['Υλικό']}</td>
                <td style='text-align:right;'>{item['ML']:g} ml</td>
                <td style='text-align:right;'>{item.get('Alc %', 0):g}%</td>
                <td style='text-align:right;'>{item['Κόστος']:.3f} €</td>
            </tr>
            """

        # --- ΤΟ HTML TEMPLATE ---
        report_html = f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; line-height: 1.5; padding: 30px; }}
                .report-card {{ max-width: 800px; margin: auto; border: 1px solid #eee; padding: 40px; border-radius: 15px; box-shadow: 0 0 20px rgba(0,0,0,0.05); }}
                .header {{ text-align: center; border-bottom: 3px solid #d32f2f; padding-bottom: 20px; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; color: #d32f2f; font-size: 28px; text-transform: uppercase; }}
                .meta-info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                .meta-item {{ font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
                th {{ background-color: #34495e; color: white; padding: 12px; text-align: left; font-size: 13px; }}
                td {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 13px; }}
                .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .stat-box {{ padding: 15px; border-radius: 8px; background: #2c3e50; color: white; }}
                .stat-label {{ font-size: 11px; text-transform: uppercase; opacity: 0.8; }}
                .stat-value {{ font-size: 18px; font-weight: bold; color: #00ffcc; }}
                .footer {{ margin-top: 40px; text-align: center; font-size: 11px; color: #95a5a6; border-top: 1px solid #eee; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <div class='report-card'>
                <div class='header'>
                    <h1>CABCLUB COCKTAILS</h1>
                    <div style='font-size: 12px; color: #7f8c8d;'>ΤΕΧΝΙΚΟ ΔΕΛΤΙΟ & ΑΝΑΛΥΣΗ ΚΟΣΤΟΥΣ</div>
                </div>

                <div class='meta-info'>
                    <div class='meta-item'><strong>Cocktail:</strong> {choice}</div>
                    <div class='meta-item'><strong>Barcode:</strong> {current_barcode}</div>
                    <div class='meta-item'><strong>Συνολικά ML:</strong> {total_ml_cocktail:g} ml</div>
                    <div class='meta-item'><strong>Αλκοόλ (ABV):</strong> {final_abv:g}%</div>
                    <div class='meta-item'><strong>Ημερομηνία:</strong> {datetime.now().strftime('%d/%m/%Y')}</div>
                </div>

                <h3 style='color: #2c3e50; border-left: 4px solid #d32f2f; padding-left: 10px;'>📋 Συνταγή</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Υλικό</th>
                            <th style='text-align:right;'>Ποσότητα</th>
                            <th style='text-align:right;'>ABV</th>
                            <th style='text-align:right;'>Κόστος</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ingredients_rows}
                    </tbody>
                </table>

                <h3 style='color: #2c3e50; border-left: 4px solid #d32f2f; padding-left: 10px;'>💰 Οικονομικά Στοιχεία</h3>
                <div class='summary-grid'>
                    <div class='stat-box'>
                        <div class='stat-label'>Κόστος Παραγωγής</div>
                        <div class='stat-value'>{total_production:.2f} €</div>
                    </div>
                    <div class='stat-box'>
                        <div class='stat-label'>Margin Λιανικής</div>
                        <div class='stat-value'>{margin_retail:.1f}%</div>
                    </div>
                    <div class='stat-box' style='background: #f1f2f6; color: #2c3e50;'>
                        <div class='stat-label' style='color: #7f8c8d;'>Κέρδος Λιανικής</div>
                        <div class='stat-value' style='color: #2c3e50;'>{profit_retail:.2f} €</div>
                        <div style='font-size: 9px;'>Τιμή: {p_retail:.2f} €</div>
                    </div>
                    <div class='stat-box' style='background: #f1f2f6; color: #2c3e50;'>
                        <div class='stat-label' style='color: #7f8c8d;'>Κέρδος Αντιπροσώπου</div>
                        <div class='stat-value' style='color: #2c3e50;'>{profit_agent:.2f} €</div>
                        <div style='font-size: 9px;'>Τιμή: {p_agent:.2f} €</div>
                    </div>
                </div>

                <div class='footer'>
                    Το παρόν έγγραφο αποτελεί πνευματική ιδιοκτησία της CABCLUB.<br>
                    Υπολογισμένο με σταθερά έξοδα μονάδας {fixed_cost:g} €.
                </div>
            </div>
        </body>
        </html>
        """

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            st.info(f"Το επαγγελματικό report για το {choice} είναι έτοιμο για λήψη.")
        with col_btn2:
            st.download_button(
                label="📥 Λήψη Report (HTML)",
                data=report_html,
                file_name=f"Report_{choice.replace(' ', '_')}.html",
                mime="text/html",
                key="html_report_download"
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
                    # Καθαρισμός των ML σε περίπτωση που έχουν κόμμα αντί για τελεία
                    ml_str = str(recipe.get(f"ML{i}", 0)).replace(',', '.')
                    ml = float(ml_str)
                except:
                    ml = 0
                
                ing_clean = raw_ing.strip()
                ing_check = ing_clean.upper()
                
                if ing_clean and ing_check not in ["NAN", "ΚΕΝΟ", "ΚΕΝΟ.", "-", "NONE", "0", "NULL"] and ml > 0:
                    # ΑΛΛΑΓΗ: Βάλαμε .2f για να δείχνει 2 δεκαδικά ψηφία και στα ml (π.χ. 22.50 ml)
                    html_book += f"<tr><td class='ing-name'>{ing_clean}</td><td>{ml:.2f} ml</td></tr>"
                    found_ingredients += 1
                    
                    # Προσθέτουμε ΠΑΝΤΑ τα ml στο σύνολο του cocktail
                    total_ml_cocktail += ml
                    
                    if not df_ing.empty and ing_clean in df_ing["Name"].values:
                        ing_row = df_ing[df_ing["Name"] == ing_clean].iloc[0]
                        
                        try:
                            # Παίρνουμε την τιμή (ABV ή Αλκοόλ)
                            raw_abv = str(ing_row.get("ABV", ing_row.get("Αλκοόλ", 0)))
                            # Καθαρίζουμε κόμματα και σύμβολα %
                            clean_abv = raw_abv.replace(',', '.').replace('%', '').strip()
                            abv = float(clean_abv)
                            
                            # ΑΝ ΤΟ ΕΧΕΙΣ ΠΕΡΑΣΕΙ ΩΣ 0.4 ΑΝΤΙ ΓΙΑ 40, ΤΟ ΦΤΙΑΧΝΕΙ ΑΥΤΟΜΑΤΑ
                            if 0 < abv <= 1.0:
                                abv = abv * 100
                                
                        except:
                            abv = 0
                        
                        try:
                            price = float(str(ing_row.get("Price", 0)).replace(',', '.'))
                            vol = float(str(ing_row.get("Volume", 700)).replace(',', '.'))
                            cost_per_ml = price / vol if vol > 0 else 0
                        except:
                            cost_per_ml = 0
                            
                        # Υπολογισμός καθαρών ml αλκοόλ και κόστους
                        total_alcohol_ml += ml * (abv / 100)
                        total_cost += ml * cost_per_ml
            
            if found_ingredients == 0:
                html_book += "<tr><td colspan='2'><i>Δεν έχουν καταχωρηθεί συστατικά.</i></td></tr>"

            # --- Ο ΣΩΣΤΟΣ ΤΥΠΟΣ ΥΠΟΛΟΓΙΣΜΟΥ ABV ---
            final_abv = (total_alcohol_ml / total_ml_cocktail * 100) if total_ml_cocktail > 0 else 0
            
            suggested_price = float(str(recipe.get("Τιμή Καταλόγου", 0.0)).replace(',', '.'))

            html_book += f"""
                    </tbody>
                </table>
                <div class='analysis-box'>
                    <span style='font-size:16px;'>Αλκοόλ (ABV): <b>{final_abv:.2f}%</b></span>
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
# --- 7. DASHBOARD (ΔΙΟΡΘΩΜΕΝΟ ΚΟΣΤΟΣ & ΚΕΡΔΟΣ) ---
elif page == "📈 Dashboard":
    st.header("📈 Business Analytics & Πωλήσεις")
    
    import plotly.express as px

    # 1. ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ
    with st.spinner("Ενημέρωση στατιστικών..."):
        res_log = supabase.table("production_log").select("*").execute()
        res_rec = supabase.table("recipes").select("id, name, catalog_price").execute()
        res_ing = supabase.table("ingredients").select("name, price, volume").execute()
        res_items = supabase.table("recipe_items").select("recipe_id, ingredient_name, ml_per_unit").execute()
        
    if res_log.data and res_rec.data:
        df_raw = pd.DataFrame(res_log.data)
        df_recipes = pd.DataFrame(res_rec.data)
        
        # Καθαρισμός δεδομένων πωλήσεων
        df_sales = df_raw.drop_duplicates(subset=["prod_date", "prod_time", "customer", "cocktail_name", "lot_cocktail"]).copy()
        df_sales['Date_Obj'] = pd.to_datetime(df_sales['prod_date'], format='%d/%m/%Y', errors='coerce')
        df_sales['Month_Year'] = df_sales['Date_Obj'].dt.strftime('%m/%Y')

        # --- ΦΙΛΤΡΑ ---
        st.markdown("### 🎯 Φίλτρα Ανάλυσης")
        col_f1, col_f2 = st.columns(2)
        all_customers = ["ΟΛΟΙ ΟΙ ΠΕΛΑΤΕΣ"] + sorted(df_sales['customer'].dropna().unique().tolist())
        sel_customer = col_f1.selectbox("👤 Πελάτης:", options=all_customers)
        all_months = ["ΟΛΟΙ ΟΙ ΜΗΝΕΣ"] + sorted(df_sales['Month_Year'].dropna().unique().tolist(), reverse=True)
        sel_month = col_f2.selectbox("📅 Μήνας:", options=all_months)
        
        df_filtered = df_sales.copy()
        if sel_customer != "ΟΛΟΙ ΟΙ ΠΕΛΑΤΕΣ":
            df_filtered = df_filtered[df_filtered['customer'] == sel_customer]
        if sel_month != "ΟΛΟΙ ΟΙ ΜΗΝΕΣ":
            df_filtered = df_filtered[df_filtered['Month_Year'] == sel_month]

        # --- ΥΠΟΛΟΓΙΣΜΟΣ ΚΟΣΤΟΥΣ ΑΝΑ ΣΥΝΤΑΓΗ ---
        df_ing = pd.DataFrame(res_ing.data)
        df_ing['cost_per_ml'] = pd.to_numeric(df_ing['price'], errors='coerce') / pd.to_numeric(df_ing['volume'], errors='coerce')
        ing_cost_dict = dict(zip(df_ing['name'], df_ing['cost_per_ml']))

        df_items = pd.DataFrame(res_items.data)
        
        # Υπολογισμός κόστους ανά recipe_id
        recipe_costs_by_id = {}
        for rid in df_items['recipe_id'].unique():
            sub = df_items[df_items['recipe_id'] == rid]
            cost = 0.22  # Σταθερά έξοδα
            for _, item in sub.iterrows():
                cost += item['ml_per_unit'] * ing_cost_dict.get(item['ingredient_name'], 0)
            recipe_costs_by_id[rid] = cost

        # Δημιουργία mapping: Cocktail Name -> Unit Cost
        # Συνδέουμε το ID της συνταγής με το Όνομά της
        name_to_cost = {}
        for _, r in df_recipes.iterrows():
            name_to_cost[r['name']] = recipe_costs_by_id.get(r['id'], 0)

        # --- ΥΠΟΛΟΓΙΣΜΟΣ ΟΙΚΟΝΟΜΙΚΩΝ ΣΤΟ FILTERED DF ---
        # Φέρνουμε την τιμή λιανικής
        df_filtered = df_filtered.merge(df_recipes[['name', 'catalog_price']], left_on="cocktail_name", right_on="name", how="left")
        
        df_filtered['catalog_price'] = pd.to_numeric(df_filtered['catalog_price'], errors='coerce').fillna(0)
        df_filtered['dealer_price'] = df_filtered['catalog_price'] * 0.74
        df_filtered['Revenue'] = df_filtered['pieces'] * df_filtered['dealer_price']
        
        # Εφαρμογή κόστους βάσει ονόματος cocktail
        df_filtered['unit_cost'] = df_filtered['cocktail_name'].map(name_to_cost).fillna(0)
        df_filtered['Total_Cost'] = df_filtered['pieces'] * df_filtered['unit_cost']
        df_filtered['Profit'] = df_filtered['Revenue'] - df_filtered['Total_Cost']

        # Τελικά νούμερα
        total_rev = df_filtered['Revenue'].sum()
        total_cost = df_filtered['Total_Cost'].sum()
        total_profit = df_filtered['Profit'].sum()
        total_units = df_filtered['pieces'].sum()
        total_orders = len(df_filtered)

        # --- ΣΥΝΟΨΗ (METRICS) ---
        st.divider()
        st.subheader(f"📊 Σύνοψη: {sel_customer if sel_customer != 'ΟΛΟΙ ΟΙ ΠΕΛΑΤΕΣ' else 'Όλοι οι Πελάτες'}")
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("💰 Τζίρος (Dealer)", f"{total_rev:.2f} €".replace('.', ','))
        m2.metric("📉 Κόστος Υλικών", f"{total_cost:.2f} €".replace('.', ','))
        
        margin = (total_profit / total_rev * 100) if total_rev > 0 else 0
        m3.metric("📈 Καθαρό Κέρδος", f"{total_profit:.2f} €".replace('.', ','), 
                  delta=f"{margin:.1f}% Margin", delta_color="normal")
        
        m4.metric("🍹 Τεμάχια", f"{int(total_units)} τμχ")
        m5.metric("📦 Παραγγελίες", total_orders)

        # --- 8. ABC ΑΝΑΛΥΣΗ ---
        st.divider()
        st.subheader("🏆 ABC Ανάλυση Πελατολογίου")
        customer_abc = df_filtered.groupby("customer")["Revenue"].sum().sort_values(ascending=False).reset_index()
        if not customer_abc.empty and total_rev > 0:
            customer_abc['Percentage'] = (customer_abc['Revenue'] / total_rev) * 100
            customer_abc['CumSum'] = customer_abc['Percentage'].cumsum()
            customer_abc['Category'] = customer_abc['CumSum'].apply(lambda x: "A" if x <= 80 else ("B" if x <= 95 else "C"))
            
            fig_abc = px.bar(customer_abc, x="customer", y="Revenue", color="Category",
                           title="Ranking Πελατών", text_auto='.2s',
                           color_discrete_map={"A": "#00ffcc", "B": "#f1c40f", "C": "#ff4b4b"})
            st.plotly_chart(fig_abc, use_container_width=True)

        # --- 9. ΧΑΡΤΗΣ ΑΠΟΔΟΣΗΣ (HEATMAP) ---
        st.divider()
        st.subheader("🎯 Χάρτης Απόδοσης Cocktail")
        
        # Προετοιμασία δεδομένων για το γράφημα
        heatmap_list = []
        for name in df_filtered['cocktail_name'].unique():
            temp = df_filtered[df_filtered['cocktail_name'] == name]
            sold = temp['pieces'].sum()
            rev = temp['Revenue'].sum()
            cost = temp['Total_Cost'].sum()
            prof = rev - cost
            if sold > 0:
                heatmap_list.append({
                    "Cocktail": name,
                    "Πωλήσεις": sold,
                    "Κέρδος/Τμχ": round(prof/sold, 2),
                    "Συνολικό Κέρδος": round(prof, 2)
                })
        
        if heatmap_list:
            df_hm = pd.DataFrame(heatmap_list)
            fig_hm = px.scatter(df_hm, x="Πωλήσεις", y="Κέρδος/Τμχ", size="Συνολικό Κέρδος",
                               color="Cocktail", hover_name="Cocktail", text="Cocktail",
                               size_max=50, template="plotly_dark")
            fig_hm.update_traces(textposition='top center')
            st.plotly_chart(fig_hm, use_container_width=True)

        # --- ΑΝΑΛΥΤΙΚΟΣ ΠΙΝΑΚΑΣ ---
        with st.expander("📄 Αναλυτικό Αρχείο"):
            st.dataframe(df_filtered[["prod_date", "customer", "cocktail_name", "pieces", "Revenue", "Total_Cost", "Profit", "lot_cocktail"]].sort_values("prod_date", ascending=False), use_container_width=True)

    else:
       
# --- 8. LOT ΠΑΡΑΓΩΓΗΣ ---
elif page == "📦 Lot Παραγωγής":
    st.header("📦 Αναλυτικό Δελτίο Παραγωγής & Ιχνηλασιμότητα")

    # --- ΒΟΗΘΗΤΙΚΗ ΣΥΝΑΡΤΗΣΗ: ΑΣΦΑΛΗΣ ΜΕΤΑΤΡΟΠΗ ML ---
    def get_recipe_ml(row_series, idx):
        raw_val = None
        exact_key = f"ML{idx}"
        
        if exact_key in row_series:
            raw_val = row_series[exact_key]
        else:
            target = exact_key.lower()
            for col in row_series.index:
                if str(col).lower().replace(" ", "").replace("_", "") == target:
                    raw_val = row_series[col]
                    break
        
        if raw_val is None or pd.isna(raw_val):
            return 0.0
            
        try:
            val_str = str(raw_val).replace(',', '.').replace(' ', '')
            return float(val_str) if val_str else 0.0
        except Exception:
            return 0.0

    # --- 100% ΑΣΦΑΛΗΣ ΜΝΗΜΗ ΕΦΑΡΜΟΓΗΣ ---
    if 'active_b2b_order' not in st.session_state:
        st.session_state['active_b2b_order'] = None
    if 'lot_reset_key' not in st.session_state:
        st.session_state['lot_reset_key'] = 0

    active_order = st.session_state.get('active_b2b_order')
    reset_key = st.session_state['lot_reset_key']

    # --- ΕΚΚΡΕΜΟΤΗΤΕΣ ΑΠΟ B2B ---
    st.subheader("📋 Εκκρεμείς Παραγγελίες Πελατών (B2B)")
    res_b2b = supabase.table("b2b_orders").select("*").in_("status", ["ΝΕΑ", "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ"]).execute()
    
    if res_b2b.data:
        df_pending = pd.DataFrame(res_b2b.data)
        for _, order in df_pending.iterrows():
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(f"**Πελάτης:** {order['customer_name']} | **Προϊόντα:** {order['order_details'].replace('•', '')}")
            with col_b:
                if st.button("📥 Φόρτωση", key=f"load_{order['id']}"):
                    st.session_state['active_b2b_order'] = order.to_dict() 
                    st.success(f"Φορτώθηκε η παραγγελία του {order['customer_name']}!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.write("✅ Καμία εκκρεμής παραγγελία.")

    if active_order is not None:
        if st.button("❌ Ακύρωση Φόρτωσης"):
            st.session_state['active_b2b_order'] = None
            st.rerun()

    st.divider()

    # 1. ΚΕΝΤΡΙΚΟΣ ΟΡΙΣΜΟΣ ΗΜΕΡΟΜΗΝΙΑΣ & LOT
    col_date1, col_date2 = st.columns([2, 1])
    with col_date1:
        selected_date = st.date_input("📅 Ημερομηνία LOT", value=datetime.now(), format="DD/MM/YYYY")
    with col_date2:
        prod_day = st.text_input("Ημερομηνία Παραγωγής", value=datetime.now().strftime('%d'), max_chars=2)

    formatted_date = selected_date.strftime('%d/%m/%Y')
    date_lot_label = f"{formatted_date}-{prod_day}" 
    current_time = datetime.now().strftime('%H:%M')

    st.divider()

    # --- ΑΥΤΟΜΑΤΗ ΑΝΑΓΝΩΣΗ ΠΑΡΑΓΓΕΛΙΑΣ ---
    default_cocktails_list = []
    default_quantities = {}
    
    if active_order is not None and not df_rec.empty:
        details = active_order.get('order_details', '')
        lines = details.split('\n')
        for line in lines:
            try:
                parts = line.split('x ')
                qty = int(parts[0].replace('•', '').strip())
                c_name = parts[1].split(' (')[0].strip()
                if c_name in df_rec["Ονομα"].unique():
                    default_cocktails_list.append(c_name)
                    default_quantities[c_name] = qty
            except Exception:
                pass

    # 2. ΦΟΡΜΑ ΠΑΡΑΓΩΓΗΣ
    if not df_rec.empty:
        selected_cocktails = st.multiselect("Επιλέξτε Προϊόντα:", options=df_rec["Ονομα"].unique(), default=default_cocktails_list)

        if selected_cocktails:
            st.subheader(f"⚖️ Οδηγίες Ζύγισης (LOT: {date_lot_label})")
            
            # --- ΒΗΜΑ 1: ΚΑΤΑΝΟΜΗ ΤΕΜΑΧΙΩΝ ΑΝΑ ΠΕΛΑΤΗ ---
            st.markdown("### 🔢 1. Τεμάχια Παραγωγής & Πελάτες")
            st.info("💡 Πατήστε το '+' κάτω από κάθε πίνακα για να προσθέσετε κι άλλο πελάτη στο ίδιο κοκτέιλ.")
            
            all_assignments = {}
            default_global_cust = active_order.get('customer_name', '') if active_order else ""

            for name in selected_cocktails:
                st.markdown(f"**🍹 {name}**")
                init_data = [{"Πελάτης": default_global_cust, "Τεμάχια": default_quantities.get(name, 1)}]
                df_init = pd.DataFrame(init_data)
                
                edited_df = st.data_editor(
                    df_init,
                    num_rows="dynamic",
                    key=f"editor_{name}_{reset_key}",
                    use_container_width=True,
                    column_config={
                        "Τεμάχια": st.column_config.NumberColumn(min_value=1, step=1, default=1),
                        "Πελάτης": st.column_config.TextColumn()
                    }
                )
                all_assignments[name] = edited_df

            # --- ΒΗΜΑ 2: ΥΠΟΛΟΓΙΣΜΟΣ ΜΟΝΑΔΙΚΩΝ ΥΛΙΚΩΝ ΚΑΙ ΣΥΝΟΛΙΚΩΝ ML ---
            ing_totals = {}
            for cocktail_name in selected_cocktails:
                df_assign = all_assignments[cocktail_name]
                # ΑΣΦΑΛΗΣ ΕΛΕΓΧΟΣ ΓΙΑ ΑΠΟΦΥΓΗ KeyError: 'Τεμάχια'
                total_qty_for_cocktail = df_assign["Τεμάχια"].sum() if "Τεμάχια" in df_assign.columns else 0
                
                if total_qty_for_cocktail > 0:
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    for i in range(1, 14):
                        ing = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        if ing not in ["ΚΕΝΟ", "nan", "Νερό", ""]:
                            ml_u = get_recipe_ml(recipe_row, i)
                            ing_totals[ing] = ing_totals.get(ing, 0.0) + (ml_u * total_qty_for_cocktail)

            # --- ΚΕΝΤΡΙΚΗ ΦΟΡΜΑ ΗΜΕΡΗΣΙΩΝ LOT ---
            st.markdown("### 🔄 2. Συνολικά LOT Πρώτων Υλών Ημέρας")
            st.info("Δείτε τα συνολικά ml που απαιτούνται. Πληκτρολογήστε το LOT και θα περαστεί αυτόματα στις συνταγές!")
            
            with st.expander("📋 Πίνακας Μοναδικών Υλικών & Συνολικών Ποσοτήτων", expanded=True):
                mh = st.columns([2, 1, 1.5, 1.5])
                mh[0].caption("ΠΡΩΤΗ ΥΛΗ")
                mh[1].caption("ΣΥΝΟΛΟ (ml)")
                mh[2].caption("LOT ΗΜΕΡΑΣ")
                mh[3].caption("ΛΗΞΗ ΗΜΕΡΑΣ")
                
                for ing in sorted(ing_totals.keys()):
                    mr = st.columns([2, 1, 1.5, 1.5])
                    mr[0].write(f"**{ing}**")
                    mr[1].write(f"**{ing_totals[ing]:.0f} ml**")
                    mr[2].text_input("LOT", key=f"mlot_{ing}_{reset_key}", label_visibility="collapsed")
                    mr[3].text_input("EXP", key=f"mexp_{ing}_{reset_key}", label_visibility="collapsed")

            # --- ΒΗΜΑ 3: ΑΝΑΛΥΤΙΚΗ ΦΟΡΜΑ & ΟΡΙΣΤΙΚΟΠΟΙΗΣΗ ---
            st.markdown("### 🏷️ 3. Αναλυτικό Δελτίο & Οριστικοποίηση")
            lot_entries = []
            
            with st.form(f"detailed_lot_form_{reset_key}"):
                for cocktail_name in selected_cocktails:
                    recipe_row = df_rec[df_rec["Ονομα"] == cocktail_name].iloc[0]
                    df_assign = all_assignments[cocktail_name]
                    
                    # ΑΣΦΑΛΗΣ ΕΛΕΓΧΟΣ
                    total_qty_this = df_assign["Τεμάχια"].sum() if "Τεμάχια" in df_assign.columns else 0
                    
                    if total_qty_this == 0:
                        st.warning(f"⚠️ Δεν έχετε ορίσει τεμάχια για το {cocktail_name}.")
                        continue

                    st.markdown(f"#### 🍹 {cocktail_name} (Σύνολο: {total_qty_this} τμχ)")
                    h = st.columns([2, 1, 1, 1.2, 1.2, 1.2, 1.2])
                    for col, label in zip(h, ["Υλικό", "ml", "Βάρος(g)", "Lot 1", "Λήξη 1", "Lot 2", "Λήξη 2"]): col.caption(label)
                    
                    for i in range(1, 14):
                        ing = str(recipe_row.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        if ing in ["ΚΕΝΟ", "nan", "Νερό", ""]: continue
                        
                        ml_u = get_recipe_ml(recipe_row, i)
                        tot_ml = ml_u * total_qty_this
                        tg_g = tot_ml
                        match_ing = df_ing[df_ing["Name"] == ing]
                        if not match_ing.empty:
                            tg_g = (tot_ml / match_ing.iloc[0]["Volume"]) * match_ing.iloc[0]["Weight_Full"]

                        r = st.columns([2, 1, 1, 1.2, 1.2, 1.2, 1.2])
                        r[0].write(f"**{ing}**")
                        r[1].write(f"{tot_ml:.0f}")
                        r[2].markdown(f"**{tg_g:.1f}g**")
                        
                        m_lot = st.session_state.get(f"mlot_{ing}_{reset_key}", "")
                        m_exp = st.session_state.get(f"mexp_{ing}_{reset_key}", "")
                        
                        l1 = r[3].text_input("L1", key=f"l1_{cocktail_name}_{i}_{reset_key}", placeholder=m_lot, label_visibility="collapsed")
                        e1 = r[4].text_input("E1", key=f"e1_{cocktail_name}_{i}_{reset_key}", placeholder=m_exp, label_visibility="collapsed")
                        l2 = r[5].text_input("L2", key=f"l2_{cocktail_name}_{i}_{reset_key}", label_visibility="collapsed")
                        e2 = r[6].text_input("E2", key=f"e2_{cocktail_name}_{i}_{reset_key}", label_visibility="collapsed")

                        val_l1 = l1.strip() if l1.strip() else m_lot.strip()
                        val_e1 = e1.strip() if e1.strip() else m_exp.strip()
                        val_l2 = l2.strip()
                        val_e2 = e2.strip()

                        final_lot = val_l1 if not val_l2 else f"{val_l1} / {val_l2}"
                        final_exp = val_e1 if not val_e2 else f"{val_e1} / {val_e2}"

                        # ΔΗΜΙΟΥΡΓΙΑ ΕΓΓΡΑΦΩΝ ΓΙΑ ΚΑΘΕ ΠΕΛΑΤΗ ΞΕΧΩΡΙΣΤΑ
                        for _, row_assign in df_assign.iterrows():
                            c_name = str(row_assign.get("Πελάτης", "Λιανική / Άγνωστος")).strip()
                            if not c_name: c_name = "Λιανική / Άγνωστος"
                            
                            c_qty = int(row_assign.get("Τεμάχια", 0))
                            
                            if c_qty > 0:
                                lot_entries.append({
                                    "prod_date": formatted_date, "prod_time": current_time, "customer": c_name,
                                    "cocktail_name": cocktail_name, "lot_cocktail": date_lot_label, "pieces": c_qty,
                                    "ingredient_name": ing, "total_ml": float(ml_u * c_qty), 
                                    "target_g": round(float((ml_u * c_qty) / match_ing.iloc[0]["Volume"] * match_ing.iloc[0]["Weight_Full"]), 1) if not match_ing.empty else float(ml_u * c_qty),
                                    "lot_number": final_lot, 
                                    "expiry_date": final_exp
                                })
                
                st.divider()
                if st.form_submit_button("💾 Οριστικοποίηση & Αποθήκευση στο Cloud", type="primary"):
                    if lot_entries:
                        try:
                            supabase.table("production_log").insert(lot_entries).execute()
                            
                            if active_order is not None:
                                supabase.table("b2b_orders").update({"status": "ΟΛΟΚΛΗΡΩΘΗΚΕ"}).eq("id", active_order['id']).execute()
                                st.session_state['active_b2b_order'] = None 
                            
                            st.session_state['lot_reset_key'] += 1
                            
                            st.success("✅ Η παρτίδα αποθηκεύτηκε επιτυχώς! Τα LOT και οι Ημερομηνίες καταχωρήθηκαν σωστά.")
                            st.cache_data.clear()
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα κατά την αποθήκευση: {e}")
                            
    # --- 4. ΙΣΤΟΡΙΚΟ & ΔΙΑΧΕΙΡΙΣΗ ---
    st.divider()
    st.subheader("📂 Ιστορικό Παραγωγής & Εκτυπώσεις")
    
    res_log = supabase.table("production_log").select("*").order("prod_date", desc=True).execute()
    if res_log.data:
        df_all_logs = pd.DataFrame(res_log.data)
        df_all_logs_renamed = df_all_logs.rename(columns={
            "prod_date": "Ημερομηνία", "prod_time": "Ώρα", "customer": "Πελάτης", "cocktail_name": "Cocktail",
            "lot_cocktail": "LOT_Cocktail", "pieces": "Τεμάχια", "ingredient_name": "Υλικό",
            "total_ml": "Σύνολο_ML", "target_g": "Στόχος_Γραμμάρια", "lot_number": "Lot Number", "expiry_date": "Ημ_Λήξης"
        })

        all_dates = sorted(df_all_logs_renamed["Ημερομηνία"].unique(), reverse=True)
        sel_hist_date = st.selectbox("🔍 Επιλέξτε Ημερομηνία για Διαχείριση / Εκτύπωση:", all_dates)
        
        if sel_hist_date:
            df_past = df_all_logs_renamed[df_all_logs_renamed["Ημερομηνία"] == sel_hist_date]
            
            batches = df_past.groupby(['Ώρα', 'Πελάτης', 'Cocktail', 'LOT_Cocktail']).groups
            options = ["-- Επιλέξτε Παραγωγή --"]
            batch_mapping = {}
            for (time_v, cust, cock, lot_c), indices in batches.items():
                label = f"🍹 {cock} | 👤 {cust} | 🕒 {time_v} | LOT: {lot_c}"
                options.append(label)
                batch_mapping[label] = list(indices)

            selected_batch = st.selectbox("🛠️ Επεξεργασία Συγκεκριμένης Παραγωγής (Προσθήκη LOT 2):", options)
            
            if selected_batch != "-- Επιλέξτε Παραγωγή --":
                batch_id = str(hash(selected_batch))
                row_indices = batch_mapping[selected_batch]
                base_data = df_past.loc[row_indices[0]]
                old_pieces = int(base_data["Τεμάχια"])
                
                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1.5])
                new_cust = c1.text_input("Πελάτης", value=base_data["Πελάτης"], key=f"ed_cust_{batch_id}")
                
                cocktail_list = list(df_rec["Ονομα"].unique())
                try: current_idx = cocktail_list.index(base_data["Cocktail"])
                except: current_idx = 0
                
                new_cock = c2.selectbox("Cocktail", options=cocktail_list, index=current_idx, key=f"ed_cock_{batch_id}")
                new_pcs = c3.number_input("Τεμάχια", value=old_pieces, min_value=1, key=f"ed_pcs_{batch_id}")
                new_lot_c = c4.text_input("LOT", value=base_data["LOT_Cocktail"], key=f"ed_lot_{batch_id}")

                cocktail_changed = (new_cock != base_data["Cocktail"])
                display_ingredients = []
                if cocktail_changed:
                    new_r = df_rec[df_rec["Ονομα"] == new_cock].iloc[0]
                    for i in range(1, 14):
                        ing_n = str(new_r.get(f"ΣΥΣΤΑΤΙΚΟ{i}", "ΚΕΝΟ"))
                        if ing_n not in ["ΚΕΝΟ", "nan", ""]:
                            ml_calc = get_recipe_ml(new_r, i) * new_pcs
                            display_ingredients.append({"Υλικό": ing_n, "ML": ml_calc, "Lot": "", "Exp": ""})
                else:
                    for idx in row_indices:
                        r_d = df_past.loc[idx]
                        mult = new_pcs / old_pieces
                        display_ingredients.append({"Υλικό": r_d["Υλικό"], "ML": r_d["Σύνολο_ML"] * mult, "Lot": r_d["Lot Number"], "Exp": r_d["Ημ_Λήξης"]})

                with st.form(f"edit_batch_form_{batch_id}"):
                    h_edit = st.columns([2, 1, 1.2, 1.2, 1.2, 1.2])
                    h_labels = ["Υλικό", "ml", "Lot 1", "Λήξη 1", "Lot 2", "Λήξη 2"]
                    for col, label in zip(h_edit, h_labels):
                        col.caption(label)

                    final_updated = []
                    for i, itm in enumerate(display_ingredients):
                        raw_lot = str(itm["Lot"])
                        raw_exp = str(itm["Exp"])
                        
                        lot_parts = raw_lot.split(" / ") if " / " in raw_lot else [raw_lot, ""]
                        exp_parts = raw_exp.split(" / ") if " / " in raw_exp else [raw_exp, ""]
                        while len(lot_parts) < 2: lot_parts.append("")
                        while len(exp_parts) < 2: exp_parts.append("")

                        r = st.columns([2, 1, 1.2, 1.2, 1.2, 1.2])
                        r[0].write(f"**{itm['Υλικό']}**")
                        r[1].write(f"{itm['ML']:.0f}")
                        
                        lt1 = r[2].text_input("L1", value=lot_parts[0], key=f"ed_l1_{batch_id}_{i}", label_visibility="collapsed")
                        ex1 = r[3].text_input("E1", value=exp_parts[0], key=f"ed_e1_{batch_id}_{i}", label_visibility="collapsed")
                        lt2 = r[4].text_input("L2", value=lot_parts[1], key=f"ed_l2_{batch_id}_{i}", label_visibility="collapsed")
                        ex2 = r[5].text_input("E2", value=exp_parts[1], key=f"ed_e2_{batch_id}_{i}", label_visibility="collapsed")
                        
                        final_lot = lt1 if not lt2 else f"{lt1} / {lt2}"
                        final_exp = ex1 if not ex2 else f"{ex1} / {ex2}"
                        
                        final_updated.append({
                            "ing": itm["Υλικό"], "ml": itm["ML"], "lot": final_lot, "exp": final_exp
                        })
                    
                    st.divider()
                    b_save, b_del = st.columns(2)
                    
                    if b_save.form_submit_button("💾 Αποθήκευση Αλλαγών (Προσθήκη LOT 2)", type="primary"):
                        ids_to_del = df_all_logs.loc[row_indices, "id"].tolist()
                        for di in ids_to_del: supabase.table("production_log").delete().eq("id", di).execute()
                        
                        new_batch = []
                        for fd in final_updated:
                            g_calc = fd["ml"]
                            match_i = df_ing[df_ing["Name"] == fd["ing"]]
                            if not match_i.empty: 
                                g_calc = (fd["ml"] / match_i.iloc[0]["Volume"]) * match_i.iloc[0]["Weight_Full"]
                            
                            new_batch.append({
                                "prod_date": base_data["Ημερομηνία"], "prod_time": base_data["Ώρα"], "customer": new_cust if new_cust.strip() else "Άγνωστος", 
                                "cocktail_name": new_cock, "lot_cocktail": new_lot_c, "pieces": int(new_pcs), 
                                "ingredient_name": fd["ing"], "total_ml": fd["ml"], "target_g": round(g_calc, 1), 
                                "lot_number": fd["lot"], "expiry_date": fd["exp"]
                            })
                        supabase.table("production_log").insert(new_batch).execute()
                        st.success("✅ Ενημερώθηκε!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()

                    if b_del.form_submit_button("🗑️ Διαγραφή Παραγωγής"):
                        ids_to_del = df_all_logs.loc[row_indices, "id"].tolist()
                        for di in ids_to_del: supabase.table("production_log").delete().eq("id", di).execute()
                        st.warning("Διαγράφηκε!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
            st.divider()
            
            # --- 🛠️ ΕΠΑΝΑΦΟΡΑ HTML REPORTS (YELLOW, RED & BLUE THEMES) ---
            # 1. ΕΠΑΓΓΕΛΜΑΤΙΚΟ ΔΕΛΤΙΟ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑΣ
            html_pro = f"""
            <html>
            <head><meta charset='UTF-8'><style>
                body {{ font-family: sans-serif; color: #333; }}
                .document-header {{ text-align: center; border-bottom: 2px solid #444; padding-bottom: 10px; }}
                .customer-section {{ background-color: #f2f2f2; padding: 10px; border: 1px solid #ccc; margin-top: 20px; }}
                .cocktail-title {{ color: #d32f2f; border-left: 5px solid #d32f2f; padding-left: 10px; margin: 15px 0 5px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
                th {{ background-color: #444; color: white; padding: 8px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 6px; }}
            </style></head>
            <body><div class='document-header'><h1>CABCLUB COCKTAILS</h1><h2>ΔΕΛΤΙΟ ΠΑΡΑΓΩΓΗΣ & ΙΧΝΗΛΑΣΙΜΟΤΗΤΑΣ</h2><p>Ημερομηνία: <b>{sel_hist_date}</b></p></div>
            """
            for p in df_past["Πελάτης"].unique():
                p_df = df_past[df_past["Πελάτης"] == p]
                html_pro += f"<div class='customer-section'><strong>ΠΕΛΑΤΗΣ:</strong> {p}</div>"
                for cock in p_df["Cocktail"].unique():
                    c_df = p_df[p_df["Cocktail"] == cock]
                    c_lot = c_df["LOT_Cocktail"].iloc[0] # ΤΟ ΣΩΣΤΟ LOT ΑΝΑ COCKTAIL
                    html_pro += f"<h3 class='cocktail-title'>{cock}</h3><p style='font-size:12px;margin:0;'>Ποσότητα: <b>{c_df['Τεμάχια'].iloc[0]} τμχ</b> | LOT: <b>{c_lot}</b></p>"
                    html_pro += "<table><thead><tr><th>Πρώτη Ύλη</th><th>Σύνολο ml</th><th>Βάρος (g)</th><th>Lot Number</th><th>Ημ. Λήξης</th></tr></thead><tbody>"
                    for _, row in c_df.iterrows():
                        html_pro += f"<tr><td><b>{row['Υλικό']}</b></td><td>{row['Σύνολο_ML']:.0f}</td><td>{row['Στόχος_Γραμμάρια']}g</td><td>{row['Lot Number']}</td><td>{row['Ημ_Λήξης']}</td></tr>"
                    html_pro += "</tbody></table>"
            html_pro += "</body></html>"

            # --- 2. ΗΜΕΡΗΣΙΟ ΦΥΛΛΟ ΠΑΡΑΓΩΓΗΣ (RED THEME) ---
            df_daily = df_past.drop_duplicates(subset=["Πελάτης", "Cocktail", "LOT_Cocktail"])
            
            # Υπολογισμός Γενικού Συνόλου Ημέρας
            grand_total_pcs = df_daily["Τεμάχια"].sum()

            html_daily = f"""
            <html><head><meta charset='UTF-8'><style>
                body {{ font-family: sans-serif; padding: 20px; }}
                .header {{ text-align: center; border-bottom: 3px solid #d32f2f; margin-bottom: 30px; }}
                .cocktail-header {{ background-color: #d32f2f; color: white; padding: 10px; margin-top: 20px; border-radius: 5px 5px 0 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                th {{ background-color: #444; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 10px; border: 1px solid #ddd; }}
                .grand-total {{ 
                    margin-top: 30px; 
                    padding: 20px; 
                    background-color: #f8f9fa; 
                    border: 2px solid #d32f2f; 
                    text-align: center; 
                    font-size: 1.4em; 
                    border-radius: 10px;
                }}
                .grand-total b {{ color: #d32f2f; font-size: 1.6em; }}
            </style></head>
            <body>
                <div class='header'>
                    <h1>📋 ΗΜΕΡΗΣΙΟ ΦΥΛΛΟ ΠΑΡΑΓΩΓΗΣ</h1>
                    <p>Ημερομηνία: <b>{sel_hist_date}</b></p>
                </div>
            """
            
            for cock in df_daily["Cocktail"].unique():
                c_data = df_daily[df_daily["Cocktail"] == cock]
                html_daily += f"""
                <h2 class='cocktail-header'>🍹 {cock}</h2>
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
                    html_daily += f"<tr><td>{row['LOT_Cocktail']}</td><td>{row['Πελάτης']}</td><td>{row['Τεμάχια']}</td></tr>"
                
                # Υποσύνολο ανά Cocktail
                html_daily += f"""
                    <tr style='background:#f9f9f9; font-weight:bold;'>
                        <td colspan='2' style='text-align: right;'>ΜΕΡΙΚΟ ΣΥΝΟΛΟ {cock}:</td>
                        <td>{c_data['Τεμάχια'].sum()} τμχ</td>
                    </tr>
                </tbody></table>
                """

            # Προσθήκη του Γενικού Συνόλου στο τέλος της σελίδας
            html_daily += f"""
                <div class='grand-total'>
                    ΣΥΝΟΛΙΚΗ ΠΑΡΑΓΩΓΗ ΗΜΕΡΑΣ ({sel_hist_date}):<br>
                    <b>{grand_total_pcs} Τεμάχια</b>
                </div>
            </body></html>
            """
            # --- 3. ΛΙΣΤΑ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ΥΛΙΚΩΝ (BLUE THEME) ---
            # Συγκεντρώνουμε τα δεδομένα ανά υλικό, αθροίζοντας ποσότητες και ενώνοντας τα μοναδικά LOT/Λήξεις
            # Χρησιμοποιούμε πιο αυστηρό φιλτράρισμα για να αγνοούμε κενά ή "None"
            df_prep = df_past.groupby("Υλικό").agg({
                "Σύνολο_ML": "sum", 
                "Στόχος_Γραμμάρια": "sum",
                "Lot Number": lambda x: " / ".join(sorted(set(str(v).strip() for v in x if v and str(v).lower() not in ['none', '', 'nan']))),
                "Ημ_Λήξης": lambda x: " / ".join(sorted(set(str(v).strip() for v in x if v and str(v).lower() not in ['none', '', 'nan'])))
            }).reset_index()

            html_prep = f"""
            <html><head><meta charset='UTF-8'><style>
                body {{ font-family: sans-serif; padding: 30px; }}
                .header {{ text-align: center; border-bottom: 4px solid #2980b9; margin-bottom: 30px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background-color: #2980b9; color: white; padding: 12px; text-align: left; }}
                td {{ border: 1px solid #bdc3c7; padding: 10px; }}
                .lot-info {{ font-size: 0.9em; color: #555; }}
            </style></head>
            <body>
                <div class='header'>
                    <h1>🧪 ΛΙΣΤΑ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ΥΛΙΚΩΝ</h1>
                    <p>Ημερομηνία: <b>{sel_hist_date}</b></p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Πρώτη Ύλη</th>
                            <th>Συνολική Ποσότητα (ml)</th>
                            <th>Συνολικό Βάρος (g)</th>
                            <th>Lot & Λήξη Πρ. Ύλης</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for _, row in df_prep.iterrows():
                # ΔΙΟΡΘΩΜΕΝΗ ΛΟΓΙΚΗ: Δημιουργία κειμένου με ό,τι είναι διαθέσιμο (Lot ή/και Λήξη)
                display_parts = []
                if row['Lot Number']: 
                    display_parts.append(row['Lot Number'])
                if row['Ημ_Λήξης']: 
                    display_parts.append(row['Ημ_Λήξης'])
                
                # Αν υπάρχουν στοιχεία τα ενώνουμε με |, αλλιώς βάζουμε παύλα
                lot_text = " | ".join(display_parts) if display_parts else "-"
                
                html_prep += f"""
                    <tr>
                        <td><b>{row['Υλικό']}</b></td>
                        <td>{row['Σύνολο_ML']:.0f} ml</td>
                        <td>{row['Στόχος_Γραμμάρια']:.1f} g</td>
                        <td class='lot-info'>{lot_text}</td>
                    </tr>
                """
            html_prep += "</tbody></table></body></html>"

            # --- ΤΟΠΟΘΕΤΗΣΗ ΚΟΥΜΠΙΩΝ DOWNLOAD ---
            col_p1, col_p2, col_p3 = st.columns(3)
            col_p1.download_button("🖨️ Δελτίο Ιχνηλασιμότητας", data=html_pro, file_name=f"Trace_{sel_hist_date}.html", mime="text/html", use_container_width=True)
            col_p2.download_button("📋 Ημερήσια Παραγωγή", data=html_daily, file_name=f"Daily_{sel_hist_date}.html", mime="text/html", use_container_width=True)
            col_p3.download_button("🧪 Λίστα Προετοιμασίας", data=html_prep, file_name=f"Prep_{sel_hist_date}.html", mime="text/html", use_container_width=True)
        # --- 5. ΣΥΝΘΕΤΗ ΙΧΝΗΛΑΣΙΜΟΤΗΤΑ & RECALL TOOL ---
    st.divider()
    st.subheader("🔍 Έλεγχος & Ιχνηλασιμότητα")
    
    # 1. Ανάκτηση όλων των δεδομένων από τη Supabase
    res_all = supabase.table("production_log").select("*").execute()
    
    if res_all.data:
        # Μετατροπή σε DataFrame και μετονομασία στηλών (όπως το είχες)
        df_all = pd.DataFrame(res_all.data).rename(columns={
            "prod_date": "Ημερομηνία",
            "customer": "Πελάτης",
            "cocktail_name": "Cocktail",
            "lot_cocktail": "LOT_Cocktail",
            "ingredient_name": "Υλικό",
            "lot_number": "Lot Number",
            "pieces": "Τεμάχια"
        })

        # Δημιουργία Tabs για οργάνωση
        tab_filter, tab_recall_tool = st.tabs(["📋 Αναζήτηση & Φίλτρα", "🚨 Recall Tool (Ανάκληση)"])

        with tab_filter:
            # Ο ΠΑΛΙΟΣ ΣΟΥ ΚΩΔΙΚΑΣ ΜΕ ΤΑ ΦΙΛΤΡΑ
            with st.expander("⚙️ Ρυθμίσεις Φίλτρων (Πελάτης, Υλικά, Lot)"):
                f1, f2, f3 = st.columns(3)
                search_cust = f1.multiselect("Πελάτης:", sorted(df_all["Πελάτης"].unique()), key="filter_cust")
                search_cock = f2.multiselect("Cocktail:", sorted(df_all["Cocktail"].unique()), key="filter_cock")
                search_ing = f3.multiselect("Πρώτη Ύλη:", sorted(df_all["Υλικό"].unique()), key="filter_ing")
                search_lot = st.text_input("🔢 Αναζήτηση βάσει οποιουδήποτε LOT:", placeholder="π.χ. 040526 ή L123...", key="filter_lot_txt")

            # Εφαρμογή Φίλτρων
            dff = df_all.copy()
            if search_cust: dff = dff[dff["Πελάτης"].isin(search_cust)]
            if search_cock: dff = dff[dff["Cocktail"].isin(search_cock)]
            if search_ing: dff = dff[dff["Υλικό"].isin(search_ing)]
            if search_lot:
                dff = dff[dff.apply(lambda x: search_lot.lower() in str(x).lower(), axis=1)]

            st.write(f"Αποτελέσματα: **{len(dff)}** εγγραφές")
            st.dataframe(dff, use_container_width=True, hide_index=True)

            # Κουμπιά Εξαγωγής (HTML/CSV) που ήδη είχες
            if not dff.empty:
                # ... (εδώ παραμένει ο κώδικας για το trace_html που έχεις ήδη) ...
                # Σημείωση: Κράτα τον κώδικα του trace_html και τα download_buttons εδώ
                pass 

        with tab_recall_tool:
            # Η ΝΕΑ ΛΕΙΤΟΥΡΓΙΑ ΑΝΑΚΛΗΣΗΣ
            st.markdown("#### 🚨 Εργαλείο Άμεσης Ανάκλησης")
            st.write("Αν ένας προμηθευτής αναφέρει πρόβλημα σε ένα υλικό, βάλτε το **Lot Number του υλικού** παρακάτω.")
            
            recall_lot = st.text_input("Εισάγετε το Lot Number της Πρώτης Ύλης:", placeholder="π.χ. LOT-GIN-2024", key="recall_input")
            
            if recall_lot:
                # Φιλτράρουμε τις εγγραφές που περιέχουν ΑΥΤΟ το lot πρώτης ύλης
                # Στη βάση σου το πεδίο είναι το "lot_number" (το μενομάσαμε σε "Lot Number" στο df)
                df_affected = df_all[df_all["Lot Number"] == recall_lot]
                
                if not df_affected.empty:
                    st.error(f"⚠️ **Βρέθηκαν {len(df_affected)} εγγραφές παραγωγής** που περιέχουν αυτό το υλικό!")
                    
                    # Πίνακας με τα επηρεαζόμενα Cocktail και Πελάτες
                    st.dataframe(
                        df_affected[["Ημερομηνία", "Πελάτης", "Cocktail", "LOT_Cocktail", "Τεμάχια"]],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Συγκεντρωτική λίστα πελατών για τηλέφωνα
                    affected_cust_list = df_affected["Πελάτης"].unique().tolist()
                    st.warning(f"📞 **Πελάτες που πρέπει να ενημερωθούν:** \n\n {', '.join([f'**{c}**' for c in affected_cust_list])}")
                    
                    # Ειδική εξαγωγή για την ανάκληση
                    recall_csv = df_affected.to_csv(index=False, encoding="utf-8-sig")
                    st.download_button("📥 Λήψη Λίστας Ανάκλησης (CSV)", data=recall_csv, file_name=f"RECALL_REPORT_{recall_lot}.csv", mime="text/csv")
                else:
                    st.success("✅ Καμία παραγωγή δεν βρέθηκε με αυτό το Lot πρώτης ύλης. Δεν απαιτείται ανάκληση.")
    
    # --- 6. ΕΚΤΥΠΩΣΗ ΠΛΗΡΟΥΣ ΙΣΤΟΡΙΚΟΥ (ΣΥΝΔΕΣΗ ΜΕ SUPABASE) ---
    st.divider()
    st.subheader("📊 Γενικό Αρχείο Παραγωγής")
    st.info("Εδώ μπορείτε να εκτυπώσετε ολόκληρο το ιστορικό παραγωγής από τη Supabase.")
    
    if st.button("📑 Προετοιμασία Πλήρους Ιστορικού για Εκτύπωση"):
        if res_all.data:
            # Μετατροπή και ταξινόμηση
            df_full_hist = pd.DataFrame(res_all.data).rename(columns={
                "prod_date": "Ημερομηνία",
                "customer": "Πελάτης",
                "cocktail_name": "Cocktail",
                "lot_cocktail": "LOT_Cocktail",
                "ingredient_name": "Υλικό",
                "lot_number": "Lot Number",
                "pieces": "Τεμάχια"
            })
            
            df_full_hist['temp_date'] = pd.to_datetime(df_full_hist['Ημερομηνία'], format='%d/%m/%Y')
            df_full_hist = df_full_hist.sort_values(by='temp_date', ascending=False)
    
            # Δημιουργία HTML (ΑΚΡΙΒΩΣ ΟΠΩΣ ΗΤΑΝ Ο ΚΩΔΙΚΑΣ ΣΟΥ)
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
    
            st.download_button(
                label="📥 Λήψη Πλήρους Ιστορικού (HTML)",
                data=full_html,
                file_name=f"Full_Production_History_{datetime.now().strftime('%d_%m_%y')}.html",
                mime="text/html"
            )
        else:
            st.warning("Δεν βρέθηκαν δεδομένα στη βάση.")


# --- 1.6 ΣΥΝΤΗΡΗΣΗ & HACCP (ULΤΙΜΑΤΕ VERSION) ---
elif page == "🧼 Συντήρηση & HACCP":
    st.header("🧼 Ψηφιακό Μητρώο HACCP & Καθαρισμού")

    # --- ΒΟΗΘΗΤΙΚΗ ΣΥΝΑΡΤΗΣΗ ΓΙΑ REPORT ΜΕ ΥΠΟΓΡΑΦΗ ---
    def generate_haccp_report_html(data, title="ΑΡΧΕΙΟ HACCP"):
        rows_html = ""
        for _, r in data.iterrows():
            extra_info = r['cleaner'] if r['log_type'] == "Καθαρισμός" else r['notes']
            rows_html += f"<tr><td>{r['date']}</td><td>{r['time']}</td><td>{r['item']}</td><td>{r['value']}</td><td>{r['status']}</td><td>{extra_info}</td><td>{r['user_name']}</td></tr>"
        
        return f"""
        <html><head><meta charset='UTF-8'><style>
            body {{ font-family: DejaVu Sans, Arial, sans-serif; padding: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #1e3a8a; color: white; padding: 10px; font-size: 12px; }}
            td {{ border: 1px solid #000; padding: 8px; text-align: center; font-size: 10px; }}
            h2 {{ text-align: center; color: #1e3a8a; text-transform: uppercase; }}
            .signature-section {{ margin-top: 50px; width: 100%; }}
            .sig-box {{ float: right; width: 250px; text-align: center; border-top: 1px solid #000; padding-top: 10px; margin-top: 20px; font-weight: bold; }}
            .date-box {{ float: left; width: 200px; text-align: center; border-top: 1px solid #000; padding-top: 10px; margin-top: 20px; }}
        </style></head><body>
            <h2>CABCLUB COCKTAILS - {title}</h2>
            <table><thead><tr><th>Ημ/νία</th><th>Ώρα</th><th>Στοιχείο</th><th>Τιμή/Τύπος</th><th>Κατάσταση</th><th>Λεπτομέρειες/Καθαριστικά</th><th>Υπεύθυνος</th></tr></thead>
            <tbody>{rows_html}</tbody></table>
            <div class='signature-section'>
                <div class='date-box'>Ημερομηνία Ελέγχου</div>
                <div class='sig-box'>Υπογραφή Υπευθύνου</div>
            </div>
        </body></html>"""

    # --- ΚΕΝΤΡΙΚΑ ΠΕΔΙΑ ---
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        staff_name = st.text_input("👤 Υπεύθυνος Καταγραφής:", placeholder="Ονοματεπώνυμο...")
    with col_u2:
        selected_date = st.date_input("📅 Ημερομηνία:", value=datetime.now())
        date_str = selected_date.strftime("%d/%m/%Y")
    
    tab1, tab2, tab3 = st.tabs(["🌡️ Θερμοκρασίες", "🧹 Checklists Καθαρισμού", "📋 Αρχείο & Εκτυπώσεις"])
    
    # --- TAB 1: ΘΕΡΜΟΚΡΑΣΙΕΣ ---
    with tab1:
        st.subheader("🌡️ Έλεγχος Ψυκτικών Θαλάμων")
        with st.form("temp_form_final_supabase"):
            c1, c2, c3 = st.columns([2, 1, 2])
            device = c1.selectbox("Συσκευή:", ["Ψυγείο 1", "Ψυγείο 2", "Ψυγείο 3", "Κατάψυξη 1", "Κατάψυξη 2"])
            is_freezer = "Κατάψυξη" in device
            temp = c2.number_input("Θερμοκρασία (°C):", value=-18.0 if is_freezer else 4.0, step=0.5)
            notes = c3.text_input("Παρατηρήσεις / Διορθωτικές Ενέργειες:")
            is_ok = not ((is_freezer and temp > -15.0) or (not is_freezer and temp > 7.0))
            
            if st.form_submit_button("💾 Αποθήκευση Μέτρησης", type="primary"):
                if staff_name:
                    log = {"date": date_str, "time": datetime.now().strftime("%H:%M"), "user_name": staff_name, 
                           "log_type": "Θερμοκρασία", "item": device, "value": f"{temp}°C", 
                           "status": "ΕΝΤΟΣ ΟΡΙΩΝ" if is_ok else "ΕΚΤΟΣ ΟΡΙΩΝ", "cleaner": "-", "notes": notes if notes else "-"}
                    supabase.table("haccp_log").insert([log]).execute()
                    st.success("Καταγράφηκε!")
                    time.sleep(1); st.rerun()
                else: st.error("Συμπληρώστε το όνομα!")

    # --- TAB 2: CHECKLISTS ΚΑΘΑΡΙΣΜΟΥ (ΑΚΡΙΒΩΣ ΟΙ ΕΡΓΑΣΙΕΣ ΣΟΥ) ---
    with tab2:
        tasks_data = {
            "Ημερήσιος Καθαρισμός": ["Πάγκοι Εργασίας", "Εξοπλισμός (Blenders/Shakers)", "Δάπεδο Εργαστηρίου", "Απομάκρυνση Απορριμμάτων", "Απολύμανση Χεριών"],
            "Εβδομαδιαίος Καθαρισμός": ["Εσωτερικό Ψυγείων", "Ράφια Αποθήκης", "Τοίχοι & Πλακάκια", "Γενική Απολύμανση"],
            "Μηνιαίος Καθαρισμός": ["Φίλτρα Εξαερισμού", "Σύστημα Κλιματισμού", "Καθαρισμός Οροφής"]
        }
        category = st.radio("Πρόγραμμα:", list(tasks_data.keys()), horizontal=True)
        with st.form(f"cleaning_{category}"):
            st.markdown(f"#### {category}")
            responses = []
            for i, task in enumerate(tasks_data[category]):
                c_task, c_clean = st.columns([0.5, 0.5])
                done = c_task.checkbox(task, key=f"c_{category}_{i}")
                cleaner = c_clean.text_input("Καθαριστικό", key=f"cl_{category}_{i}", placeholder="π.χ. Χλώριο", label_visibility="collapsed")
                if done: responses.append(f"{task} ({cleaner if cleaner else 'Νερό'})")
            
            if st.form_submit_button("🚀 Οριστικοποίηση"):
                if staff_name and len(responses) == len(tasks_data[category]):
                    log = {"date": date_str, "time": datetime.now().strftime("%H:%M"), "user_name": staff_name, 
                           "log_type": "Καθαρισμός", "item": category, "value": "ΟΛΟΚΛΗΡΩΘΗΚΕ", 
                           "status": "ΟΚ", "cleaner": " | ".join(responses), "notes": "-"}
                    supabase.table("haccp_log").insert([log]).execute()
                    st.success("Ενημερώθηκε!")
                    time.sleep(1); st.rerun()
                else: st.error("Επιλέξτε όλες τις εργασίες και βάλτε όνομα!")

    # --- TAB 3: ΑΡΧΕΙΟ & ΕΚΤΥΠΩΣΕΙΣ ---
    with tab3:
        res = supabase.table("haccp_log").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['dt_obj'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
            df = df.sort_values(by=['dt_obj', 'time'], ascending=[False, False])

            # --- ΦΙΛΤΡΑ ΕΚΤΥΠΩΣΗΣ ---
            with st.expander("🖨️ Επιλεκτική Εκτύπωση (Φίλτρα)", expanded=False):
                c1, c2 = st.columns(2)
                p_days = c1.multiselect("Ημερομηνίες:", options=df['date'].unique())
                p_types = c2.multiselect("Τύπος:", ["Θερμοκρασία", "Καθαρισμός"], default=["Θερμοκρασία", "Καθαρισμός"])
                df_rep = df.copy()
                if p_days: df_rep = df_rep[df_rep['date'].isin(p_days)]
                df_rep = df_rep[df_rep['log_type'].isin(p_types)]
                st.download_button("📥 Λήψη Επιλεγμένου Report", generate_haccp_report_html(df_rep), "HACCP_Custom.html", "text/html", use_container_width=True)

            st.divider()
            
            # --- ΙΣΤΟΡΙΚΟ ΜΕ NESTED EXPANDERS ---
            greek_months = {1:"Ιανουάριος", 2:"Φεβρουάριος", 3:"Μάρτιος", 4:"Απρίλιος", 5:"Μάιος", 6:"Ιούνιος", 
                            7:"Ιούλιος", 8:"Αύγουστος", 9:"Σεπτέμβριος", 10:"Οκτώβριος", 11:"Νοέμβριος", 12:"Δεκέμβριος"}
            df['m_label'] = df['dt_obj'].dt.month.map(greek_months) + " " + df['dt_obj'].dt.year.astype(str)

            for m in df['m_label'].unique():
                with st.expander(f"📅 {m}", expanded=False):
                    m_df = df[df['m_label'] == m]
                    for d in m_df['date'].unique():
                        with st.expander(f"🗓️ Ημέρα: {d}", expanded=False):
                            d_df = m_df[m_df['date'] == d]
                            for _, row in d_df.iterrows():
                                col_txt, col_del = st.columns([4, 1])
                                with col_txt:
                                    ic = "🌡️" if row['log_type']=="Θερμοκρασία" else "🧹"
                                    st.write(f"**{ic} {row['item']}** ({row['time']}) -> {row['value']}")
                                    if row['cleaner'] != "-": st.caption(f"🧪 {row['cleaner']}")
                                with col_del:
                                    if st.button("🗑️", key=f"del_{row['id']}"):
                                        supabase.table("haccp_log").delete().eq("id", row['id']).execute()
                                        st.rerun()

            # --- ΚΟΥΜΠΙ ΕΚΤΥΠΩΣΗΣ ΟΛΩΝ ΣΤΟ ΤΕΛΟΣ ---
            st.divider()
            st.download_button(
                label="🖨️ ΕΚΤΥΠΩΣΗ ΟΛΟΥ ΤΟΥ ΑΡΧΕΙΟΥ (Χωρίς Φίλτρα)",
                data=generate_haccp_report_html(df, "ΠΛΗΡΕΣ ΜΗΤΡΩΟ HACCP"),
                file_name="HACCP_Full_Archive.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )
        else:
            st.info("Καμία καταγραφή.")


# --- 10. ΠΕΛΑΤΟΛΟΓΙΟ (CRM - ΜΕ ΔΙΟΡΘΩΣΗ ΣΤΟΙΧΕΙΩΝ) ---
elif page == "👥 Πελατολόγιο":
    st.header("👥 Διαχείριση Πελατολογίου")
    
    # 1. ΦΟΡΤΩΣΗ ΠΕΛΑΤΩΝ
    res_cust = supabase.table("customers").select("*").order("name").execute()
    df_cust = pd.DataFrame(res_cust.data) if res_cust.data else pd.DataFrame()

    tab_crm1, tab_crm2 = st.tabs(["📋 Καρτέλα & Ιστορικό Αγορών", "➕ Προσθήκη Νέου Πελάτη"])

    with tab_crm1:
        if not df_cust.empty:
            col_crm_a, col_crm_b = st.columns([1, 2.5])
            
            with col_crm_a:
                st.subheader("👤 Στοιχεία")
                sel_name = st.selectbox("Επιλέξτε Πελάτη:", options=df_cust["name"].tolist(), key="crm_select_final")
                customer_data = df_cust[df_cust["name"] == sel_name].iloc[0]
                
                st.info(f"""
                **Επικοινωνία:**
                * 📞 {customer_data['phone'] if customer_data['phone'] else '-'}
                * ✉️ {customer_data['email'] if customer_data['email'] else '-'}
                * 📍 {customer_data['address'] if customer_data['address'] else '-'}
                ---
                **Σημειώσεις:**
                {customer_data['notes'] if customer_data['notes'] else 'Καμία σημείωση'}
                """)
                
                # --- ΝΕΟ: ΕΞΥΠΝΗ ΔΙΟΡΘΩΣΗ ΣΤΟΙΧΕΙΩΝ ---
                with st.expander("📝 Επεξεργασία Στοιχείων"):
                    with st.form(f"edit_cust_{customer_data['id']}"):
                        e_name = st.text_input("Όνομα / Επωνυμία", value=customer_data['name'])
                        e_phone = st.text_input("Τηλέφωνο", value=customer_data['phone'])
                        e_email = st.text_input("Email", value=customer_data['email'])
                        e_addr = st.text_area("Διεύθυνση", value=customer_data['address'])
                        e_notes = st.text_area("Σημειώσεις", value=customer_data['notes'])
                        
                        if st.form_submit_button("💾 Ενημέρωση Στοιχείων"):
                            supabase.table("customers").update({
                                "name": e_name, "phone": e_phone, 
                                "email": e_email, "address": e_addr, "notes": e_notes
                            }).eq("id", customer_data["id"]).execute()
                            st.success("Τα στοιχεία ενημερώθηκαν!")
                            st.rerun()

                st.divider()
                if st.button("🗑️ Διαγραφή Πελάτη", type="secondary"):
                    if st.warning("Είστε σίγουροι;"):
                        supabase.table("customers").delete().eq("id", customer_data["id"]).execute()
                        st.success("Διαγράφηκε!")
                        st.rerun()

            with col_crm_b:
                st.subheader(f"🛒 Ιστορικό Παραγγελιών: {sel_name}")
                res_prod = supabase.table("production_log").select("prod_date, cocktail_name, pieces, lot_cocktail, prod_time").eq("customer", sel_name).order("prod_date", desc=True).execute()
                
                if res_prod.data:
                    df_p = pd.DataFrame(res_prod.data)
                    df_p_clean = df_p.drop_duplicates(subset=["prod_date", "prod_time", "lot_cocktail", "cocktail_name"])
                    
                    st.dataframe(
                        df_p_clean.rename(columns={
                            "prod_date": "Ημερομηνία",
                            "cocktail_name": "Cocktail",
                            "pieces": "Τεμάχια"
                        })[["Ημερομηνία", "Cocktail", "Τεμάχια"]],
                        use_container_width=True,
                        hide_index=True
                    )
                    st.metric("Συνολικές Αγορές", f"{int(df_p_clean['pieces'].sum())} τμχ")
                else:
                    st.info("Δεν υπάρχουν παραγγελίες.")
        else:
            st.warning("⚠️ Η λίστα πελατών είναι άδεια.")

    with tab_crm2:
        st.subheader("➕ Καταχώρηση Νέου Πελάτη")
        with st.form("new_customer_form_final", clear_on_submit=True):
            n_name = st.text_input("Όνομα / Επωνυμία *")
            n_phone = st.text_input("Τηλέφωνο")
            n_email = st.text_input("Email")
            n_addr = st.text_area("Διεύθυνση")
            n_notes = st.text_area("Σημειώσεις")
            if st.form_submit_button("💾 Αποθήκευση"):
                if n_name:
                    supabase.table("customers").insert({"name": n_name, "phone": n_phone, "email": n_email, "address": n_addr, "notes": n_notes}).execute()
                    st.success("Ο πελάτης προστέθηκε!")
                    st.rerun()
                else:
                    st.error("Το όνομα είναι υποχρεωτικό!")


# --- 1.5 ΑΝΤΙΚΑΤΑΣΤΑΣΗ ΠΡΩΤΗΣ ΥΛΗΣ (FINAL VERSION - CUSTOM PRICES & CLEAN NUMBERS) ---
elif page == "🔄 Αντικατάσταση":
    st.header("🔄 Καθολική Αντικατάσταση & Οικονομική Πρόγνωση")
    st.info("Σύγκριση Τιμών: Χρησιμοποιούνται οι δικές σας καταχωρημένες τιμές λιανικής. Ο Αντιπρόσωπος υπολογίζεται στο -26%.")

    # Βοηθητική συνάρτηση για καθαρούς αριθμούς (χωρίς περιττά μηδενικά)
    def format_num(n):
        if n is None or n == 0: return "0"
        return f"{n:g}"

    # 1. Ανάκτηση δεδομένων από τη βάση
    res_all_items = supabase.table("recipe_items").select("*").execute()
    df_all_items = pd.DataFrame(res_all_items.data) if res_all_items.data else pd.DataFrame()
    
    if not df_all_items.empty and not df_ing.empty:
        # Λίστα υλικών που χρησιμοποιούνται όντως σε συνταγές
        used_ings = sorted(df_all_items["ingredient_name"].unique().tolist())
        
        col_r1, col_r2 = st.columns(2)
        old_ing = col_r1.selectbox("❌ Παλιό Υλικό:", options=used_ings, index=None, placeholder="Επιλέξτε υλικό...")
        new_ing = col_r2.selectbox("✅ Νέο Υλικό:", options=sorted(df_ing["Name"].unique().tolist()), index=None, placeholder="Από την αποθήκη...")

        if old_ing and new_ing and old_ing != new_ing:
            # Τιμές ανά ml από την αποθήκη
            price_old_ml = df_ing[df_ing["Name"] == old_ing]["Τιμή/ml"].values[0]
            price_new_ml = df_ing[df_ing["Name"] == new_ing]["Τιμή/ml"].values[0]
            diff_ml = price_new_ml - price_old_ml

            # Εύρεση συνταγών που επηρεάζονται
            affected_recipes_ids = df_all_items[df_all_items["ingredient_name"] == old_ing]["recipe_id"].unique().tolist()
            
            if affected_recipes_ids:
                # Φέρνουμε τις υπάρχουσες τιμές λιανικής από τον πίνακα recipes
                res_rec_info = supabase.table("recipes").select("id, name, catalog_price").in_("id", affected_recipes_ids).execute()
                rec_lookup = {r['id']: r for r in res_rec_info.data}

                analysis_data = []
                for rid in affected_recipes_ids:
                    r_items = df_all_items[df_all_items["recipe_id"] == rid]
                    r_name = rec_lookup[rid]['name']
                    # Η τιμή που έχεις ήδη καταχωρήσει εσύ
                    old_retail = rec_lookup[rid]['catalog_price'] or 0.0
                    old_agent = old_retail * 0.74 # -26% 
                    
                    # Υπολογισμός τρέχοντος κόστους για να βρούμε το περιθώριο κέρδους
                    current_cost = 0.22 # TOTAL_FIXED
                    ml_of_old = 0
                    for _, item in r_items.iterrows():
                        ing_n = item['ingredient_name']
                        ml = item['ml_per_unit']
                        if ing_n == old_ing: ml_of_old = ml
                        ing_info = df_ing[df_ing["Name"] == ing_n]
                        if not ing_info.empty:
                            current_cost += ml * ing_info["Τιμή/ml"].values[0]
                    
                    # Υπολογισμός Μεταβολής
                    cost_diff = ml_of_old * diff_ml
                    new_cost = current_cost + cost_diff
                    
                    # Υπολογισμός Νέας Λιανικής (διατηρώντας το ίδιο Markup: Retail/Cost)
                    # Αν δεν υπάρχει τιμή, χρησιμοποιούμε το default Food Cost 25%
                    if current_cost > 0 and old_retail > 0:
                        markup_factor = old_retail / current_cost
                        new_retail = new_cost * markup_factor
                    else:
                        new_retail = new_cost / 0.25
                        
                    new_agent = new_retail * 0.74

                    analysis_data.append({
                        "Cocktail": r_name,
                        "Μεταβολή (€)": round(cost_diff, 3),
                        "Παλιά Λιανική (€)": round(old_retail, 2),
                        "Νέα Λιανική (€)": round(new_retail, 2),
                        "Παλιά Αντιπρ. (€)": round(old_agent, 2),
                        "Νέα Αντιπρ. (€)": round(new_agent, 2)
                    })

                # Δημιουργία DataFrame
                df_res = pd.DataFrame(analysis_data)

                # Μορφοποίηση αριθμών (καθαρισμός μηδενικών)
                # Κρατάμε τη Μεταβολή ως float για το styling
                plot_df = df_res.copy()
                for col in ["Παλιά Λιανική (€)", "Νέα Λιανική (€)", "Παλιά Αντιπρ. (€)", "Νέα Αντιπρ. (€)"]:
                    plot_df[col] = plot_df[col].apply(format_num)

                # Χρωματισμός Μεταβολής
                def style_diff(val):
                    color = '#ff4b4b' if val > 0 else '#00ffcc'
                    return f'color: {color}; font-weight: bold'

                st.subheader(f"📊 Σύγκριση Τιμών: {old_ing} ➡️ {new_ing}")
                
                # Προβολή πίνακα με .map() για Pandas 2.1+
                st.dataframe(
                    plot_df.style.map(style_diff, subset=['Μεταβολή (€)']).format({"Μεταβολή (€)": lambda x: f"{x:g}"}),
                    use_container_width=True,
                    hide_index=True
                )

                st.divider()
                st.caption("💡 Η 'Νέα Λιανική' υπολογίζεται ώστε να διατηρηθεί το ίδιο ποσοστό κέρδους που είχατε με την παλιά πρώτη ύλη.")
                
                # --- ΕΚΤΕΛΕΣΗ ---
                confirm = st.checkbox(f"Επιβεβαιώνω την αντικατάσταση σε {len(df_res)} συνταγές.")
                if st.button("🚀 ΕΚΤΕΛΕΣΗ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΤΩΡΑ", type="primary", disabled=not confirm):
                    with st.spinner("Ενημέρωση συστατικών..."):
                        supabase.table("recipe_items").update({"ingredient_name": new_ing}).eq("ingredient_name", old_ing).execute()
                        st.success("✅ Η αντικατάσταση ολοκληρώθηκε!")
                        st.cache_data.clear()
                        time.sleep(1.5)
                        st.rerun()
            else:
                st.info("Το υλικό δεν βρέθηκε σε καμία συνταγή.")
    else:
        st.warning("⚠️ Δεν υπάρχουν δεδομένα στην αποθήκη ή στις συνταγές.")

# --- ΕΝΟΤΗΤΑ: ΔΙΑΧΕΙΡΙΣΗ ΠΑΡΑΓΓΕΛΙΩΝ B2B & E-SHOP ---
elif page == "📦 Παραγγελίες B2B":
    st.header("📦 Διαχείριση Παραγγελιών B2B")
    
    # --- ΛΕΙΤΟΥΡΓΙΑ WOOCOMMERCE SYNC ---
    from woocommerce import API
    try:
        wcapi = API(
            url=st.secrets["woo"]["url"],
            consumer_key=st.secrets["woo"]["ck"],
            consumer_secret=st.secrets["woo"]["cs"],
            version="wc/v3",
            timeout=20
        )
    except Exception as e:
        st.error(f"⚠️ Πρόβλημα WooCommerce: {e}")

    # Κουμπί Συγχρονισμού στην κορυφή
    col_sync1, col_sync2 = st.columns([1, 2])
    with col_sync1:
        if st.button("📥 Συγχρονισμός με E-shop", use_container_width=True, type="primary"):
            with st.spinner("Τραβάω παραγγελίες από το site..."):
                try:
                    # Τραβάμε παραγγελίες που είναι "processing" (Σε επεξεργασία στο Woo)
                    woo_orders = wcapi.get("orders", params={"status": "processing"}).json()
                    
                    new_entries = 0
                    for o in woo_orders:
                        # Έλεγχος αν η παραγγελία υπάρχει ήδη στη Supabase
                        check = supabase.table("b2b_orders").select("id").eq("woo_id", str(o['id'])).execute()
                        
                        if not check.data:
                            # Προετοιμασία κειμένου παραγγελίας
                            items = []
                            for item in o['line_items']:
                                items.append(f"{item['quantity']}x {item['name']}")
                            order_text = "\n".join(items)
                            
                            # Αποθήκευση στη Supabase
                            data = {
                                "customer_name": f"{o['billing']['first_name']} {o['billing']['last_name']}",
                                "total_amount": float(o['total']),
                                "status": "ΝΕΑ (E-shop)",
                                "order_details": order_text,
                                "notes": o.get('customer_note', ''),
                                "woo_id": str(o['id']),
                                "created_at": o['date_created']
                            }
                            supabase.table("b2b_orders").insert(data).execute()
                            new_entries += 1
                    
                    if new_entries > 0:
                        st.success(f"✅ Εισήχθησαν {new_entries} νέες παραγγελίες!")
                    else:
                        st.info("Δεν βρέθηκαν νέες παραγγελίες στο E-shop.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Σφάλμα σύνδεσης: {e}")

    st.divider()
    
    tab1, tab2 = st.tabs(["🔔 Τρέχουσες Παραγγελίες", "📜 Ιστορικό & Αναζήτηση"])

    # --- TAB 1: ΤΡΕΧΟΥΣΕΣ ΠΑΡΑΓΓΕΛΙΕΣ ---
    with tab1:
        res_orders = supabase.table("b2b_orders").select("*").order("created_at", desc=True).execute()
        if res_orders.data:
            df_orders = pd.DataFrame(res_orders.data)
            
            # Φίλτρο για να περιλαμβάνει και το νέο status από το E-shop
            all_statuses = ["ΝΕΑ", "ΝΕΑ (E-shop)", "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ", "ΟΛΟΚΛΗΡΩΘΗΚΕ"]
            status_filter = st.multiselect("Φίλτρο Κατάστασης:", all_statuses, default=["ΝΕΑ", "ΝΕΑ (E-shop)", "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ"])
            
            df_filtered = df_orders[df_orders["status"].isin(status_filter)]

            for _, row in df_filtered.iterrows():
                # Εικονίδια ανάλογα με την κατάσταση
                icon = "🔵" if "ΝΕΑ" in row['status'] else "🟡" if row['status'] == "ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ" else "✅"
                
                with st.expander(f"{icon} {row['customer_name']} - {row['total_amount']:.2f} €"):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.code(row['order_details'])
                        if row['notes']: st.info(f"📝 {row['notes']}")
                        st.caption(f"ID: {row['id']} | WooID: {row.get('woo_id','-')} | Ημερομηνία: {row['created_at']}")
                    
                    with c2:
                        # Επιλογή νέας κατάστασης
                        current_idx = all_statuses.index(row['status']) if row['status'] in all_statuses else 0
                        new_status = st.selectbox("Αλλαγή Κατάστασης:", all_statuses, index=current_idx, key=f"st_upd_{row['id']}")
                        
                        if st.button("Ενημέρωση", key=f"btn_upd_{row['id']}", use_container_width=True):
                            supabase.table("b2b_orders").update({"status": new_status}).eq("id", row['id']).execute()
                            st.success("Ενημερώθηκε!")
                            time.sleep(0.5)
                            st.rerun()
                        
                        st.divider()
                        if st.button("🗑️ Διαγραφή", key=f"del_b2b_{row['id']}", type="secondary", use_container_width=True):
                            supabase.table("b2b_orders").delete().eq("id", row['id']).execute()
                            st.rerun()
        else:
            st.info("Δεν υπάρχουν παραγγελίες στη βάση.")

    # --- TAB 2: ΙΣΤΟΡΙΚΟ & ΑΝΑΖΗΤΗΣΗ ---
    with tab2:
        st.subheader("🔍 Αναζήτηση στο Ιστορικό")
        if res_orders.data:
            df_hist = pd.DataFrame(res_orders.data)
            
            search_col1, search_col2 = st.columns(2)
            with search_col1:
                cust_search = st.multiselect("Φίλτρο Πελάτη:", options=sorted(df_hist["customer_name"].unique()))
            with search_col2:
                # Εξαγωγή ονομάτων κοκτέιλ από το κείμενο της παραγγελίας
                all_cocktails = set()
                for details in df_hist["order_details"]:
                    lines = str(details).split('\n')
                    for line in lines:
                        if 'x ' in line:
                            # Παίρνει το όνομα μετά το "x "
                            parts = line.split('x ')
                            if len(parts) > 1:
                                name = parts[1].split(' (')[0].strip()
                                all_cocktails.add(name)
                cocktail_search = st.multiselect("Φίλτρο Κοκτέιλ:", options=sorted(list(all_cocktails)))

            # Φιλτράρισμα
            mask = pd.Series([True] * len(df_hist))
            if cust_search: 
                mask &= df_hist["customer_name"].isin(cust_search)
            if cocktail_search:
                cocktail_mask = df_hist["order_details"].apply(lambda x: any(c in str(x) for c in cocktail_search))
                mask &= cocktail_mask

            df_results = df_hist[mask]

            if not df_results.empty:
                st.write(f"Βρέθηκαν **{len(df_results)}** παραγγελίες.")
                for _, row in df_results.iterrows():
                    with st.expander(f"📅 {str(row['created_at'])[:10]} | {row['customer_name']} | {row['total_amount']:.2f} €"):
                        col_h1, col_h2 = st.columns([2, 1])
                        with col_h1:
                            st.markdown(f"**Κατάσταση:** {row['status']}")
                            st.text(row['order_details'])
                        with col_h2:
                            if st.button("🗑️ Διαγραφή", key=f"del_hist_{row['id']}", use_container_width=True):
                                supabase.table("b2b_orders").delete().eq("id", row['id']).execute()
                                st.rerun()
            else:
                st.warning("Δεν βρέθηκαν παραγγελίες με αυτά τα κριτήρια.")
